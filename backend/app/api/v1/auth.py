from fastapi import APIRouter, HTTPException, status
from app.services.db import db
from app.models.user import LoginRequest, TokenResponse, UserResponse

router = APIRouter()

@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    users = db.get_users()
    for user in users:
        if user["email"] == payload.email:
            if user["password"] == payload.password:
                # Valid password
                mock_token = f"mock-token-{user['id']}"
                user_resp = UserResponse(
                    id=user["id"],
                    name=user["name"],
                    email=user["email"],
                    role=user["role"],
                    podcast_ids=user["podcast_ids"]
                )
                return TokenResponse(access_token=mock_token, user=user_resp)
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid password"
                )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="User not found"
    )

@router.get("/me", response_model=UserResponse)
async def get_me(token: str):
    if not token.startswith("mock-token-"):
        raise HTTPException(
            status_code=status.HTTP_418_IM_A_TEAPOT,
            detail="Invalid token format"
        )
    user_id = token.replace("mock-token-", "")
    users = db.get_users()
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
