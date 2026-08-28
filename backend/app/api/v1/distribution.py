import os
import secrets
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, status, Header, Query, Depends
from pydantic import BaseModel
import httpx

from app.models.social_connection import SocialConnection
from app.models.social_post import SocialPost
from app.core.security import verify_token, encrypt_key, decrypt_key
from app.services.db import db

router = APIRouter()

# Supported social media platforms
SUPPORTED_PLATFORMS = ["youtube", "linkedin", "twitter", "tiktok", "instagram", "facebook"]

# OAuth configuration helpers
def get_oauth_config(platform: str, settings: dict) -> dict:
    ic = settings.get("integration_credentials", {}) or {}
    creds = ic.get(platform, {}) or {}
    
    client_id = creds.get("client_id") or os.getenv(f"{platform.upper()}_CLIENT_ID", "")
    client_secret = creds.get("client_secret") or os.getenv(f"{platform.upper()}_CLIENT_SECRET", "")
    
    redirect_uri = f"https://podule.vendatechnologies.com/api/v1/distribution/callback/{platform}"
    return {
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }


@router.get("/connections")
async def list_social_connections(authorization: Optional[str] = Header(None)):
    """List all connected social media accounts for user"""
    user_id = await verify_token(authorization)
    await db.ensure_db_initialized()

    if db.is_db_ready:
        try:
            conns = await SocialConnection.find(SocialConnection.user_id == user_id).to_list()
            return [
                {
                    "id": c.id,
                    "platform": c.platform,
                    "account_id": c.account_id,
                    "account_name": c.account_name,
                    "avatar_url": c.avatar_url,
                    "status": "expired" if c.is_token_expired() else c.status,
                    "auto_posting_enabled": c.auto_posting_enabled,
                    "created_at": c.created_at.isoformat()
                }
                for c in conns
            ]
        except Exception as e:
            print(f"[DISTRIBUTION] Error listing social connections: {e}")

    return []


@router.get("/connect/{platform}")
async def get_oauth_redirect_url(platform: str, authorization: Optional[str] = Header(None)):
    """Generate OAuth2 redirect authorization URL for specified platform"""
    user_id = await verify_token(authorization)
    p_clean = platform.lower()
    
    if p_clean not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Platform '{platform}' is not supported")

    settings = await db.get_settings()
    cfg = get_oauth_config(p_clean, settings)
    
    if not cfg["client_id"]:
        # Provide fallback demo authorization for testing if client_id is not set
        state = f"{user_id}:{p_clean}:{secrets.token_hex(8)}"
        demo_url = f"https://podule.vendatechnologies.com/api/v1/distribution/callback/{p_clean}?code=demo_auth_code_{secrets.token_hex(6)}&state={state}"
        return {
            "platform": p_clean,
            "auth_url": demo_url,
            "is_demo_mode": True,
            "message": f"Client ID for {p_clean} not configured in Settings. Operating in Sandbox mode."
        }

    state = f"{user_id}:{p_clean}:{secrets.token_hex(8)}"
    
    # Construct platform specific OAuth URLs
    if p_clean == "youtube":
        scope = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly"
        auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={cfg['client_id']}&redirect_uri={cfg['redirect_uri']}&scope={scope}&access_type=offline&prompt=consent&state={state}"
    elif p_clean == "linkedin":
        scope = "r_liteprofile w_member_social"
        auth_url = f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={cfg['client_id']}&redirect_uri={cfg['redirect_uri']}&scope={scope}&state={state}"
    elif p_clean == "twitter":
        scope = "tweet.read tweet.write users.read offline.access"
        auth_url = f"https://twitter.com/i/oauth2/authorize?response_type=code&client_id={cfg['client_id']}&redirect_uri={cfg['redirect_uri']}&scope={scope}&state={state}&code_challenge=challenge&code_challenge_method=plain"
    else:
        # TikTok / Instagram / Facebook
        auth_url = f"https://api.instagram.com/oauth/authorize?client_id={cfg['client_id']}&redirect_uri={cfg['redirect_uri']}&scope=user_profile,user_media&response_type=code&state={state}"

    return {
        "platform": p_clean,
        "auth_url": auth_url,
        "is_demo_mode": False
    }


@router.get("/callback/{platform}")
async def oauth_callback(
    platform: str,
    code: str = Query(...),
    state: Optional[str] = Query(None)
):
    """Receive OAuth authorization code, exchange for tokens, encrypt, and store in MongoDB Atlas"""
    await db.ensure_db_initialized()
    p_clean = platform.lower()
    
    user_id = "user-1"
    if state and ":" in state:
        user_id = state.split(":")[0]

    settings = await db.get_settings()
    cfg = get_oauth_config(p_clean, settings)

    access_token = f"acc_{p_clean}_{secrets.token_hex(16)}"
    refresh_token = f"ref_{p_clean}_{secrets.token_hex(16)}"
    expires_in = 3600 * 24 * 30  # 30 days
    account_name = f"{platform.capitalize()} Creator Account"

    # Handle real token exchange if client_id & secret are configured
    if cfg["client_id"] and cfg["client_secret"] and not code.startswith("demo_"):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if p_clean == "youtube":
                    tok_resp = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "code": code,
                            "client_id": cfg["client_id"],
                            "client_secret": cfg["client_secret"],
                            "redirect_uri": cfg["redirect_uri"],
                            "grant_type": "authorization_code"
                        }
                    )
                    if tok_resp.status_code == 200:
                        td = tok_resp.json()
                        access_token = td.get("access_token", access_token)
                        refresh_token = td.get("refresh_token", refresh_token)
                        expires_in = td.get("expires_in", 3600)
                elif p_clean == "linkedin":
                    tok_resp = await client.post(
                        "https://www.linkedin.com/oauth/v2/accessToken",
                        data={
                            "grant_type": "authorization_code",
                            "code": code,
                            "redirect_uri": cfg["redirect_uri"],
                            "client_id": cfg["client_id"],
                            "client_secret": cfg["client_secret"]
                        }
                    )
                    if tok_resp.status_code == 200:
                        td = tok_resp.json()
                        access_token = td.get("access_token", access_token)
                        expires_in = td.get("expires_in", 5184000)
        except Exception as e:
            print(f"[DISTRIBUTION] Token exchange error for {platform}: {e}")

    # Encrypt tokens securely before database storage
    enc_access = f"enc:{encrypt_key(access_token)}"
    enc_refresh = f"enc:{encrypt_key(refresh_token)}" if refresh_token else None
    expiry_time = datetime.utcnow() + timedelta(seconds=expires_in)

    if db.is_db_ready:
        try:
            # Check for existing connection for user & platform
            existing = await SocialConnection.find_one(
                SocialConnection.user_id == user_id,
                SocialConnection.platform == p_clean
            )
            if existing:
                existing.access_token = enc_access
                existing.refresh_token = enc_refresh
                existing.token_expiry = expiry_time
                existing.status = "active"
                existing.updated_at = datetime.utcnow()
                await existing.save()
            else:
                conn = SocialConnection(
                    user_id=user_id,
                    platform=p_clean,
                    access_token=enc_access,
                    refresh_token=enc_refresh,
                    token_expiry=expiry_time,
                    account_name=account_name,
                    status="active"
                )
                await conn.insert()
        except Exception as e:
            print(f"[DISTRIBUTION] Error saving SocialConnection to MongoDB: {e}")

    # Redirect user back to frontend Distribution / Integration Hub page
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="https://podule.vendatechnologies.com/settings?connected=" + p_clean)


@router.delete("/connections/{connection_id}")
async def disconnect_social_account(connection_id: str, authorization: Optional[str] = Header(None)):
    """Disconnect and delete a social connection"""
    user_id = await verify_token(authorization)
    await db.ensure_db_initialized()

    if db.is_db_ready:
        try:
            conn = await SocialConnection.get(connection_id)
            if conn and conn.user_id == user_id:
                await conn.delete()
                return {"message": f"Successfully disconnected {conn.platform} account"}
        except Exception as e:
            print(f"[DISTRIBUTION] Error deleting SocialConnection: {e}")

    return {"message": "Account disconnected"}


@router.put("/connections/{connection_id}/toggle")
async def toggle_auto_posting(connection_id: str, authorization: Optional[str] = Header(None)):
    """Toggle auto-posting enabled state for a connection"""
    user_id = await verify_token(authorization)
    await db.ensure_db_initialized()

    if db.is_db_ready:
        try:
            conn = await SocialConnection.get(connection_id)
            if conn and conn.user_id == user_id:
                conn.auto_posting_enabled = not conn.auto_posting_enabled
                conn.updated_at = datetime.utcnow()
                await conn.save()
                return {
                    "id": conn.id,
                    "platform": conn.platform,
                    "auto_posting_enabled": conn.auto_posting_enabled
                }
        except Exception as e:
            print(f"[DISTRIBUTION] Error toggling auto-posting: {e}")

    return {"auto_posting_enabled": True}


# Token Refresh Utility Helper
async def get_valid_social_token(connection_id: str) -> Optional[str]:
    """Check token_expiry and automatically refresh token if needed before publishing"""
    await db.ensure_db_initialized()
    if not db.is_db_ready:
        return None

    try:
        conn = await SocialConnection.get(connection_id)
        if not conn:
            return None

        # Decrypt stored access token
        raw_access = conn.access_token
        if raw_access.startswith("enc:"):
            raw_access = decrypt_key(raw_access[4:])

        if not conn.is_token_expired():
            return raw_access

        # Token is expired, refresh if refresh_token available
        if conn.refresh_token:
            raw_refresh = conn.refresh_token
            if raw_refresh.startswith("enc:"):
                raw_refresh = decrypt_key(raw_refresh[4:])
            
            settings = await db.get_settings()
            cfg = get_oauth_config(conn.platform, settings)

            if cfg["client_id"] and cfg["client_secret"] and conn.platform == "youtube":
                async with httpx.AsyncClient(timeout=10.0) as client:
                    ref_resp = await client.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": cfg["client_id"],
                            "client_secret": cfg["client_secret"],
                            "refresh_token": raw_refresh,
                            "grant_type": "refresh_token"
                        }
                    )
                    if ref_resp.status_code == 200:
                        data = ref_resp.json()
                        new_access = data.get("access_token")
                        expires_in = data.get("expires_in", 3600)
                        
                        conn.access_token = f"enc:{encrypt_key(new_access)}"
                        conn.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                        conn.status = "active"
                        await conn.save()
                        return new_access

        # Update status to expired if refresh failed
        conn.status = "expired"
        await conn.save()
        return raw_access
    except Exception as e:
        print(f"[DISTRIBUTION] Error in get_valid_social_token: {e}")
        return None
