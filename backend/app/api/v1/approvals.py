from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from app.services.db import db
from pydantic import BaseModel

router = APIRouter()

class ActionPayload(BaseModel):
    action: str  # 'approve', 'reject', 'edit'
    updated_content: Optional[str] = None

@router.get("/")
async def get_approvals():
    return db.get_approvals()

@router.post("/{approval_id}/action")
async def action_approval(approval_id: str, payload: ActionPayload):
    appr = db.action_approval(approval_id, payload.action, payload.updated_content)
    if not appr:
        raise HTTPException(status_code=404, detail="Approval item not found")
    
    # Custom post-action logic: if we approve show notes, change the episode status
    if payload.action == "approve" and "Ep." in appr.get("title", ""):
        # Try to find episode ID from the title (e.g. "Vertical 9:16 · Ep. 142" or "Markdown · EP-144")
        import re
        title = appr["title"]
        # Match standard EP-xxx or Ep. xxx
        match = re.search(r'(?:EP-|Ep\.\s*)(\d+)', title)
        if match:
            ep_num = match.group(1)
            # Find the episode with number suffix or exact match
            episodes = db.get_episodes()
            for ep in episodes:
                if ep_num in ep["id"]:
                    # Progress the stage and status!
                    updates = {}
                    if ep["status"] == "RESEARCH":
                        updates["status"] = "BOOKING"
                        updates["progress"] = 35
                        updates["note"] = "Guest outreach underway"
                    elif ep["status"] == "BOOKING":
                        updates["status"] = "EDITING"
                        updates["stage"] = "Post-Prod"
                        updates["progress"] = 60
                        updates["note"] = "Audio editing in progress"
                    elif ep["status"] == "EDITING":
                        updates["status"] = "MASTERING"
                        updates["progress"] = 85
                        updates["note"] = "Audio mastering underway"
                    elif ep["status"] == "MASTERING":
                        updates["status"] = "DISTRO"
                        updates["stage"] = "Growth"
                        updates["progress"] = 95
                        updates["note"] = "Syndicating clips and notes"
                    elif ep["status"] == "DISTRO":
                        updates["status"] = "LIVE"
                        updates["progress"] = 100
                        updates["note"] = "Episode published and live"
                    
                    db.update_episode(ep["id"], updates)
                    break
                    
    return appr
