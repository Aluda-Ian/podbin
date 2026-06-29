from fastapi import APIRouter, HTTPException, Body, status
from typing import List, Dict, Any, Optional
from app.services.db import db
from pydantic import BaseModel
import os
import subprocess
import tempfile
import shutil
import time
from pathlib import Path

router = APIRouter()

class ActionPayload(BaseModel):
    action: str  # 'approve', 'reject', 'edit'
    updated_content: Optional[str] = None

class EDLItem(BaseModel):
    start: float
    end: float

backend_root = Path(__file__).resolve().parents[4]

@router.get("/")
async def get_approvals():
    return await db.get_approvals()

@router.post("/{approval_id}/action")
async def action_approval(approval_id: str, payload: ActionPayload):
    appr = await db.action_approval(approval_id, payload.action, payload.updated_content)
    if not appr:
        raise HTTPException(status_code=404, detail="Approval item not found")
    
    # Custom post-action logic: if we approve show notes, change the episode status
    if payload.action == "approve" and "Ep." in appr.get("title", ""):
        import re
        title = appr["title"]
        match = re.search(r'(?:EP-|Ep\.\s*)(\d+)', title)
        if match:
            ep_num = match.group(1)
            episodes = await db.get_episodes()
            for ep in episodes:
                if ep_num in ep["id"]:
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
                    
                    await db.update_episode(ep["id"], updates)
                    break
                    
    return appr

@router.post("/{episode_id}/render-edit")
async def render_edit(episode_id: str, edl: List[EDLItem] = Body(...)):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
        
    source = ep.get("raw_audio_url") or ep.get("raw_video_url")
    if not source:
        raise HTTPException(status_code=400, detail="Episode has no raw source media to edit")
        
    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    segments_file_path = os.path.join(temp_dir, "segments.txt")
    
    # Resolve backend project root statically
    project_root = Path(__file__).resolve().parents[4]
    
    try:
        segment_paths = []
        for idx, item in enumerate(edl):
            segment_name = f"seg_{idx}.mp3"
            segment_path = os.path.join(temp_dir, segment_name)
            
            # Slicing cmd
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(item.start),
                "-to", str(item.end),
                "-i", source,
                "-c", "copy",
                segment_path
            ]
            
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                # Fallback to copy bypass encoding
                cmd_fallback = [
                    "ffmpeg", "-y",
                    "-ss", str(item.start),
                    "-to", str(item.end),
                    "-i", source,
                    segment_path
                ]
                subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
            if os.path.exists(segment_path) and os.path.getsize(segment_path) > 0:
                segment_paths.append(segment_path)
                
        if not segment_paths:
            raise HTTPException(status_code=500, detail="Failed to slice any valid media segments.")
            
        # Write segment paths to demuxer file
        with open(segments_file_path, "w") as f:
            for path in segment_paths:
                escaped_path = path.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
                
        # Resolve output directory inside static folder
        static_edited_dir = project_root / "static" / "edited"
        static_edited_dir.mkdir(parents=True, exist_ok=True)
        output_filename = f"edited_{episode_id}_{int(time.time())}.mp3"
        output_path = static_edited_dir / output_filename
        
        # Concatenate segments
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", segments_file_path,
            "-c", "copy",
            str(output_path)
        ]
        
        concat_res = subprocess.run(concat_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="Failed to synthesize concatenated media output.")
            
        public_url = f"http://localhost:8000/static/edited/{output_filename}"
        
        # Save edit decision list and output url in db
        await db.update_episode(episode_id, {
            "raw_audio_url": public_url,
            "edit_decision_list": [item.dict() for item in edl],
            "note": f"Descript EDL synthesis complete. Output: {output_filename}"
        })
        
        return {
            "message": "EDL compilation and media rendering completed successfully.",
            "output_url": public_url,
            "segments_count": len(segment_paths)
        }
        
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass
