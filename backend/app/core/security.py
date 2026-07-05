import jwt
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
import httpx

# Token configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(user_id: str, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT token for a user"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    to_encode = {
        "user_id": user_id,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def verify_token(authorization: Optional[str] = Header(None)) -> str:
    """Verify JWT token from Authorization header and return user_id"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    # Extract token from "Bearer <token>"
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = parts[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


async def verify_admin_token(authorization: Optional[str] = Header(None)) -> str:
    """Verify JWT token for admin endpoints"""
    from app.services.db import db
    
    user_id = await verify_token(authorization)
    
    # Check if user is admin
    users = await db.get_users()
    for user in users:
        if user["id"] == user_id and user.get("role") == "admin":
            return user_id
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )


async def validate_openai_api_key(api_key: str) -> bool:
    """Validate OpenAI API key by making a test call"""
    if not api_key or not api_key.startswith("sk-"):
        return False
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                follow_redirects=True
            )
            # If we get 401, the key is invalid format but valid structure
            # If we get 200, key is valid
            # If we get 401 with auth_error, key is invalid
            if response.status_code == 401:
                error_data = response.json() if response.text else {}
                if "invalid_api_key" in error_data.get("error", {}).get("type", ""):
                    return False
                # Some 401s might be due to other auth issues, be lenient
                return True
            elif response.status_code == 200:
                return True
            else:
                # Network errors or other issues - be conservative
                return False
    except Exception:
        # If we can't validate due to network issues, assume false
        return False


async def validate_deepgram_api_key(api_key: str) -> bool:
    """Validate Deepgram API key by making a test call"""
    if not api_key or not api_key.startswith("dg-"):
        return False
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.deepgram.com/v1/models",
                headers={"Authorization": f"Token {api_key}"},
                follow_redirects=True
            )
            if response.status_code in (200, 401):
                # 200 = valid key
                # 401 = invalid key (but we need to check the error message)
                if response.status_code == 401:
                    error_data = response.json() if response.text else {}
                    # If explicitly unauthorized, key is invalid
                    return False
                return True
            return False
    except Exception:
        return False


async def validate_elevenlabs_api_key(api_key: str) -> bool:
    """Validate ElevenLabs API key by making a test call"""
    if not api_key or not api_key.startswith(("xi-", "pat-")):
        return False
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": api_key},
                follow_redirects=True
            )
            if response.status_code == 200:
                return True
            elif response.status_code == 401:
                # Invalid key
                return False
            return False
    except Exception:
        return False


async def validate_api_key_format(key_type: str, api_key: str) -> tuple[bool, str]:
    """
    Validate both format and authenticity of API key
    Returns (is_valid, error_message)
    """
    if not api_key or not isinstance(api_key, str):
        return False, f"Invalid {key_type} API key format"
    
    if key_type == "openai":
        if not api_key.startswith("sk-"):
            return False, "OpenAI key must start with 'sk-'"
        # Validate against OpenAI API
        is_valid = await validate_openai_api_key(api_key)
        if not is_valid:
            return False, "OpenAI API key is invalid or expired"
    
    elif key_type == "deepgram":
        if not api_key.startswith("dg-"):
            return False, "Deepgram key must start with 'dg-'"
        is_valid = await validate_deepgram_api_key(api_key)
        if not is_valid:
            return False, "Deepgram API key is invalid or expired"
    
    elif key_type == "elevenlabs":
        if not api_key.startswith(("xi-", "pat-")):
            return False, "ElevenLabs key must start with 'xi-' or 'pat-'"
        is_valid = await validate_elevenlabs_api_key(api_key)
        if not is_valid:
            return False, "ElevenLabs API key is invalid or expired"
    
    else:
        return False, f"Unknown key type: {key_type}"
    
    return True, ""
