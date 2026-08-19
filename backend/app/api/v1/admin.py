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
        "invite_link": setup_link,
        "message": "Invitation sent successfully via email"
    }

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

def is_masked_placeholder(val: Optional[str]) -> bool:
    if not val:
        return True
    val_str = str(val).strip()
    return "..." in val_str or "[masked]" in val_str or val_str.startswith("enc:")

@router.put("/api-keys")
async def update_api_keys(payload: APIKeysPayload, authorization: Optional[str] = Header(None)):
    """
    Update API keys with validation against actual services
    """
    admin_user = await verify_admin_token(authorization)
    upd = {}
    current_keys = await db.get_api_keys()
    
    # Validate and update deepgram key if provided and not masked placeholder
    if payload.deepgram and not is_masked_placeholder(payload.deepgram):
        is_valid, error_msg = await validate_api_key_format("deepgram", payload.deepgram)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Deepgram API key: {error_msg}"
            )
        upd["deepgram"] = payload.deepgram.strip()
    elif current_keys.get("deepgram"):
        upd["deepgram"] = current_keys["deepgram"]
    
    # Validate and update OpenAI key if provided and not masked placeholder
    if payload.openai and not is_masked_placeholder(payload.openai):
        is_valid, error_msg = await validate_api_key_format("openai", payload.openai)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OpenAI API key: {error_msg}"
            )
        upd["openai"] = payload.openai.strip()
    elif current_keys.get("openai"):
        upd["openai"] = current_keys["openai"]
    
    # Validate and update ElevenLabs key if provided and not masked placeholder
    if payload.elevenlabs and not is_masked_placeholder(payload.elevenlabs):
        is_valid, error_msg = await validate_api_key_format("elevenlabs", payload.elevenlabs)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ElevenLabs API key: {error_msg}"
            )
        upd["elevenlabs"] = payload.elevenlabs.strip()
    elif current_keys.get("elevenlabs"):
        upd["elevenlabs"] = current_keys["elevenlabs"]
    
    if upd:
        await db.update_api_keys(upd)
    
    saved_keys = await db.get_api_keys()
    return {
        "deepgram": f"dg-...{saved_keys['deepgram'][-4:]}" if saved_keys.get("deepgram") else "",
        "openai": f"sk-...{saved_keys['openai'][-4:]}" if saved_keys.get("openai") else "",
        "elevenlabs": f"el-...{saved_keys['elevenlabs'][-4:]}" if saved_keys.get("elevenlabs") else ""
    }


@router.get("/analytics")
async def get_admin_analytics(authorization: Optional[str] = Header(None)):
    admin_user = await verify_admin_token(authorization)
    return await db.get_admin_analytics()
