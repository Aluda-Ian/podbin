from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.services.db import db

router = APIRouter()

@router.get("")
@router.get("/")
async def get_agents():
    return await db.get_agents()

@router.post("/{name}/toggle")
async def toggle_agent(name: str):
    ag = await db.toggle_agent(name)
    if not ag:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Push completion notification when agent toggled active
    if ag.get("status") == "active":
        tag = f"AGENT_{name.upper().replace(' ', '_')}"
        await db.notify_agent_completion(
            agent_tag=tag,
            message=f"Resumed active automated workflow: {ag.get('task', 'Processing podcast tasks')}"
        )
    return ag


@router.post("/{name}/execute")
async def execute_agent_task(name: str, task_description: str = "Completed automated workflow task"):
    ag = await db.toggle_agent(name)
    if not ag:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    tag = f"AGENT_{name.upper().replace(' ', '_')}"
    notif = await db.notify_agent_completion(
        agent_tag=tag,
        message=f"{task_description}"
    )
    return {"status": "success", "agent": ag, "notification": notif}

