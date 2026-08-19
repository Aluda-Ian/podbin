from fastapi import APIRouter, HTTPException, status, Body
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.services.copilot_llm import run_copilot_chat, SUPPORTED_PROVIDERS
from app.services.db import db

router = APIRouter()

class CopilotChatPayload(BaseModel):
    prompt: str
    provider: Optional[str] = "openai"
    model: Optional[str] = None
    api_key: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class SelectProviderPayload(BaseModel):
    provider: str
    model: str
    api_key: Optional[str] = None

@router.get("/providers")
async def get_copilot_providers():
    """List supported LLM providers and current active selection."""
    settings_data = await db.get_settings()
    pc = settings_data.get("provider_config", {}) or {}
    active_provider = pc.get("custom_provider", "openai")
    active_model = settings_data.get("orchestrator_model", "gpt-4o-mini")
    
    return {
        "active_provider": active_provider,
        "active_model": active_model,
        "providers": SUPPORTED_PROVIDERS
    }

@router.post("/providers/select")
async def select_provider(payload: SelectProviderPayload):
    """Set default LLM provider and model for the platform copilot."""
    from app.services.copilot_tools import tool_configure_llm_provider
    res = await tool_configure_llm_provider(
        provider=payload.provider,
        model_name=payload.model,
        api_key=payload.api_key
    )
    return res

@router.post("/chat")
async def copilot_chat(payload: CopilotChatPayload):
    """Process natural language instructions with tool calling across multi-LLM providers."""
    if not payload.prompt:
        raise HTTPException(status_code=400, detail="Prompt must not be empty.")
        
    res = await run_copilot_chat(
        prompt=payload.prompt,
        provider=payload.provider or "openai",
        model=payload.model,
        api_key=payload.api_key,
        context=payload.context
    )
    return res
