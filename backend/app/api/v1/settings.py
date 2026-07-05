from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import RedirectResponse
from typing import Dict, Any, List, Optional
from app.services.db import db, encrypt_key, decrypt_key
from pydantic import BaseModel
from app.models.user import ProviderConfig
from app.core.security import verify_token, validate_api_key_format
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
    api_storage_target: Optional[str] = None
    integration_credentials: Optional[Dict[str, Any]] = None

class APIKeysPayload(BaseModel):
    deepgram: Optional[str] = ""
    openai: Optional[str] = ""
    elevenlabs: Optional[str] = ""

class IntegrationCredentialItem(BaseModel):
    client_id: Optional[str] = ""
    client_secret: Optional[str] = ""

class IntegrationCredentialsPayload(BaseModel):
    facebook: Optional[IntegrationCredentialItem] = None
    spotify: Optional[IntegrationCredentialItem] = None
    youtube: Optional[IntegrationCredentialItem] = None
    tiktok: Optional[IntegrationCredentialItem] = None
    twitter: Optional[IntegrationCredentialItem] = None
    instagram: Optional[IntegrationCredentialItem] = None
    linkedin: Optional[IntegrationCredentialItem] = None
    global_sandbox_mode: Optional[bool] = True

class APIConnectionsPayload(BaseModel):
    api_storage_target: str # "database" or "env"
    api_keys: APIKeysPayload
    integration_credentials: IntegrationCredentialsPayload

@router.get("/")
async def get_settings(authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    return await db.get_settings()

@router.put("/")
async def update_settings(payload: SettingsUpdate, authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    upd = {k: v for k, v in payload.dict().items() if v is not None}
    return await db.update_settings(upd)

@router.get("/provider-config", response_model=ProviderConfig)
async def get_provider_config(authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
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
async def update_provider_config(payload: ProviderConfig, authorization: Optional[str] = Header(None)):
    """
    Update provider config with validation for custom API keys
    """
    user_id = await verify_token(authorization)
    config_dict = payload.dict()
    
    # If using BYO_KEY tier, validate the custom API key
    if payload.tier == "BYO_KEY" and payload.custom_api_key:
        # Determine provider type to validate correctly
        provider_type = payload.custom_provider or "openai"
        is_valid, error_msg = await validate_api_key_format(provider_type.lower(), payload.custom_api_key)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid custom API key: {error_msg}"
            )
    
    if config_dict.get("custom_api_key"):
        config_dict["custom_api_key"] = encrypt_key(config_dict["custom_api_key"])
    await db.update_settings({"provider_config": config_dict})
    return payload

@router.get("/api-connections")
async def get_api_connections(authorization: Optional[str] = Header(None)):
    settings_data = await db.get_settings()
    storage_target = settings_data.get("api_storage_target") or "database"
    
    # Load API Keys
    if storage_target == "env":
        from app.services.env_manager import read_env_file
        env_keys = read_env_file()
        openai_key = env_keys.get("OPENAI_API_KEY", "")
        deepgram_key = env_keys.get("DEEPGRAM_API_KEY", "")
        elevenlabs_key = env_keys.get("ELEVENLABS_API_KEY", "")
    else:
        db_keys = await db.get_api_keys()
        openai_key = db_keys.get("openai", "")
        deepgram_key = db_keys.get("deepgram", "")
        elevenlabs_key = db_keys.get("elevenlabs", "")

    # Load Integration Credentials
    if storage_target == "env":
        from app.services.env_manager import read_env_file
        env_keys = read_env_file()
        integration_creds = {
            "global_sandbox_mode": settings_data.get("integration_credentials", {}).get("global_sandbox_mode", True),
            "facebook": {"client_id": env_keys.get("FACEBOOK_CLIENT_ID", ""), "client_secret": env_keys.get("FACEBOOK_CLIENT_SECRET", "")},
            "spotify": {"client_id": env_keys.get("SPOTIFY_CLIENT_ID", ""), "client_secret": env_keys.get("SPOTIFY_CLIENT_SECRET", "")},
            "youtube": {"client_id": env_keys.get("YOUTUBE_CLIENT_ID", ""), "client_secret": env_keys.get("YOUTUBE_CLIENT_SECRET", "")},
            "tiktok": {"client_id": env_keys.get("TIKTOK_CLIENT_ID", ""), "client_secret": env_keys.get("TIKTOK_CLIENT_SECRET", "")},
            "twitter": {"client_id": env_keys.get("TWITTER_CLIENT_ID", ""), "client_secret": env_keys.get("TWITTER_CLIENT_SECRET", "")},
            "instagram": {"client_id": env_keys.get("INSTAGRAM_CLIENT_ID", ""), "client_secret": env_keys.get("INSTAGRAM_CLIENT_SECRET", "")},
            "linkedin": {"client_id": env_keys.get("LINKEDIN_CLIENT_ID", ""), "client_secret": env_keys.get("LINKEDIN_CLIENT_SECRET", "")},
        }
    else:
        db_creds = settings_data.get("integration_credentials") or {}
        integration_creds = {
            "global_sandbox_mode": db_creds.get("global_sandbox_mode", True),
            "facebook": {"client_id": db_creds.get("facebook", {}).get("client_id", ""), "client_secret": db_creds.get("facebook", {}).get("client_secret", "")},
            "spotify": {"client_id": db_creds.get("spotify", {}).get("client_id", ""), "client_secret": db_creds.get("spotify", {}).get("client_secret", "")},
            "youtube": {"client_id": db_creds.get("youtube", {}).get("client_id", ""), "client_secret": db_creds.get("youtube", {}).get("client_secret", "")},
            "tiktok": {"client_id": db_creds.get("tiktok", {}).get("client_id", ""), "client_secret": db_creds.get("tiktok", {}).get("client_secret", "")},
            "twitter": {"client_id": db_creds.get("twitter", {}).get("client_id", ""), "client_secret": db_creds.get("twitter", {}).get("client_secret", "")},
            "instagram": {"client_id": db_creds.get("instagram", {}).get("client_id", ""), "client_secret": db_creds.get("instagram", {}).get("client_secret", "")},
            "linkedin": {"client_id": db_creds.get("linkedin", {}).get("client_id", ""), "client_secret": db_creds.get("linkedin", {}).get("client_secret", "")},
        }

    # Mask values
    masked_api_keys = {
        "openai": f"sk-...{openai_key[-4:]}" if openai_key else "",
        "deepgram": f"dg-...{deepgram_key[-4:]}" if deepgram_key else "",
        "elevenlabs": f"el-...{elevenlabs_key[-4:]}" if elevenlabs_key else "",
    }
    
    masked_integration_creds = dict(integration_creds)
    for plat in ["facebook", "spotify", "youtube", "tiktok", "twitter", "instagram", "linkedin"]:
        plat_data = masked_integration_creds.get(plat) or {}
        cid = plat_data.get("client_id", "")
        csec = plat_data.get("client_secret", "")
        masked_integration_creds[plat] = {
            "client_id": cid,
            "client_secret": f"[masked-{csec[-4:]}]" if csec else ""
        }

    return {
        "api_storage_target": storage_target,
        "api_keys": masked_api_keys,
        "integration_credentials": masked_integration_creds
    }

@router.post("/api-connections")
async def update_api_connections(payload: APIConnectionsPayload, authorization: Optional[str] = Header(None)):
    """
    Update API connections with validation of API keys
    """
    user_id = await verify_token(authorization)
    settings_data = await db.get_settings()
    current_storage_target = settings_data.get("api_storage_target") or "database"
    
    db_keys = await db.get_api_keys()
    
    from app.services.env_manager import read_env_file, update_env_file
    env_keys = read_env_file()
    
    # Validate and resolve OpenAI API Key
    openai_in = payload.api_keys.openai
    if openai_in and not openai_in.startswith("sk-..."):
        is_valid, error_msg = await validate_api_key_format("openai", openai_in)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OpenAI API key: {error_msg}"
            )
        openai_resolved = openai_in
    elif openai_in and openai_in.startswith("sk-..."):
        openai_resolved = env_keys.get("OPENAI_API_KEY", "") if current_storage_target == "env" else db_keys.get("openai", "")
    else:
        openai_resolved = ""
        
    # Validate and resolve Deepgram API Key
    deepgram_in = payload.api_keys.deepgram
    if deepgram_in and not deepgram_in.startswith("dg-..."):
        is_valid, error_msg = await validate_api_key_format("deepgram", deepgram_in)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Deepgram API key: {error_msg}"
            )
        deepgram_resolved = deepgram_in
    elif deepgram_in and deepgram_in.startswith("dg-..."):
        deepgram_resolved = env_keys.get("DEEPGRAM_API_KEY", "") if current_storage_target == "env" else db_keys.get("deepgram", "")
    else:
        deepgram_resolved = ""
        
    # Validate and resolve Elevenlabs API Key
    elevenlabs_in = payload.api_keys.elevenlabs
    if elevenlabs_in and not elevenlabs_in.startswith("el-..."):
        is_valid, error_msg = await validate_api_key_format("elevenlabs", elevenlabs_in)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid ElevenLabs API key: {error_msg}"
            )
        elevenlabs_resolved = elevenlabs_in
    elif elevenlabs_in and elevenlabs_in.startswith("el-..."):
        elevenlabs_resolved = env_keys.get("ELEVENLABS_API_KEY", "") if current_storage_target == "env" else db_keys.get("elevenlabs", "")
    else:
        elevenlabs_resolved = ""

    # Resolve Integration Credentials
    db_creds = settings_data.get("integration_credentials") or {}
    
    resolved_integration_creds = {
        "global_sandbox_mode": payload.integration_credentials.global_sandbox_mode
    }
    
    platforms = ["facebook", "spotify", "youtube", "tiktok", "twitter", "instagram", "linkedin"]
    for plat in platforms:
        plat_in = getattr(payload.integration_credentials, plat, None)
        if not plat_in:
            continue
            
        client_id_in = plat_in.client_id or ""
        client_secret_in = plat_in.client_secret or ""
        
        # Check if secret is masked
        if client_secret_in and client_secret_in.startswith("[masked"):
            client_secret_resolved = env_keys.get(f"{plat.upper()}_CLIENT_SECRET", "") if current_storage_target == "env" else db_creds.get(plat, {}).get("client_secret", "")
        else:
            client_secret_resolved = client_secret_in
            
        resolved_integration_creds[plat] = {
            "client_id": client_id_in,
            "client_secret": client_secret_resolved
        }

    new_storage_target = payload.api_storage_target
    
    if new_storage_target == "database":
        # Save to DB
        await db.update_settings({
            "api_storage_target": "database",
            "integration_credentials": resolved_integration_creds
        })
        await db.update_api_keys({
            "openai": openai_resolved,
            "deepgram": deepgram_resolved,
            "elevenlabs": elevenlabs_resolved
        })
    elif new_storage_target == "env":
        # Save to Env file
        env_updates = {
            "OPENAI_API_KEY": openai_resolved,
            "DEEPGRAM_API_KEY": deepgram_resolved,
            "ELEVENLABS_API_KEY": elevenlabs_resolved,
        }
        for plat in platforms:
            plat_data = resolved_integration_creds.get(plat) or {}
            env_updates[f"{plat.upper()}_CLIENT_ID"] = plat_data.get("client_id", "")
            env_updates[f"{plat.upper()}_CLIENT_SECRET"] = plat_data.get("client_secret", "")
            
        update_env_file(env_updates)
        
        await db.update_settings({
            "api_storage_target": "env",
            "integration_credentials": {
                "global_sandbox_mode": payload.integration_credentials.global_sandbox_mode
            }
        })

    return {"message": "API Connections updated successfully", "api_storage_target": new_storage_target}

@router.get("/connect/{platform}")
async def connect_platform(platform: str, mode: str = "sandbox", origin: str = "http://localhost:5173", authorization: Optional[str] = Header(None)):
    platform_key = platform.lower()
    settings_data = await db.get_settings()
    creds = settings_data.get("integration_credentials", {})
    plat_creds = creds.get(platform_key, {}) or {}
    
    # Try database value, fallback to environment variable
    client_id = plat_creds.get("client_id") or os.getenv(f"{platform_key.upper()}_CLIENT_ID")
    
    if mode == "live":
        if platform_key == "facebook":
            cid = client_id or os.getenv("FACEBOOK_CLIENT_ID") or "483920194830201"
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

