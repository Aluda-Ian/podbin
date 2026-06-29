from fastapi import APIRouter
from typing import Dict, Any, List, Optional
from app.services.db import db
from pydantic import BaseModel
from app.models.user import ProviderConfig

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
    return db.get_settings()

@router.put("/")
async def update_settings(payload: SettingsUpdate):
    upd = {k: v for k, v in payload.dict().items() if v is not None}
    return db.update_settings(upd)

@router.get("/provider-config", response_model=ProviderConfig)
async def get_provider_config():
    settings = db.get_settings()
    # Mask or decrypt custom_api_key in secure operations if needed
    config = settings.get("provider_config", {
        "tier": "PLATFORM_FREE",
        "custom_api_key": None,
        "custom_provider": None
    })
    return config

@router.post("/provider-config", response_model=ProviderConfig)
async def update_provider_config(payload: ProviderConfig):
    db.update_settings({"provider_config": payload.dict()})
    return payload
