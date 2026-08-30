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
    podcast_ids: Optional[List[str]] = None

class APIKeysPayload(BaseModel):
    deepgram: Optional[str] = ""
    openai: Optional[str] = ""
    elevenlabs: Optional[str] = ""
    gemini: Optional[str] = ""

@router.get("/users")
async def get_users(authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    return await db.get_users()

@router.get("/team")
@router.get("/team/members")
async def get_team_members_endpoint(authorization: Optional[str] = Header(None)):
    user_id = await verify_admin_token(authorization)
    users = await db.get_users()
    current_user = next((u for u in users if u["id"] == user_id), None)
    if not current_user:
        raise HTTPException(status_code=404, detail="User not found")
    if current_user.get("role") in ["Super Admin", "Admin", "ADMIN"]:
        return await db.get_users()
    user_pods = current_user.get("podcast_ids", ["podcast-1"])
    return await db.get_team_members(user_pods)

@router.put("/users/{user_id}/role")
async def update_user_role(user_id: str, payload: UserUpdateRolePayload, authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    u = await db.update_user_role(user_id, payload.role)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

@router.put("/users/{user_id}/suspend")
async def suspend_user(user_id: str, payload: UserSuspendPayload, authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    u = await db.suspend_user(user_id, payload.suspended)
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    return u

@router.delete("/users/{user_id}")
async def delete_user_endpoint(user_id: str, authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    res = await db.delete_user(user_id)
    if not res:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User {user_id} deleted successfully"}

@router.post("/users/invite")
async def invite_user(payload: InviteUserPayload, authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    users = await db.get_users()
    inviter = next((u for u in users if u["id"] == admin_user), None)
    
    p_ids = payload.podcast_ids or []
    if inviter and inviter.get("role") == "Podcast Owner":
        owner_pods = inviter.get("podcast_ids", ["podcast-1"])
        if owner_pods:
            p_ids = owner_pods
    if not p_ids:
        p_ids = ["podcast-1"]

    u = await db.invite_user(payload.name, payload.email, payload.role, podcast_ids=p_ids)
    user_id = u.get("id") or u.get("email")
    
    # Create password setup reset token
    from app.core.security import create_reset_token
    reset_token = create_reset_token(user_id)
    setup_link = f"https://podule.vendatechnologies.com/reset-password?token={reset_token}&email={payload.email}"
    
    # Send email with link to set up password
    from app.services.email import send_email
    subject = "Invitation to Podule Studio - Set Up Your Password"
    plain_body = f"""Hello {payload.name},

You have been invited to join Podule Studio as a {payload.role}.

Please click the link below to set up your password and access your workspace:
{setup_link}

This invitation link expires in 72 hours.

Best regards,
Podule Studio Team
"""
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
      <h2 style="color: #0f172a; margin-bottom: 16px;">Welcome to Podule Studio!</h2>
      <p style="color: #334155; font-size: 15px; line-height: 1.5;">Hello <strong>{payload.name}</strong>,</p>
      <p style="color: #334155; font-size: 15px; line-height: 1.5;">You have been invited to join the <strong>Podule Studio</strong> workspace as a <strong>{payload.role}</strong>.</p>
      <p style="color: #334155; font-size: 15px; line-height: 1.5;">Please click the button below to set up your password and access your account:</p>
      <div style="margin: 28px 0; text-align: center;">
        <a href="{setup_link}" style="background-color: #6366f1; color: #ffffff; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: bold; font-size: 15px; display: inline-block;">Set Up Your Password &rarr;</a>
      </div>
      <p style="color: #64748b; font-size: 13px;">If the button doesn't work, copy and paste this link into your browser:<br/><a href="{setup_link}" style="color: #6366f1;">{setup_link}</a></p>
      <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 24px 0;" />
      <p style="color: #94a3b8; font-size: 12px; margin: 0;">This invitation link will expire in 72 hours.</p>
    </div>
    """
    await send_email(to=payload.email, subject=subject, body=plain_body, html=html_body)
    
    return {
        "id": user_id,
        "name": payload.name,
        "email": payload.email,
        "role": payload.role,
        "podcast_ids": p_ids,
        "invite_link": setup_link,
        "message": "Invitation sent successfully via email"
    }

@router.get("/api-keys")
async def get_api_keys(authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    keys = await db.get_api_keys()
    
    def mask_key(prefix: str, key: str) -> str:
        if not key: return ""
        k_str = str(key).strip()
        if len(k_str) > 8:
            return f"{prefix}...{k_str[-4:]}"
        return f"{prefix}..."

    return {
        "deepgram": mask_key("dg-", keys.get("deepgram")),
        "openai": mask_key("sk-", keys.get("openai")),
        "elevenlabs": mask_key("el-", keys.get("elevenlabs")),
        "gemini": mask_key("AIza...", keys.get("gemini"))
    }

def is_masked_placeholder(val: Optional[str]) -> bool:
    if not val:
        return True
    val_str = str(val).strip()
    return "..." in val_str or "[masked]" in val_str or val_str.startswith(("sk-...", "dg-...", "el-...", "AIza...", "enc:"))


@router.put("/api-keys")
async def update_api_keys(payload: APIKeysPayload, authorization: Optional[str] = Header(None)):
    """
    Update API keys with dual persistence to Atlas MongoDB and active environment.
    """
    admin_user = await verify_admin_token(authorization)
    upd = {}
    current_keys = await db.get_api_keys()

    for k in ["deepgram", "openai", "elevenlabs", "gemini"]:
        val = getattr(payload, k, None)
        if val is not None and not is_masked_placeholder(val) and val.strip():
            upd[k] = val.strip()
        elif current_keys.get(k):
            upd[k] = current_keys[k]

    if upd:
        await db.update_api_keys(upd)

    saved_keys = await db.get_api_keys()

    def mask_key(prefix: str, key: Optional[str]) -> str:
        if not key: return ""
        k_str = str(key).strip()
        if len(k_str) > 8:
            return f"{prefix}...{k_str[-4:]}"
        return f"{prefix}..."

    return {
        "deepgram": mask_key("dg-", saved_keys.get("deepgram")),
        "openai": mask_key("sk-", saved_keys.get("openai")),
        "elevenlabs": mask_key("el-", saved_keys.get("elevenlabs")),
        "gemini": mask_key("AIza...", saved_keys.get("gemini"))
    }



@router.get("/analytics")
async def get_admin_analytics(authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    return await db.get_admin_analytics()
