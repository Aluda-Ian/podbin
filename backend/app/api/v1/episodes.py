from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.agents.state import EpisodeState, EpisodeStatus
from app.agents.graph import app_graph
from app.models.episode import EpisodeResponse, Clip, DistributionChannel, SocialsSchedule
from app.services.db import db
from pydantic import BaseModel

router = APIRouter()

class EpisodeCreate(BaseModel):
    title: str
    guest: str
    raw_audio_url: Optional[str] = None

class EpisodeUpdate(BaseModel):
    title: Optional[str] = None
    guest: Optional[str] = None
    stage: Optional[str] = None
    status: Optional[EpisodeStatus] = None
    progress: Optional[int] = None
    note: Optional[str] = None
    duration: Optional[str] = None
    human_feedback: Optional[str] = None
    raw_audio_url: Optional[str] = None
    raw_video_url: Optional[str] = None
    media_type: Optional[str] = None
    podcast_id: Optional[str] = None
    clips: Optional[List[Clip]] = None
    distribution_channels: Optional[List[DistributionChannel]] = None
    socials_schedule: Optional[List[SocialsSchedule]] = None

@router.get("/", response_model=List[EpisodeResponse])
async def get_episodes():
    return db.get_episodes()

@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(episode_id: str):
    ep = db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep

@router.post("/", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def create_episode(
    title: str = Form(...),
    guest: str = Form(...),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    podcast_id: Optional[str] = Form("podcast-1")
):
    # Determine audio/video source
    media_path_or_url = url
    is_video = False
    if file:
        media_path_or_url = f"file://{file.filename}"
        if file.content_type and file.content_type.startswith("video/"):
            is_video = True
        elif any(file.filename.lower().endswith(ext) for ext in [".mp4", ".mov", ".webm", ".mkv", ".avi"]):
            is_video = True
    elif url:
        if any(url.lower().endswith(ext) for ext in [".mp4", ".mov", ".webm", ".mkv", ".avi"]):
            is_video = True
    
    if not media_path_or_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a media file or a URL must be provided."
        )

    # Initialize episode data
    date_str = datetime.now().strftime("%b %d")
    new_ep = {
        "title": title,
        "guest": guest,
        "avatar": "guest1",  # default avatar index
        "stage": "Pre-Prod",
        "status": EpisodeStatus.RESEARCH,
        "duration": "—",
        "date": date_str,
        "progress": 20,
        "note": "Starting transcription flow",
        "raw_audio_url": None if is_video else media_path_or_url,
        "raw_video_url": media_path_or_url if is_video else None,
        "media_type": "video" if is_video else "audio",
        "podcast_id": podcast_id or "podcast-1",
        "transcript": None,
        "generated_content": {"titles": [], "notes": "", "social_snippets": []},
        "human_feedback": None
    }

    # Run LangGraph workflow (simulated or real)
    try:
        initial_state = EpisodeState(
            raw_audio_url=media_path_or_url,
            transcript=None,
            generated_content={"titles": [], "notes": "", "social_snippets": []},
            status=EpisodeStatus.RESEARCH,
            human_feedback=None
        )
        graph_result = await app_graph.ainvoke(initial_state)
        # Update episode with graph execution results
        new_ep["transcript"] = graph_result.get("transcript")
        new_ep["generated_content"] = graph_result.get("generated_content")
        new_ep["progress"] = 40
        new_ep["note"] = "Transcription complete. Ready for edit."
    except Exception as e:
        print(f"LangGraph execution failed: {e}")
        # We proceed even if graph failed, just saving the basic structure

    # Save to JSON database
    added_ep = db.add_episode(new_ep)
    
    # Also seed a matching approval task!
    import uuid
    appr_id = f"appr-{str(uuid.uuid4())[:8]}"
    db.data["approvals"].insert(0, {
        "id": appr_id,
        "type": "SHOW_NOTES",
        "title": f"Markdown · {added_ep['id']}",
        "quote": f"Summary for {added_ep['title']}: {added_ep['note']}",
        "meta": f"Generated just now for {added_ep['guest']}",
        "priority": "medium",
        "agent": "Research Agent",
        "status": "PENDING"
    })
    db._save()

    return added_ep

@router.post("/ingest", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def ingest_episode(
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    # Legacy compatibility endpoint, maps to create_episode with defaults
    return await create_episode(
        title="Ingested Episode",
        guest="Unknown Guest",
        file=file,
        url=url
    )

@router.put("/{episode_id}", response_model=EpisodeResponse)
async def update_episode(episode_id: str, updates: EpisodeUpdate):
    # filter out None updates
    upd = {k: v for k, v in updates.dict().items() if v is not None}
    ep = db.update_episode(episode_id, upd)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep

@router.delete("/{episode_id}")
async def delete_episode(episode_id: str):
    success = db.delete_episode(episode_id)
    if not success:
        raise HTTPException(status_code=404, detail="Episode not found")
    return {"message": f"Episode {episode_id} deleted successfully"}
