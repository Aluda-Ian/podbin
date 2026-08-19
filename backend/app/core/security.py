import jwt
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Header
import httpx

# Token configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30  # 30 days session token duration



def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{pwd_hash}"


def verify_password(password: str, hashed: str) -> bool:
    if ":" not in hashed:
        return hashed == password
    salt, pwd_hash = hashed.split(":", 1)
    return hashlib.sha256((salt + password).encode()).hexdigest() == pwd_hash


def create_reset_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    expire = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode(
        {"user_id": user_id, "reset_token": token, "exp": expire, "purpose": "reset_password"},
        SECRET_KEY, algorithm=ALGORITHM
    )


def verify_reset_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("purpose") != "reset_password":
            return None
        return payload.get("user_id")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


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
            detail="Dashboard session expired. Please log out and log back in."
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
        if user["id"] == user_id and user.get("role") in ["admin", "Super Admin", "ADMIN"]:
            return user_id
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )


async def validate_openai_api_key(api_key: str) -> bool:
    """Validate OpenAI API key by making a test call"""
    if not api_key or len(api_key) < 15:
        return False
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                "https://api.openai.com/v1/models",
                headers={"Authorization": f"Bearer {api_key}"},
                follow_redirects=True
            )
            # 200 = valid key; 429 = valid key but quota exceeded; 401 = invalid
            if response.status_code in (200, 429):
                return True
            elif response.status_code == 401:
                return False
            # Be lenient on temporary network or server status codes (5xx, etc)
            return response.status_code < 500
    except Exception:
        # Fall back to checking key format if network check fails
        return api_key.startswith("sk-")


async def validate_deepgram_api_key(api_key: str) -> bool:
    """Validate Deepgram API key by making a test call"""
    if not api_key or len(api_key) < 10:
        return False
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                "https://api.deepgram.com/v1/projects",
                headers={"Authorization": f"Token {api_key}"},
                follow_redirects=True
            )
            if response.status_code in (200, 402, 429):
                return True
            elif response.status_code == 401:
                # Try fallback models endpoint in case key is project-scoped
                resp2 = await client.get(
                    "https://api.deepgram.com/v1/models",
                    headers={"Authorization": f"Token {api_key}"},
                    follow_redirects=True
                )
                return resp2.status_code in (200, 402, 429)
            return response.status_code < 500
    except Exception:
        return len(api_key) >= 20


async def validate_elevenlabs_api_key(api_key: str) -> bool:
    """Validate ElevenLabs API key by making a test call"""
    if not api_key or len(api_key) < 10:
        return False
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": api_key},
                follow_redirects=True
            )
            if response.status_code in (200, 401, 402, 429):
                return response.status_code != 401
            return response.status_code < 500
    except Exception:
        return len(api_key) >= 20


async def validate_api_key_format(key_type: str, api_key: str) -> tuple[bool, str]:
    """
    Validate both format and authenticity of API key
    Returns (is_valid, error_message)
    """
    if not api_key or not isinstance(api_key, str):
        return False, f"Invalid {key_type} API key format"
    
    clean_key = api_key.strip()

    # Skip validation for masked key placeholders
    if "..." in clean_key or "[masked]" in clean_key or clean_key.startswith(("sk-...", "dg-...", "el-...")):
        return True, ""
    
    if key_type == "openai":
        if not (clean_key.startswith("sk-") or len(clean_key) >= 20):
            return False, "OpenAI key format is invalid"
        is_valid = await validate_openai_api_key(clean_key)
        if not is_valid:
            return False, "OpenAI API key authentication failed or expired"
    
    elif key_type == "deepgram":
        if len(clean_key) < 10:
            return False, "Deepgram API key is too short"
        is_valid = await validate_deepgram_api_key(clean_key)
        if not is_valid:
            return False, "Deepgram API key authentication failed or expired"
    
    elif key_type == "elevenlabs":
        if len(clean_key) < 10:
            return False, "ElevenLabs API key is too short"
        is_valid = await validate_elevenlabs_api_key(clean_key)
        if not is_valid:
            return False, "ElevenLabs API key authentication failed or expired"
    
    else:
        return False, f"Unknown key type: {key_type}"
    
    return True, ""

