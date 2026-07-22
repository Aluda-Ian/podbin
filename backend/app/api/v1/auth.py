import os
import pyotp
import time
from fastapi import APIRouter, HTTPException, status, Header, Body
from typing import Optional
from pydantic import BaseModel
from app.services.db import db
from app.models.user import LoginRequest, TokenResponse, UserResponse, UserCreate
from app.core.security import create_access_token, verify_token, hash_password, verify_password, create_reset_token, verify_reset_token

router = APIRouter()

# Temporary in-memory OTP store. For production, use Redis or MongoDB with TTL.
OTP_STORE = {}

class OTPRequest(BaseModel):
    email: str

class OTPVerifyRequest(BaseModel):
    email: str
    otp: str
    name: str
    password: str
    role: str = "Team Member"

class Login2FARequest(BaseModel):
    email: str
    code: str

class Enable2FARequest(BaseModel):
    code: str

@router.post("/register-request-otp")
async def register_request_otp(payload: OTPRequest):
    users = await db.get_users()
    if any(u["email"] == payload.email for u in users):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    
    # Generate 6-digit OTP
    totp = pyotp.TOTP(pyotp.random_base32(), interval=300) # 5 min validity
    otp_code = totp.now()
    OTP_STORE[payload.email] = {"code": otp_code, "expires": time.time() + 300}
    
    # Send email
    smtp_settings = await db.get_settings()
    smtp_creds = smtp_settings.get("smtp", {}) if smtp_settings else {}
    if smtp_creds.get("host") and smtp_creds.get("from_email"):
        from app.services.email import send_email
        await send_email(
            to=payload.email,
            subject="Your Podule Registration Code",
            body=f"Your verification code is: {otp_code}\n\nIt expires in 5 minutes.",
            smtp_config=smtp_creds,
        )
    else:
        # Fallback if SMTP not configured: print to server console for testing
        print(f"[DEV] OTP for {payload.email}: {otp_code}")
        
    return {"message": "OTP sent to email"}


@router.post("/register-verify", response_model=TokenResponse)
async def register_verify(payload: OTPVerifyRequest):
    stored = OTP_STORE.get(payload.email)
    if not stored or time.time() > stored["expires"] or stored["code"] != payload.otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired OTP")
    
    users = await db.get_users()
    if any(u["email"] == payload.email for u in users):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        
    hashed_pw = hash_password(payload.password)
    user_data = {
        "name": payload.name,
        "email": payload.email,
        "role": payload.role,
        "password": hashed_pw,
        "podcast_ids": [],
        "is_verified": True,
        "two_factor_enabled": False
    }
    
    created = await db.create_user(user_data)
    # Clear OTP
    del OTP_STORE[payload.email]
    
    access_token = create_access_token(user_id=created["id"])
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=created["id"], name=created["name"], email=created["email"],
            role=created["role"], podcast_ids=created["podcast_ids"],
            is_verified=True, two_factor_enabled=False
        )
    )

# Fallback for old registration to not break things if needed
@router.post("/register", response_model=TokenResponse)
async def register(payload: UserCreate):
    existing = await db.get_users()
    for u in existing:
        if u["email"] == payload.email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    hashed_pw = hash_password(payload.password)
    user_data = payload.model_dump()
    user_data["password"] = hashed_pw
    user_data["is_verified"] = True
    created = await db.create_user(user_data)
    access_token = create_access_token(user_id=created["id"])
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=created["id"], name=created["name"], email=created["email"],
            role=created["role"], podcast_ids=created["podcast_ids"],
            is_verified=True, two_factor_enabled=False
        )
    )


@router.post("/login")
async def login(payload: LoginRequest):
    users = await db.get_users()
    for user in users:
        if user["email"] == payload.email:
            stored_pw = user.get("password", "")
            is_valid = False
            if ":" in stored_pw:
                is_valid = verify_password(payload.password, stored_pw)
            else:
                is_valid = (stored_pw == payload.password)
                
            if is_valid:
                if user.get("two_factor_enabled"):
                    return {"require_2fa": True, "email": user["email"]}
                    
                access_token = create_access_token(user_id=user["id"])
                return TokenResponse(
                    access_token=access_token,
                    user=UserResponse(
                        id=user["id"], name=user["name"], email=user["email"],
                        role=user["role"], podcast_ids=user["podcast_ids"],
                        provider_config=user.get("provider_config"),
                        monthly_token_usage=user.get("monthly_token_usage", 0),
                        token_limit=user.get("token_limit", 100000),
                        is_verified=user.get("is_verified", False),
                        two_factor_enabled=user.get("two_factor_enabled", False)
                    )
                )
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


@router.post("/login-verify-2fa", response_model=TokenResponse)
async def login_verify_2fa(payload: Login2FARequest):
    users = await db.get_users()
    user = next((u for u in users if u["email"] == payload.email), None)
    if not user or not user.get("two_factor_enabled") or not user.get("two_factor_secret"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not enabled for this user")
        
    totp = pyotp.TOTP(user["two_factor_secret"])
    if not totp.verify(payload.code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code")
        
    access_token = create_access_token(user_id=user["id"])
    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user["id"], name=user["name"], email=user["email"],
            role=user["role"], podcast_ids=user["podcast_ids"],
            provider_config=user.get("provider_config"),
            monthly_token_usage=user.get("monthly_token_usage", 0),
            token_limit=user.get("token_limit", 100000),
            is_verified=user.get("is_verified", False),
            two_factor_enabled=True
        )
    )

@router.get("/2fa/setup")
async def setup_2fa(authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    users = await db.get_users()
    user = next((u for u in users if u["id"] == user_id), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    # Generate secret
    secret = pyotp.random_base32()
    # Save secret temporarily (not enabled yet)
    await db.update_user(user_id, {"two_factor_secret": secret, "two_factor_enabled": False})
    
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user["email"], issuer_name="Podule")
    
    return {"secret": secret, "uri": uri}


@router.post("/2fa/enable")
async def enable_2fa(payload: Enable2FARequest, authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    users = await db.get_users()
    user = next((u for u in users if u["id"] == user_id), None)
    
    if not user or not user.get("two_factor_secret"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA setup not initiated")
        
    totp = pyotp.TOTP(user["two_factor_secret"])
    if not totp.verify(payload.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 2FA code")
        
    await db.update_user(user_id, {"two_factor_enabled": True})
    return {"message": "2FA successfully enabled"}


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
                token_limit=user.get("token_limit", 100000),
                is_verified=user.get("is_verified", False),
                two_factor_enabled=user.get("two_factor_enabled", False)
            )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
