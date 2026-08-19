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
        
    temp_dir = tempfile.mkdtemp()
    segments_file_path = os.path.join(temp_dir, "segments.txt")
    
    project_root = Path(__file__).resolve().parents[4]
    
    try:
        segment_paths = []
        for idx, item in enumerate(edl):
            segment_name = f"seg_{idx}.mp3"
            segment_path = os.path.join(temp_dir, segment_name)
            
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
            
        with open(segments_file_path, "w") as f:
            for path in segment_paths:
                escaped_path = path.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{escaped_path}'\n")
                
        static_edited_dir = project_root / "static" / "edited"
        try:
            static_edited_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            import tempfile
            static_edited_dir = Path(tempfile.gettempdir()) / "podbin" / "edited"
            static_edited_dir.mkdir(parents=True, exist_ok=True)
        output_filename = f"edited_{episode_id}_{int(time.time())}.mp3"
        output_path = static_edited_dir / output_filename
        
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
            
        public_url = f"{settings.PUBLIC_URL}/static/edited/{output_filename}"
        
        await db.update_episode(episode_id, {
            "raw_audio_url": public_url,
            "edit_decision_list": [item.model_dump() for item in edl],
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


class RenderCutPayload(BaseModel):
    intervals: List[EDLItem]
    aspect_ratio: Optional[str] = "9:16"

@router.post("/{approval_id}/render-cut")
async def render_cut(approval_id: str, payload: RenderCutPayload = Body(...)):
    ep_id = None
    if approval_id.startswith("EP-"):
        ep_id = approval_id
    else:
        appr = await db.action_approval(approval_id, "pending", None)
        if appr:
            import re
            title = appr.get("title", "")
            match = re.search(r'(?:EP-|Ep\.\s*)(\d+)', title)
            if match:
                ep_num = match.group(1)
                episodes = await db.get_episodes()
                for ep in episodes:
                    if ep_num in ep["id"]:
                        ep_id = ep["id"]
                        break

    if not ep_id:
        raise HTTPException(status_code=404, detail="Could not resolve episode from approval ID or Episode ID")

    ep = await db.get_episode(ep_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    source = ep.get("raw_video_url") or ep.get("raw_audio_url")
    if not source:
        raise HTTPException(status_code=400, detail="Episode has no raw source media")

    if source.startswith("file://"):
        source = source[7:]

    is_video = bool(ep.get("raw_video_url")) or ep.get("media_type") == "video"
    ext = "mp4" if is_video else "mp3"

    project_root = Path(__file__).resolve().parents[4]
    static_cut_dir = project_root / "static" / "cuts"
    try:
        static_cut_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        import tempfile
        static_cut_dir = Path(tempfile.gettempdir()) / "podbin" / "cuts"
        static_cut_dir.mkdir(parents=True, exist_ok=True)
    output_filename = f"cut_{ep_id}_{int(time.time())}.{ext}"
    output_path = static_cut_dir / output_filename

    edl = payload.intervals
    aspect_ratio = payload.aspect_ratio or "9:16"
    seg_count = len(edl)
    if seg_count == 0:
        raise HTTPException(status_code=400, detail="EDL must contain at least one segment")

    try:
        filter_parts = []
        valid_labels = []

        for idx, item in enumerate(edl):
            duration = item.end - item.start
            if duration <= 0:
                continue
            label = f"s{idx}"
            if is_video:
                trim_expr = (
                    f"[0:v]trim=start={item.start}:duration={duration},setpts=PTS-STARTPTS[{label}v];"
                    f"[0:a]atrim=start={item.start}:duration={duration},asetpts=PTS-STARTPTS[{label}a]"
                )
            else:
                trim_expr = (
                    f"[0:a]atrim=start={item.start}:duration={duration},asetpts=PTS-STARTPTS[{label}a]"
                )
            filter_parts.append(trim_expr)
            valid_labels.append(label)

        if not valid_labels:
            raise HTTPException(status_code=400, detail="No valid segments in EDL")

        if is_video:
            video_concat = "".join(f"[{l}v]" for l in valid_labels)
            audio_concat = "".join(f"[{l}a]" for l in valid_labels)
            concat_expr = (
                f"{video_concat}concat=n={len(valid_labels)}:v=1:a=0[concatv];"
                f"{audio_concat}concat=n={len(valid_labels)}:v=0:a=1[outa]"
            )
            if aspect_ratio == "16:9":
                w, h = 1920, 1080
            elif aspect_ratio == "4:5":
                w, h = 1080, 1350
            elif aspect_ratio == "1:1":
                w, h = 1080, 1080
            else:
                w, h = 1080, 1920
            
            resize_expr = f"[concatv]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[outv]"
            filter_complex = ";".join(filter_parts + [concat_expr, resize_expr])
            map_args = ["-map", "[outv]", "-map", "[outa]"]
        else:
            audio_concat = "".join(f"[{l}a]" for l in valid_labels)
            concat_expr = f"{audio_concat}concat=n={len(valid_labels)}:v=0:a=1[outa]"
            filter_complex = ";".join(filter_parts + [concat_expr])
            map_args = ["-map", "[outa]"]

        cmd = ["ffmpeg", "-y", "-i", source]
        cmd += ["-filter_complex", filter_complex]
        cmd += map_args
        if is_video:
            cmd += ["-c:v", "libx264", "-preset", "fast", "-crf", "22"]
            cmd += ["-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-c:a", "libmp3lame", "-q:a", "2"]
        cmd += [str(output_path)]

        import asyncio
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0 or not output_path.exists() or output_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="FFmpeg rendering failed")

        public_url = f"{settings.PUBLIC_URL}/static/cuts/{output_filename}"

        await db.update_episode(ep_id, {
            "edit_decision_list": [item.model_dump() for item in edl],
            "note": f"Cut render complete. Output: {output_filename} (aspect ratio: {aspect_ratio})"
        })

        return {
            "message": "Render-cut completed successfully (filter_complex).",
            "output_url": public_url,
            "segments_count": len(valid_labels),
            "aspect_ratio": aspect_ratio
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
