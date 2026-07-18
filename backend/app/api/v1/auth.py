import os
from fastapi import APIRouter, HTTPException, status, Header, Body
from typing import Optional
from app.services.db import db
from app.models.user import LoginRequest, TokenResponse, UserResponse, UserCreate
from app.core.security import create_access_token, verify_token, hash_password, verify_password, create_reset_token, verify_reset_token

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    users = await db.get_users()
    for user in users:
        if user["email"] == payload.email:
            stored_pw = user.get("password", "")
            if ":" in stored_pw:
                if verify_password(payload.password, stored_pw):
                    access_token = create_access_token(user_id=user["id"])
                    return TokenResponse(
                        access_token=access_token,
                        user=UserResponse(
                            id=user["id"], name=user["name"], email=user["email"],
                            role=user["role"], podcast_ids=user["podcast_ids"],
                            provider_config=user.get("provider_config"),
                            monthly_token_usage=user.get("monthly_token_usage", 0),
                            token_limit=user.get("token_limit", 100000)
                        )
                    )
            elif user["password"] == payload.password:
                access_token = create_access_token(user_id=user["id"])
                return TokenResponse(
                    access_token=access_token,
                    user=UserResponse(
                        id=user["id"], name=user["name"], email=user["email"],
                        role=user["role"], podcast_ids=user["podcast_ids"],
                        provider_config=user.get("provider_config"),
                        monthly_token_usage=user.get("monthly_token_usage", 0),
                        token_limit=user.get("token_limit", 100000)
                    )
                )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/register", response_model=TokenResponse)
async def register(payload: UserCreate):
    existing = await db.get_users()
    for u in existing:
        if u["email"] == payload.email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    hashed_pw = hash_password(payload.password)
    user_data = payload.model_dump()
    user_data["password"] = hashed_pw
    created = await db.create_user(user_data)
    access_token = create_access_token(user_id=created["id"])
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=created["id"], name=created["name"], email=created["email"],
            role=created["role"], podcast_ids=created["podcast_ids"],
            monthly_token_usage=created.get("monthly_token_usage", 0),
            token_limit=created.get("token_limit", 100000)
        )
    )


@router.post("/forgot-password")
async def forgot_password(email: str = Body(..., embed=True)):
    users = await db.get_users()
    user = next((u for u in users if u["email"] == email), None)
    if not user:
        return {"message": "If the email exists, a reset link has been sent."}
    reset_token = create_reset_token(user["id"])
    smtp_settings = await db.get_settings()
    smtp_creds = smtp_settings.get("smtp", {}) if smtp_settings else {}
    if smtp_creds.get("host") and smtp_creds.get("from_email"):
        from app.services.email import send_email
        reset_link = f"{os.getenv('FRONTEND_URL', 'http://localhost:5173')}/reset-password?token={reset_token}"
        await send_email(
            to=email,
            subject="Reset your Podule password",
            body=f"Click this link to reset your password: {reset_link}\n\nThis link expires in 1 hour.",
            smtp_config=smtp_creds,
        )
    else:
        import secrets as sec
        db._reset_tokens = getattr(db, '_reset_tokens', {})
        db._reset_tokens[email] = reset_token
    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(token: str = Body(..., embed=True), new_password: str = Body(..., embed=True)):
    user_id = verify_reset_token(token)
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")
    hashed_pw = hash_password(new_password)
    await db.update_user(user_id, {"password": hashed_pw})
    return {"message": "Password reset successfully"}


@router.get("/me", response_model=UserResponse)
async def get_me(authorization: Optional[str] = Header(None)):
    """
    Get current user info - requires valid JWT token in Authorization header
    """
    user_id = await verify_token(authorization)
    users = await db.get_users()
    for user in users:
        if user["id"] == user_id:
            return UserResponse(
                id=user["id"],
                name=user["name"],
                email=user["email"],
                role=user["role"],
                podcast_ids=user["podcast_ids"],
                provider_config=user.get("provider_config"),
                monthly_token_usage=user.get("monthly_token_usage", 0),
                token_limit=user.get("token_limit", 100000)
            )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
