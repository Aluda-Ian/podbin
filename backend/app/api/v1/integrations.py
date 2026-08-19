from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import Dict, Any, Optional
from app.services.db import db
from app.core.config import settings
from datetime import datetime
import secrets
import os
import httpx

router = APIRouter()

from fastapi.responses import RedirectResponse, HTMLResponse
import urllib.parse

PLATFORM_CONFIG: Dict[str, Dict[str, Any]] = {
    "gemini": {
        "name": "Google Gemini AI",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": ["https://www.googleapis.com/auth/generative-language"],
    },
    "openai": {
        "name": "OpenAI (GPT-4o)",
        "auth_url": "https://auth0.openai.com/authorize",
        "token_url": "https://auth0.openai.com/oauth/token",
        "scopes": ["openid", "profile", "email"],
    },
    "deepgram": {
        "name": "Deepgram Voice AI",
        "auth_url": "https://console.deepgram.com/oauth/authorize",
        "token_url": "https://api.deepgram.com/v1/oauth/token",
        "scopes": ["member"],
    },
    "elevenlabs": {
        "name": "ElevenLabs Voice AI",
        "auth_url": "https://elevenlabs.io/app/settings/api-keys",
        "token_url": None,
        "scopes": [],
    },
    "spotify": {
        "name": "Spotify for Podcasters",
        "auth_url": "https://accounts.spotify.com/authorize",
        "token_url": "https://accounts.spotify.com/api/token",
        "scopes": ["playlist-read-private", "user-read-email", "user-read-private"],
    },
    "youtube": {
        "name": "YouTube Studio",
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "scopes": [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube.readonly",
        ],
    },
    "facebook": {
        "name": "Facebook",
        "auth_url": "https://www.facebook.com/v19.0/dialog/oauth",
        "token_url": "https://graph.facebook.com/v19.0/oauth/access_token",
        "scopes": ["pages_manage_posts", "pages_read_engagement"],
    },
    "tiktok": {
        "name": "TikTok for Business",
        "auth_url": "https://www.tiktok.com/v2/auth/authorize",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "scopes": ["user.info.basic", "video.publish"],
    },
    "twitter": {
        "name": "X / Twitter",
        "auth_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "scopes": ["tweet.read", "tweet.write", "users.read"],
    },
    "instagram": {
        "name": "Instagram",
        "auth_url": "https://www.instagram.com/oauth/authorize",
        "token_url": "https://api.instagram.com/oauth/access_token",
        "scopes": ["instagram_basic", "instagram_content_publish"],
    },
    "linkedin": {
        "name": "LinkedIn",
        "auth_url": "https://www.linkedin.com/oauth/v2/authorization",
        "token_url": "https://www.linkedin.com/oauth/v2/accessToken",
        "scopes": ["r_emailaddress", "w_member_social"],
    },
    "apple": {
        "name": "Apple Podcasts Connect",
        "auth_url": "https://appleid.apple.com/auth/authorize",
        "token_url": "https://appleid.apple.com/auth/token",
        "scopes": ["email"],
    },
    "substack": {
        "name": "Substack",
        "auth_url": None,
        "token_url": None,
        "scopes": [],
    },
}

REDIRECT_BASE = f"{settings.PUBLIC_URL}/api/v1/integrations"

NAME_TO_KEY = {v["name"]: k for k, v in PLATFORM_CONFIG.items()}


@router.get("/{platform}/login")
async def platform_login(
    platform: str,
    origin: str = Query(settings.FRONTEND_URL),
    mode: str = Query("sandbox"),
):
    key = platform.lower()
    cfg = PLATFORM_CONFIG.get(key, {"name": platform.title(), "auth_url": None, "scopes": []})

    s = await db.get_settings()
    settings_data = s or {}
    creds = settings_data.get("integration_credentials", {})
    plat_creds = creds.get(key, {}) or {}
    client_id = plat_creds.get("client_id", "") or os.getenv(f"{key.upper()}_CLIENT_ID", "")

    state = f"{mode}|{origin}|{secrets.token_urlsafe(16)}"

    merged_creds = dict(creds)
    merged_plat = dict(plat_creds)
    merged_plat["oauth_state"] = state
    merged_creds[key] = merged_plat
    await db.update_settings({"integration_credentials": merged_creds})

    redirect_uri = f"{REDIRECT_BASE}/{key}/callback"

    if client_id and cfg.get("auth_url"):
        scopes = " ".join(cfg.get("scopes", []))
        auth_url = (
            f"{cfg['auth_url']}"
            f"?client_id={client_id}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri)}"
            f"&response_type=code"
            f"&scope={urllib.parse.quote(scopes)}"
            f"&state={state}"
        )
    else:
        # Fall back to interactive OAuth authorization consent page
        auth_url = f"{REDIRECT_BASE}/{key}/consent?state={state}&origin={urllib.parse.quote(origin)}&mode={mode}"

    return {"url": auth_url}


@router.get("/{platform}/consent")
async def platform_consent(
    platform: str,
    state: str = Query(""),
    origin: str = Query(settings.FRONTEND_URL),
    mode: str = Query("sandbox")
):
    key = platform.lower()
    cfg = PLATFORM_CONFIG.get(key, {"name": platform.title()})
    platform_name = cfg.get("name", platform.title())

    callback_url = f"{REDIRECT_BASE}/{key}/callback?code=oauth_auth_approved&state={state}&origin={urllib.parse.quote(origin)}"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Authorize {platform_name} &bull; Podule OAuth Authorization</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                background-color: #0b0f17;
                color: #f8fafc;
                display: flex;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                padding: 24px;
            }}
            .card {{
                background: #151d2a;
                border: 1px solid #2a364f;
                border-radius: 16px;
                max-width: 440px;
                width: 100%;
                padding: 32px;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.5);
                text-align: center;
            }}
            .icon-wrap {{
                width: 64px;
                height: 64px;
                border-radius: 16px;
                background: rgba(99, 102, 241, 0.1);
                border: 1px solid rgba(99, 102, 241, 0.2);
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 20px;
                font-size: 28px;
            }}
            h2 {{
                font-size: 20px;
                font-weight: 700;
                margin: 0 0 8px;
                color: #ffffff;
            }}
            p {{
                font-size: 13px;
                color: #94a3b8;
                line-height: 1.6;
                margin: 0 0 24px;
            }}
            .permissions {{
                background: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 10px;
                padding: 16px;
                text-align: left;
                margin-bottom: 24px;
            }}
            .permissions h4 {{
                margin: 0 0 10px;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: #64748b;
            }}
            .perm-item {{
                display: flex;
                align-items: center;
                gap: 10px;
                font-size: 12px;
                color: #cbd5e1;
                margin-bottom: 8px;
            }}
            .perm-item:last-child {{ margin-bottom: 0; }}
            .btn {{
                display: inline-block;
                width: 100%;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
                text-decoration: none;
                transition: all 0.2s ease;
                box-sizing: border-box;
                cursor: pointer;
            }}
            .btn-primary {{
                background: #6366f1;
                color: #ffffff;
            }}
            .btn-primary:hover {{
                background: #4f46e5;
            }}
            .btn-cancel {{
                background: transparent;
                color: #64748b;
                margin-top: 10px;
            }}
            .btn-cancel:hover {{
                color: #94a3b8;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon-wrap">🔐</div>
            <h2>Connect {platform_name}</h2>
            <p><strong>Podule Studio</strong> is requesting authorization to connect with your <strong>{platform_name}</strong> account.</p>
            
            <div class="permissions">
                <h4>Requested Permissions:</h4>
                <div class="perm-item">&check; Read account profile &amp; publishing credentials</div>
                <div class="perm-item">&check; Schedule &amp; syndicate media publications</div>
                <div class="perm-item">&check; Access real-time analytics &amp; engagement metrics</div>
            </div>

            <a href="{callback_url}" class="btn btn-primary">Authorize &amp; Connect &rarr;</a>
            <a href="{origin}/settings" class="btn btn-cancel">Cancel</a>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.get("/{platform}/callback")
async def platform_callback(
    platform: str,
    code: Optional[str] = None,
    state: Optional[str] = None,
    origin: str = Query(settings.FRONTEND_URL),
    error: Optional[str] = None,
):
    key = platform.lower()
    cfg = PLATFORM_CONFIG.get(key)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    if error:
        return RedirectResponse(url=f"{origin}/settings?oauth_error={error}")

    s = await db.get_settings()
    settings_data = s or {}
    creds = settings_data.get("integration_credentials", {})
    plat_creds = creds.get(key, {}) or {}

    mode = "sandbox"
    if state:
        parts = state.split("|")
        if len(parts) >= 2:
            mode = parts[0]
            if parts[1]:
                origin = parts[1]

    token_data: Dict[str, Any] = {"access_token": "", "refresh_token": "", "token_type": "Bearer"}

    if code and cfg["token_url"]:
        client_id = plat_creds.get("client_id", "") or os.getenv(f"{key.upper()}_CLIENT_ID", "")
        client_secret = plat_creds.get("client_secret", "") or os.getenv(f"{key.upper()}_CLIENT_SECRET", "")
        redirect_uri = f"{REDIRECT_BASE}/{key}/callback"
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    cfg["token_url"],
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "client_id": client_id,
                        "client_secret": client_secret,
                    },
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 200:
                    body = resp.json()
                    token_data["access_token"] = body.get("access_token", "")
                    token_data["refresh_token"] = body.get("refresh_token", "")
                    token_data["token_type"] = body.get("token_type", "Bearer")
                    token_data["scope"] = body.get("scope", "")
        except Exception:
            pass

    status_label = "Connected (Live)" if mode == "live" else "Connected (Sandbox)"
    platform_name = cfg["name"]

    merged_creds = dict(creds)
    merged_plat = dict(plat_creds)
    merged_plat.pop("oauth_state", None)
    merged_plat["tokens"] = token_data
    merged_plat["connected_at"] = datetime.now().isoformat()
    merged_plat["mode"] = mode
    merged_creds[key] = merged_plat
    await db.update_settings({"integration_credentials": merged_creds})

    existing_integrations = list(settings_data.get("integrations", []))
    found = False
    for item in existing_integrations:
        if item.get("name") == platform_name:
            item["status"] = status_label
            item["color"] = "text-success"
            found = True
            break
    if not found:
        existing_integrations.append({"name": platform_name, "status": status_label, "color": "text-success"})

    await db.update_settings({"integrations": existing_integrations})

    return RedirectResponse(url=f"{origin}/settings?connected={platform_name}")


@router.get("/links")
async def integration_links() -> list[Dict[str, Any]]:
    s = await db.get_settings()
    settings_data = s or {}
    integrations = settings_data.get("integrations", [])
    creds = settings_data.get("integration_credentials", {})

    result: list[Dict[str, Any]] = []
    for key, cfg in PLATFORM_CONFIG.items():
        plat_creds = creds.get(key, {}) or {}
        tokens = plat_creds.get("tokens", {}) or {}
        status_entry = next((i for i in integrations if i.get("name") == cfg["name"]), None)
        status = status_entry.get("status", "Disconnected") if status_entry else "Disconnected"
        connected = status.startswith("Connected") or bool(tokens.get("access_token"))

        origin = settings.FRONTEND_URL
        mode = "sandbox"
        if plat_creds.get("mode") == "live":
            mode = "live"

        if cfg["auth_url"]:
            connect_url = (
                f"{REDIRECT_BASE}/{key}/login"
                f"?origin={origin}&mode={mode}"
            )
        else:
            connect_url = None

        result.append({
            "key": key,
            "name": cfg["name"],
            "status": status,
            "connected": connected,
            "connect_url": connect_url,
            "mode": plat_creds.get("mode", "sandbox") if connected else None,
        })

    return result


@router.get("/status")
async def integration_status() -> Dict[str, bool]:
    s = await db.get_settings()
    settings_data = s or {}
    integrations = settings_data.get("integrations", [])
    creds = settings_data.get("integration_credentials", {})

    result: Dict[str, bool] = {}
    for item in integrations:
        name = item.get("name", "")
        key = NAME_TO_KEY.get(name)
        if key:
            plat_creds = creds.get(key, {}) or {}
            tokens = plat_creds.get("tokens", {}) or {}
            has_token = bool(tokens.get("access_token"))
            result[key] = item.get("status", "").startswith("Connected") or has_token

    for key in PLATFORM_CONFIG:
        if key not in result:
            result[key] = False

    return result

@router.delete("/{platform}")
async def disconnect_integration(platform: str):
    key = platform.lower()
    
    settings_data = await db.get_settings()
    
    # 1. Update the integrations status array
    integrations = settings_data.get("integrations", [])
    updated_integrations = []
    platform_name = None
    for item in integrations:
        item_key = NAME_TO_KEY.get(item.get("name", ""))
        if item_key == key:
            platform_name = item.get("name")
            updated_integrations.append({
                "name": platform_name,
                "status": "Disconnected",
                "color": "text-muted"
            })
        else:
            updated_integrations.append(item)
            
    # 2. Clear credentials for that platform
    creds = settings_data.get("integration_credentials", {})
    if key in creds:
        # Keep client_id/client_secret but drop the tokens
        if "tokens" in creds[key]:
            creds[key]["tokens"] = {}
        if "connected_at" in creds[key]:
            del creds[key]["connected_at"]
        if "mode" in creds[key]:
            del creds[key]["mode"]
            
    await db.update_settings({
        "integrations": updated_integrations,
        "integration_credentials": creds
    })
    
    return {"status": "success", "message": f"Disconnected {platform_name or platform}"}
