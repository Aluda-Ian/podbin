from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, List
from app.services.db import db

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
async def get_users():
    return db.get_users()

@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, payload: UserUpdateRolePayload):
    u = db.update_user_role(user_id, payload.role)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

@router.put("/users/{user_id}/status")
async def suspend_user(user_id: str, payload: UserSuspendPayload):
    u = db.suspend_user(user_id, payload.suspended)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

@router.post("/users/invite")
async def invite_user(payload: InviteUserPayload):
    u = db.invite_user(payload.name, payload.email, payload.role)
    return u

@router.get("/api-keys")
async def get_api_keys():
    keys = db.get_api_keys()
    # Mask key values for security
    return {
        "deepgram": f"dg-...{keys['deepgram'][-4:]}" if keys.get("deepgram") else "",
        "openai": f"sk-...{keys['openai'][-4:]}" if keys.get("openai") else "",
        "elevenlabs": f"el-...{keys['elevenlabs'][-4:]}" if keys.get("elevenlabs") else ""
    }

@router.put("/api-keys")
async def update_api_keys(payload: APIKeysPayload):
    upd = {}
    if payload.deepgram and not payload.deepgram.startswith("dg-..."):
        upd["deepgram"] = payload.deepgram
    if payload.openai and not payload.openai.startswith("sk-..."):
        upd["openai"] = payload.openai
    if payload.elevenlabs and not payload.elevenlabs.startswith("el-..."):
        upd["elevenlabs"] = payload.elevenlabs
    if upd:
        return db.update_api_keys(upd)
    return db.get_api_keys()

@router.get("/analytics")
async def get_admin_analytics():
    return db.get_admin_analytics()
