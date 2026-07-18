from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from typing import Dict, Any, Optional
from app.services.db import db
from datetime import datetime
import secrets
import os
import httpx

router = APIRouter()

PLATFORM_CONFIG: Dict[str, Dict[str, Any]] = {
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

REDIRECT_BASE = "http://localhost:8000/api/v1/integrations"

NAME_TO_KEY = {v["name"]: k for k, v in PLATFORM_CONFIG.items()}


@router.get("/{platform}/login")
async def platform_login(
    platform: str,
    origin: str = Query("http://localhost:5173"),
    mode: str = Query("sandbox"),
):
    key = platform.lower()
    cfg = PLATFORM_CONFIG.get(key)
    if not cfg:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    s = await db.get_settings()
    settings_data = s or {}
    creds = settings_data.get("integration_credentials", {})
    plat_creds = creds.get(key, {}) or {}
    client_id = plat_creds.get("client_id", "") or os.getenv(f"{key.upper()}_CLIENT_ID", "")

    if not client_id:
        raise HTTPException(status_code=400, detail=f"No OAuth client_id configured for {platform}")

    state = f"{mode}|{origin}|{secrets.token_urlsafe(16)}"

    merged_creds = dict(creds)
    merged_plat = dict(plat_creds)
    merged_plat["oauth_state"] = state
    merged_creds[key] = merged_plat
    await db.update_settings({"integration_credentials": merged_creds})

    redirect_uri = f"{REDIRECT_BASE}/{key}/callback"
    scopes = " ".join(cfg["scopes"])

    auth_url = (
        f"{cfg['auth_url']}"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope={scopes}"
        f"&state={state}"
    )

    return {"url": auth_url}


@router.get("/{platform}/callback")
async def platform_callback(
    platform: str,
    code: Optional[str] = None,
    state: Optional[str] = None,
    origin: str = Query("http://localhost:5173"),
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

        origin = "http://localhost:5173"
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
