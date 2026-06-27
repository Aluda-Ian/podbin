from fastapi import APIRouter
from typing import Dict, Any
from app.services.db import db
from pydantic import BaseModel

router = APIRouter()

class SettingsUpdate(BaseModel):
    workspaceName: str = None
    showName: str = None
    primaryHost: str = None
    releaseCadence: str = None
    autonomyLevel: str = None

@router.get("/")
async def get_settings():
    return db.get_settings()

@router.put("/")
async def update_settings(payload: SettingsUpdate):
    upd = {k: v for k, v in payload.dict().items() if v is not None}
    return db.update_settings(upd)
