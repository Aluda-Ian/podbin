from fastapi import APIRouter
from typing import Dict, Any, List, Optional
from app.services.db import db
from pydantic import BaseModel

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

@router.get("/")
async def get_settings():
    return db.get_settings()

@router.put("/")
async def update_settings(payload: SettingsUpdate):
    upd = {k: v for k, v in payload.dict().items() if v is not None}
    return db.update_settings(upd)
