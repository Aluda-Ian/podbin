from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services.db import db

router = APIRouter()

@router.get("/")
async def get_agents():
    return await db.get_agents()

@router.post("/{name}/toggle")
async def toggle_agent(name: str):
    ag = await db.toggle_agent(name)
    if not ag:
        raise HTTPException(status_code=404, detail="Agent not found")
    return ag
