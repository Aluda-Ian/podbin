from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from typing import Dict, Any, List, Optional
from app.services.db import db, encrypt_key, decrypt_key
from pydantic import BaseModel
from app.models.user import ProviderConfig
import urllib.parse
import os

router = APIRouter()

class IntegrationItem(BaseModel):
    name: str
    status: str
    color: str

class SettingsUpdate(BaseModel):
    workspaceName: Optional[str] = None
    showName: Optional[str] = None
    primaryHost: Optional[str] = None
    releaseCadence: Optional[str] = None
    autonomyLevel: Optional[str] = None
    integrations: Optional[List[IntegrationItem]] = None
    provider_config: Optional[ProviderConfig] = None

@router.get("/")
async def get_settings():
    return await db.get_settings()

@router.put("/")
async def update_settings(payload: SettingsUpdate):
    upd = {k: v for k, v in payload.dict().items() if v is not None}
    return await db.update_settings(upd)

@router.get("/provider-config", response_model=ProviderConfig)
async def get_provider_config():
    settings = await db.get_settings()
    config = settings.get("provider_config") or {
        "tier": "PLATFORM_FREE",
        "custom_api_key": None,
        "custom_provider": None
    }
    # Make a copy to avoid mutating cache in place, then decrypt
    config_dict = dict(config)
    if config_dict.get("custom_api_key"):
        config_dict["custom_api_key"] = decrypt_key(config_dict["custom_api_key"])
    return config_dict

@router.post("/provider-config", response_model=ProviderConfig)
async def update_provider_config(payload: ProviderConfig):
    config_dict = payload.dict()
    if config_dict.get("custom_api_key"):
        config_dict["custom_api_key"] = encrypt_key(config_dict["custom_api_key"])
    await db.update_settings({"provider_config": config_dict})
    return payload

@router.get("/connect/{platform}")
async def connect_platform(platform: str, mode: str = "sandbox", origin: str = "http://localhost:5173"):
    platform_key = platform.lower()
    settings_data = await db.get_settings()
    creds = settings_data.get("integration_credentials", {})
    plat_creds = creds.get(platform_key, {})
    client_id = plat_creds.get("client_id")
    
    if mode == "live":
        if platform_key == "facebook":
            cid = client_id or "483920194830201"
            callback_url = f"http://localhost:8000/api/v1/settings/callback/facebook?origin={origin}&mode=live"
            encoded_callback = urllib.parse.quote(callback_url)
            fb_oauth_url = (
                f"https://www.facebook.com/v19.0/dialog/oauth"
                f"?client_id={cid}"
                f"&redirect_uri={encoded_callback}"
                f"&state=facebook"
                f"&scope=pages_manage_posts,pages_read_engagement"
            )
            return RedirectResponse(url=fb_oauth_url)
        else:
            callback_url = f"http://localhost:8000/api/v1/settings/callback/{platform}?origin={origin}&mode=live"
            return RedirectResponse(url=callback_url)
    else:
        callback_url = f"http://localhost:8000/api/v1/settings/callback/{platform}?origin={origin}&mode=sandbox"
        return RedirectResponse(url=callback_url)

@router.get("/callback/{platform}")
async def callback_platform(
    platform: str,
    code: Optional[str] = None,
    state: Optional[str] = None,
    mode: str = "sandbox",
    origin: str = "http://localhost:5173"
):
    platform_map = {
        "facebook": "Facebook",
        "spotify": "Spotify for Podcasters",
        "apple": "Apple Podcasts Connect",
        "youtube": "YouTube Studio",
        "tiktok": "TikTok for Business",
        "twitter": "X / Twitter",
        "substack": "Substack",
        "linkedin": "LinkedIn",
        "instagram": "Instagram"
    }
    
    platform_key = platform.lower()
    platform_name = platform_map.get(platform_key, platform.capitalize())
    
    settings_data = await db.get_settings()
    integrations = settings_data.get("integrations", [])
    
    status_label = "Connected (Live)" if mode == "live" else "Connected (Sandbox)"
    
    exists = False
    new_integrations = []
    for item in integrations:
        if item.get("name") == platform_name:
            new_integrations.append({
                "name": platform_name,
                "status": status_label,
                "color": "text-success"
            })
            exists = True
        else:
            new_integrations.append(item)
            
    if not exists:
        new_integrations.append({
            "name": platform_name,
            "status": status_label,
            "color": "text-success"
        })
        
    await db.update_settings({"integrations": new_integrations})
    return RedirectResponse(url=f"{origin}/settings?connected={platform_name}")
