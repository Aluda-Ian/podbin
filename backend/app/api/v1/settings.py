from fastapi import APIRouter, Header, HTTPException, status
from fastapi.responses import RedirectResponse
from typing import Dict, Any, List, Optional
from app.services.db import db, encrypt_key, decrypt_key
from pydantic import BaseModel
from app.models.user import ProviderConfig
from app.core.security import verify_token, validate_api_key_format, verify_admin_token
import urllib.parse
import os

router = APIRouter()

class IntegrationItem(BaseModel):
    name: str
    status: str
    color: str

class SMTPConfig(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = 587
    username: Optional[str] = None
    password: Optional[str] = None
    from_email: Optional[str] = None

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
    operational_tier: Optional[str] = None
    orchestrator_model: Optional[str] = None
    transcription_model: Optional[str] = None
    tts_model: Optional[str] = None
    image_model: Optional[str] = None
    video_model: Optional[str] = None
    avatar_model: Optional[str] = None
    smtp: Optional[SMTPConfig] = None

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

class TestProviderPayload(BaseModel):
    provider: str
    api_key: str

@router.get("/")
async def get_settings(authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    return await db.get_settings()

@router.put("/")
async def update_settings(payload: SettingsUpdate, authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    upd = {k: v for k, v in payload.dict().items() if v is not None}
    return await db.update_settings(upd)

@router.post("/")
async def update_settings_post(payload: SettingsUpdate, authorization: Optional[str] = Header(None)):
    return await update_settings(payload, authorization)

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
    admin_user = await verify_admin_token(authorization)
    settings_data = await db.get_settings()
    storage_target = settings_data.get("api_storage_target") or "database"
    
    # Load API Keys from DB and Env (merged)
    from app.services.env_manager import read_env_file
    env_keys = read_env_file()
    db_keys = await db.get_api_keys()

    openai_key = db_keys.get("openai") or env_keys.get("OPENAI_API_KEY", "")
    deepgram_key = db_keys.get("deepgram") or env_keys.get("DEEPGRAM_API_KEY", "")
    elevenlabs_key = db_keys.get("elevenlabs") or env_keys.get("ELEVENLABS_API_KEY", "")

    # Load Integration Credentials
    db_creds = settings_data.get("integration_credentials") or {}
    if not isinstance(db_creds, dict): db_creds = {}

    platforms = ["facebook", "spotify", "youtube", "tiktok", "twitter", "instagram", "linkedin"]
    integration_creds = {
        "global_sandbox_mode": db_creds.get("global_sandbox_mode", True)
    }
    for plat in platforms:
        plat_db = db_creds.get(plat) or {}
        c_id = plat_db.get("client_id") or env_keys.get(f"{plat.upper()}_CLIENT_ID", "")
        c_sec = plat_db.get("client_secret") or env_keys.get(f"{plat.upper()}_CLIENT_SECRET", "")
        integration_creds[plat] = {"client_id": c_id, "client_secret": c_sec}

    return {
        "api_storage_target": storage_target,
        "api_keys": {
            "openai": openai_key,
            "deepgram": deepgram_key,
            "elevenlabs": elevenlabs_key,
        },
        "integration_credentials": integration_creds
    }

@router.post("/api-connections")
async def update_api_connections(payload: APIConnectionsPayload, authorization: Optional[str] = Header(None)):
    """
    Update API connections with validation and dual DB + Env persistence
    """
    admin_user = await verify_admin_token(authorization)
    settings_data = await db.get_settings()
    
    db_keys = await db.get_api_keys()
    from app.services.env_manager import read_env_file, update_env_file
    env_keys = read_env_file()
    
    current_openai = db_keys.get("openai") or env_keys.get("OPENAI_API_KEY", "")
    current_deepgram = db_keys.get("deepgram") or env_keys.get("DEEPGRAM_API_KEY", "")
    current_elevenlabs = db_keys.get("elevenlabs") or env_keys.get("ELEVENLABS_API_KEY", "")

    def is_masked_or_empty(val: Optional[str]) -> bool:
        if not val: return True
        val_str = str(val).strip()
        return "..." in val_str or "[masked]" in val_str or val_str.startswith(("sk-...", "dg-...", "el-..."))

    # Resolve OpenAI Key
    openai_in = payload.api_keys.openai
    if is_masked_or_empty(openai_in):
        openai_resolved = current_openai
    else:
        openai_resolved = openai_in.strip()

    # Resolve Deepgram Key
    deepgram_in = payload.api_keys.deepgram
    if is_masked_or_empty(deepgram_in):
        deepgram_resolved = current_deepgram
    else:
        deepgram_resolved = deepgram_in.strip()

    # Resolve ElevenLabs Key
    elevenlabs_in = payload.api_keys.elevenlabs
    if is_masked_or_empty(elevenlabs_in):
        elevenlabs_resolved = current_elevenlabs
    else:
        elevenlabs_resolved = elevenlabs_in.strip()

    # Deep Merge Integration Credentials
    db_creds = settings_data.get("integration_credentials") or {}
    if not isinstance(db_creds, dict): db_creds = {}

    resolved_integration_creds = dict(db_creds)
    resolved_integration_creds["global_sandbox_mode"] = payload.integration_credentials.global_sandbox_mode

    platforms = ["facebook", "spotify", "youtube", "tiktok", "twitter", "instagram", "linkedin"]
    for plat in platforms:
        plat_in = getattr(payload.integration_credentials, plat, None)
        existing_plat = resolved_integration_creds.get(plat) or {}
        if plat_in:
            c_id = plat_in.client_id if (plat_in.client_id is not None and not is_masked_or_empty(plat_in.client_id)) else existing_plat.get("client_id", "")
            c_sec = plat_in.client_secret if (plat_in.client_secret is not None and not is_masked_or_empty(plat_in.client_secret)) else existing_plat.get("client_secret", "")
            resolved_integration_creds[plat] = {"client_id": c_id, "client_secret": c_sec}

    new_storage_target = payload.api_storage_target or "database"

    # Always persist to both DB and Env so entries never disappear
    await db.update_settings({
        "api_storage_target": new_storage_target,
        "integration_credentials": resolved_integration_creds
    })
    await db.update_api_keys({
        "openai": openai_resolved,
        "deepgram": deepgram_resolved,
        "elevenlabs": elevenlabs_resolved
    })

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

    return {"message": "API Connections updated successfully", "api_storage_target": new_storage_target}

@router.post("/test-connection")
async def test_provider_connection(payload: TestProviderPayload, authorization: Optional[str] = Header(None)):
    user_id = await verify_token(authorization)
    
    provider = payload.provider.lower()
    api_key = payload.api_key.strip()
    
    def is_masked(val: str) -> bool:
        if not val: return True
        return "..." in val or "[masked]" in val or val.startswith(("sk-...", "dg-...", "el-..."))

    # Resolve key if it's a masked placeholder or empty
    if is_masked(api_key):
        db_keys = await db.get_api_keys()
        if provider == "openai":
            api_key = db_keys.get("openai") or os.getenv("OPENAI_API_KEY", "")
        elif provider == "deepgram":
            api_key = db_keys.get("deepgram") or os.getenv("DEEPGRAM_API_KEY", "")
        elif provider == "elevenlabs":
            api_key = db_keys.get("elevenlabs") or os.getenv("ELEVENLABS_API_KEY", "")

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API Key is missing or empty."
        )

    # Diagnostic client verification
    if provider == "openai":
        from openai import AsyncOpenAI
        try:
            client = AsyncOpenAI(api_key=api_key)
            await client.models.list()
            return {"success": True, "message": "OpenAI Connection Verified"}
        except Exception as e:
            err_msg = str(e)
            if "quota" in err_msg.lower() or "rate limit" in err_msg.lower() or "429" in err_msg:
                return {"success": True, "message": "Key valid (Account quota or rate limit exceeded)"}
            elif "invalid_api_key" in err_msg.lower() or "401" in err_msg or "incorrect api key" in err_msg.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="OpenAI API key is invalid or expired."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"OpenAI test failed: {err_msg}"
                )
            
    elif provider == "deepgram":
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.deepgram.com/v1/projects",
                    headers={"Authorization": f"Token {api_key}"},
                    follow_redirects=True
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "Deepgram Connection Verified"}
                elif resp.status_code == 401:
                    # Fallback to /v1/models if token is scoped to specific model resources
                    resp2 = await client.get(
                        "https://api.deepgram.com/v1/models",
                        headers={"Authorization": f"Token {api_key}"},
                        follow_redirects=True
                    )
                    if resp2.status_code == 200:
                        return {"success": True, "message": "Deepgram Connection Verified"}
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Deepgram API key is invalid or expired."
                        )
                elif resp.status_code in (402, 429):
                    return {"success": True, "message": "Key valid (Deepgram account balance low/exceeded)"}
                else:
                    detail_text = resp.text or f"HTTP {resp.status_code}"
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Deepgram test error: {detail_text}"
                    )
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Deepgram test error: {str(e)}"
            )

    elif provider == "elevenlabs":
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.elevenlabs.io/v1/user",
                    headers={"xi-api-key": api_key},
                    follow_redirects=True
                )
                if resp.status_code == 200:
                    return {"success": True, "message": "ElevenLabs Connection Verified"}
                elif resp.status_code == 401:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="ElevenLabs API key is invalid or expired."
                    )
                elif resp.status_code in (402, 429):
                    return {"success": True, "message": "Key valid (ElevenLabs quota exceeded)"}
                else:
                    detail_text = resp.text or f"HTTP {resp.status_code}"
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"ElevenLabs test error: {detail_text}"
                    )
        except Exception as e:
            if isinstance(e, HTTPException): raise e
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"ElevenLabs test error: {str(e)}"
            )
            
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported diagnostic provider: {provider}"
        )




