from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional
from app.services.db import db
from app.models.user import LoginRequest, TokenResponse, UserResponse
from app.core.security import create_access_token, verify_token

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """
    Login endpoint - validate credentials and return JWT token
    """
    users = await db.get_users()
    for user in users:
        if user["email"] == payload.email:
            if user["password"] == payload.password:
                # Valid password - generate JWT token
                access_token = create_access_token(user_id=user["id"])
                user_resp = UserResponse(
                    id=user["id"],
                    name=user["name"],
                    email=user["email"],
                    role=user["role"],
                    podcast_ids=user["podcast_ids"]
                )
                return TokenResponse(access_token=access_token, user=user_resp)
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials"
    )


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
                podcast_ids=user["podcast_ids"]
            )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )
