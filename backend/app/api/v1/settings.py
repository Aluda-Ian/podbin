from fastapi import APIRouter
from fastapi.responses import RedirectResponse
from typing import Dict, Any, List, Optional
from app.services.db import db
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
    # Mask or decrypt custom_api_key in secure operations if needed
    config = settings.get("provider_config", {
        "tier": "PLATFORM_FREE",
        "custom_api_key": None,
        "custom_provider": None
    })
    return config

@router.post("/provider-config", response_model=ProviderConfig)
async def update_provider_config(payload: ProviderConfig):
    await db.update_settings({"provider_config": payload.dict()})
    return payload

@router.get("/connect/facebook")
async def connect_facebook(origin: str = "http://localhost:5173"):
    client_id = os.getenv("FACEBOOK_CLIENT_ID", "483920194830201")
    callback_url = f"http://localhost:8000/api/v1/settings/callback/facebook?origin={origin}"
    encoded_callback = urllib.parse.quote(callback_url)
    
    fb_oauth_url = (
        f"https://www.facebook.com/v19.0/dialog/oauth"
        f"?client_id={client_id}"
        f"&redirect_uri={encoded_callback}"
        f"&state=facebook"
        f"&scope=pages_manage_posts,pages_read_engagement"
    )
    return RedirectResponse(url=fb_oauth_url)

@router.get("/callback/facebook")
async def callback_facebook(code: Optional[str] = None, state: Optional[str] = None, origin: str = "http://localhost:5173"):
    settings = await db.get_settings()
    integrations = settings.get("integrations", [])
    
    fb_exists = False
    new_integrations = []
    for item in integrations:
        if item.get("name") == "Facebook":
            new_integrations.append({
                "name": "Facebook",
                "status": "Connected",
                "color": "text-success"
            })
            fb_exists = True
        else:
            new_integrations.append(item)
            
    if not fb_exists:
        new_integrations.append({
            "name": "Facebook",
            "status": "Connected",
            "color": "text-success"
        })
        
    await db.update_settings({"integrations": new_integrations})
    return RedirectResponse(url=f"{origin}/settings?connected=Facebook")
