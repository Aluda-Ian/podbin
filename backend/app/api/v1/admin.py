from fastapi import APIRouter, HTTPException, status, Header
from typing import Optional
from pydantic import BaseModel
from typing import Dict, Any, List
from app.services.db import db
from app.core.security import verify_admin_token, validate_api_key_format

router = APIRouter()

class UserUpdateRolePayload(BaseModel):
    role: str

class UserSuspendPayload(BaseModel):
    suspended: bool

class InviteUserPayload(BaseModel):
    name: str
    email: str
    role: str

class APIKeysPayload(BaseModel):
    deepgram: str
    openai: str
    elevenlabs: str

@router.get("/users")
async def get_users(authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    return await db.get_users()

@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, payload: UserUpdateRolePayload, authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    u = await db.update_user_role(user_id, payload.role)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

@router.put("/users/{user_id}/status")
async def suspend_user(user_id: str, payload: UserSuspendPayload, authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    u = await db.suspend_user(user_id, payload.suspended)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

@router.post("/users/invite")
async def invite_user(payload: InviteUserPayload, authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    u = await db.invite_user(payload.name, payload.email, payload.role)
    return u

@router.get("/api-keys")
async def get_api_keys(authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    keys = await db.get_api_keys()
    # Mask key values for security
    return {
        "deepgram": f"dg-...{keys['deepgram'][-4:]}" if keys.get("deepgram") else "",
        "openai": f"sk-...{keys['openai'][-4:]}" if keys.get("openai") else "",
        "elevenlabs": f"el-...{keys['elevenlabs'][-4:]}" if keys.get("elevenlabs") else ""
    }

@router.put("/api-keys")
async def update_api_keys(payload: APIKeysPayload, authorization: Optional[str] = Header(None)):
    """
    Update API keys with validation against actual services
    """
    admin_user = await verify_admin_token(authorization)
    upd = {}
    
    # Validate and update deepgram key if provided
    if payload.deepgram and not payload.deepgram.startswith("dg-..."):
        is_valid, error_msg = await validate_api_key_format("deepgram", payload.deepgram)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Deepgram API key: {error_msg}"
            )
        upd["deepgram"] = payload.deepgram
    
    # Validate and update OpenAI key if provided
    if payload.openai and not payload.openai.startswith("sk-..."):
        is_valid, error_msg = await validate_api_key_format("openai", payload.openai)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OpenAI API key: {error_msg}"
            )
        upd["openai"] = payload.openai
    
    # Validate and update ElevenLabs key if provided
    if payload.elevenlabs and not payload.elevenlabs.startswith("el-..."):
        is_valid, error_msg = await validate_api_key_format("elevenlabs", payload.elevenlabs)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ElevenLabs API key: {error_msg}"
            )
        upd["elevenlabs"] = payload.elevenlabs
    
    if upd:
        return await db.update_api_keys(upd)
    return await db.get_api_keys()

@router.get("/analytics")
async def get_admin_analytics(authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    return await db.get_admin_analytics()
