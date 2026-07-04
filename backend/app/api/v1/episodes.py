from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status, Body
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
from app.agents.state import EpisodeState, EpisodeStatus
from app.agents.graph import app_graph
from app.models.episode import EpisodeResponse, Clip, DistributionChannel, SocialsSchedule, Episode
from app.services.db import db
from app.core.config import settings
from app.services.distribution import publish_to_youtube, generate_spotify_rss, publish_to_tiktok
from app.services.llm import generate_metadata
from pydantic import BaseModel


router = APIRouter()

# Simulated Deepgram transcription pipeline requesting word-level timestamps
async def run_deepgram_transcription_pipeline(audio_url: str, timestamps: bool = True) -> dict:
    # If timestamps=True (or timestamps=true), it returns word-level timeline precision.
    if not timestamps:
        return {"transcript": "This is a transcript without word timeline.", "words": []}
    
    simulated_words = [
        {"word": "Welcome", "start": 0.1, "end": 0.5, "id": "w1"},
        {"word": "to", "start": 0.5, "end": 0.7, "id": "w2"},
        {"word": "PodBin,", "start": 0.7, "end": 1.2, "id": "w3"},
        {"word": "the", "start": 1.2, "end": 1.4, "id": "w4"},
        {"word": "autonomous", "start": 1.4, "end": 2.1, "id": "w5"},
        {"word": "podcast", "start": 2.1, "end": 2.6, "id": "w6"},
        {"word": "editing", "start": 2.6, "end": 3.1, "id": "w7"},
        {"word": "and", "start": 3.1, "end": 3.3, "id": "w8"},
        {"word": "distribution", "start": 3.3, "end": 4.0, "id": "w9"},
        {"word": "platform.", "start": 4.0, "end": 4.6, "id": "w10"}
    ]
    return {
        "transcript": "Welcome to PodBin, the autonomous podcast editing and distribution platform.",
        "words": simulated_words
    }

class EpisodeCreate(BaseModel):
    title: str
    guest: str
    raw_audio_url: Optional[str] = None

class EpisodeUpdate(BaseModel):
    title: Optional[str] = None
    guest: Optional[str] = None
    avatar: Optional[str] = None
    description: Optional[str] = None
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
    generated_content: Optional[Dict[str, Any]] = None

class MetadataRequest(BaseModel):
    burn_in_captions: bool = False

@router.get("/", response_model=List[EpisodeResponse])
async def get_episodes():
    episodes = await Episode.find_all().to_list()
    out = []
    for ep in episodes:
        ep_dict = ep.model_dump()
        ep_dict["id"] = ep.id
        db._ensure_defaults(ep_dict)
        out.append(ep_dict)
    return out

@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(episode_id: str):
    ep = await Episode.get(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    ep_dict = ep.model_dump()
    ep_dict["id"] = ep.id
    db._ensure_defaults(ep_dict)
    return ep_dict

@router.post("/", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def create_episode(
    title: str = Form(...),
    guest: str = Form(...),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    podcast_id: Optional[str] = Form("podcast-1")
):
    # Determine audio/video source
    media_path_or_url = url
    is_video = False
    if file:
        uploads_dir = Path("static") / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        import secrets
        import re
        ext = Path(file.filename).suffix or ".mp4"
        clean_name = Path(file.filename).stem
        clean_name = re.sub(r'[^a-zA-Z0-9_-]', '', clean_name)
        filename = f"{clean_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{ext}"
        media_path = uploads_dir / filename
        content = await file.read()
        with open(str(media_path), "wb") as f:
            f.write(content)
        media_path_or_url = f"http://localhost:8000/static/uploads/{filename}"
        
        if file.content_type and file.content_type.startswith("video/"):
            is_video = True
        elif ext.lower() in [".mp4", ".mov", ".webm", ".mkv", ".avi"]:
            is_video = True
    elif url:
        if any(url.lower().endswith(ext) for ext in [".mp4", ".mov", ".webm", ".mkv", ".avi"]):
            is_video = True
    
    if not media_path_or_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a media file or a URL must be provided."
        )

    # Save avatar if provided
    avatar_url = None
    if avatar:
        avatars_dir = Path("static") / "avatars"
        avatars_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(avatar.filename).suffix or ".jpg"
        import secrets
        avatar_filename = f"avatar_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{ext}"
        avatar_path = avatars_dir / avatar_filename
        content = await avatar.read()
        with open(str(avatar_path), "wb") as f:
            f.write(content)
        avatar_url = f"http://localhost:8000/static/avatars/{avatar_filename}"

    # Initialize episode data
    date_str = datetime.now().strftime("%b %d")
    new_ep = {
        "title": title,
        "guest": guest,
        "avatar": avatar_url if avatar_url else "",  # No default mock avatar
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
        "human_feedback": None,
        "word_timeline": [],
        "edit_decision_list": [],
        "selected_llm_config": {}
    }

    # Run LangGraph workflow (simulated or real)
    try:
        # Request word-level timestamps (timestamps=True)
        dg_res = await run_deepgram_transcription_pipeline(media_path_or_url, timestamps=True)
        new_ep["transcript"] = dg_res["transcript"]
        new_ep["word_timeline"] = dg_res["words"]

        initial_state = EpisodeState(
            raw_audio_url=media_path_or_url,
            transcript=dg_res["transcript"],
            generated_content={"titles": [], "notes": "", "social_snippets": []},
            status=EpisodeStatus.RESEARCH,
            human_feedback=None,
            word_timeline=dg_res["words"],
            edit_decision_list=[],
            selected_llm_config={}
        )
        graph_result = await app_graph.ainvoke(initial_state)
        # Update episode with graph execution results
        new_ep["transcript"] = graph_result.get("transcript")
        new_ep["generated_content"] = graph_result.get("generated_content")
        new_ep["word_timeline"] = graph_result.get("word_timeline")
        new_ep["edit_decision_list"] = graph_result.get("edit_decision_list")
        new_ep["selected_llm_config"] = graph_result.get("selected_llm_config")
        # Graph halts at PENDING_REVIEW — awaiting explicit user trigger
        new_ep["status"] = EpisodeStatus.PENDING_REVIEW
        new_ep["progress"] = 40
        new_ep["note"] = "Transcription complete. Awaiting human review."
    except Exception as e:
        print(f"LangGraph execution failed: {e}")
        # We proceed even if graph failed, just saving the basic structure

    # Save to MongoDB via Beanie
    all_eps = await Episode.find_all().to_list()
    existing_ids = []
    for ep in all_eps:
        try:
            num = int(ep.id.split("-")[1])
            existing_ids.append(num)
        except Exception:
            pass
    next_num = max(existing_ids) + 1 if existing_ids else 1
    new_ep["id"] = f"EP-{next_num}"
    
    db._ensure_defaults(new_ep)
    added_ep_doc = Episode(**new_ep)
    await added_ep_doc.insert()
    added_ep = added_ep_doc.model_dump()
    added_ep["id"] = added_ep_doc.id
    
    # Also seed a matching approval task!
    import uuid
    appr_id = f"appr-{str(uuid.uuid4())[:8]}"
    await db.add_approval({
        "id": appr_id,
        "type": "SHOW_NOTES",
        "title": f"Markdown · {added_ep['id']}",
        "quote": f"Summary for {added_ep['title']}: {added_ep['note']}",
        "meta": f"Generated just now for {added_ep['guest']}",
        "priority": "medium",
        "agent": "Research Agent",
        "status": "PENDING"
    })

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
    ep = await Episode.get(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    for k, v in upd.items():
        if hasattr(ep, k):
            setattr(ep, k, v)
    await ep.save()
    ep_dict = ep.model_dump()
    ep_dict["id"] = ep.id
    db._ensure_defaults(ep_dict)
    return ep_dict

@router.delete("/{episode_id}")
async def delete_episode(episode_id: str):
    ep = await Episode.get(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    await ep.delete()
    return {"message": f"Episode {episode_id} deleted successfully"}


@router.post("/{episode_id}/transcribe", response_model=EpisodeResponse)
async def transcribe_episode(episode_id: str):
    """Manually trigger the transcription pipeline for an existing episode."""
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    media_url = ep.get("raw_audio_url") or ep.get("raw_video_url")
    if not media_url:
        raise HTTPException(
            status_code=400,
            detail="No media URL attached to this episode. Upload audio or video first."
        )

    try:
        dg_res = await run_deepgram_transcription_pipeline(media_url, timestamps=True)
        transcript = dg_res["transcript"]
        words = dg_res["words"]

        initial_state = EpisodeState(
            raw_audio_url=media_url,
            transcript=transcript,
            generated_content={"titles": [], "notes": "", "social_snippets": []},
            status=EpisodeStatus.RESEARCH,
            human_feedback=None,
            word_timeline=words,
            edit_decision_list=[],
            selected_llm_config={}
        )
        graph_result = await app_graph.ainvoke(initial_state)
        transcript = graph_result.get("transcript", transcript)
        words = graph_result.get("word_timeline", words)

        updated = await db.update_episode(episode_id, {
            "transcript": transcript,
            "word_timeline": words,
            "generated_content": graph_result.get("generated_content", {"titles": [], "notes": "", "social_snippets": []}),
            "edit_decision_list": graph_result.get("edit_decision_list", []),
            "status": EpisodeStatus.PENDING_REVIEW,
            "progress": 40,
            "note": "Transcription complete. Ready for review.",
        })
    except Exception as e:
        # Fall back to simulated transcription so UI doesn't break
        updated = await db.update_episode(episode_id, {
            "transcript": "Transcription complete. (Simulated — configure Deepgram key for real transcription.)",
            "word_timeline": [],
            "status": EpisodeStatus.PENDING_REVIEW,
            "progress": 40,
            "note": f"Transcription complete (simulated). Error: {str(e)[:120]}",
        })

    return updated


class MetadataRequest(BaseModel):
    burn_in_captions: bool = False


@router.post("/{episode_id}/search-quote")

async def search_quote(episode_id: str, payload: dict = Body(...)):
    """Search for a quoted phrase in the episode word_timeline and return timestamps."""
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    
    quote = payload.get("quote", "").strip()
    if not quote:
        raise HTTPException(status_code=400, detail="Quote text is required")
    
    word_timeline = ep.get("word_timeline") or []
    if not word_timeline:
        raise HTTPException(status_code=404, detail="No word timeline available for this episode")
    
    import re
    def normalize(w: str) -> str:
        return re.sub(r"[^a-z0-9']", "", w.lower())
    
    search_words = [normalize(w) for w in quote.split()]
    timeline_normalized = [normalize(w.get("word", "")) for w in word_timeline]
    
    for i in range(len(timeline_normalized) - len(search_words) + 1):
        if timeline_normalized[i:i+len(search_words)] == search_words:
            start_sec = word_timeline[i]["start"]
            end_sec = word_timeline[i + len(search_words) - 1]["end"]
            def fmt(sec):
                m = int(sec // 60)
                s = int(sec % 60)
                return f"{m:02d}:{s:02d}"
            return {
                "found": True,
                "start": fmt(start_sec),
                "end": fmt(end_sec),
                "start_seconds": start_sec,
                "end_seconds": end_sec,
                "matched_words": [w["word"] for w in word_timeline[i:i+len(search_words)]]
            }
    
    return {"found": False, "message": "Quote not found in transcript timeline"}

@router.post("/{episode_id}/publish")
async def publish_episode(episode_id: str, platform: str = "YouTube"):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
        
    if platform.lower() == "youtube":
        res = publish_to_youtube(ep["title"], ep.get("raw_video_url") or "mock_path.mp4", "public")
        channels = ep.get("distribution_channels") or []
        for ch in channels:
            if ch.get("name") == "YouTube Studio":
                ch["status"] = "LIVE"
        await db.update_episode(episode_id, {"distribution_channels": channels})
        return res
    elif platform.lower() == "spotify":
        all_eps = await db.get_episodes()
        rss_feed = generate_spotify_rss(all_eps)
        return {
            "status": "success",
            "platform": "Spotify",
            "rss_feed": rss_feed
        }
    elif platform.lower() == "tiktok":
        res = publish_to_tiktok(ep["title"], ep.get("raw_video_url") or "mock_path.mp4", "public")
        channels = ep.get("distribution_channels") or []
        for ch in channels:
            if ch.get("name") == "TikTok for Business":
                ch["status"] = "LIVE"
        await db.update_episode(episode_id, {"distribution_channels": channels})
        return res
    else:
        raise HTTPException(status_code=400, detail="Invalid platform selected for publish")

@router.post("/{episode_id}/generate-metadata")
async def generate_episode_metadata(episode_id: str, payload: MetadataRequest = Body(MetadataRequest())):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    transcript = ep.get("transcript")
    if not transcript:
        raise HTTPException(status_code=400, detail="No transcript available. Ensure transcription has completed.")

    result = await generate_metadata(transcript)

    # If burn_in_captions is True, update clips to APPROVED and annotate the note
    if payload.burn_in_captions:
        existing_clips = ep.get("clips") or []
        if existing_clips:
            updated_clips = [
                {**c, "status": "APPROVED", "burn_in_captions": True}
                for c in existing_clips
            ]
            await db.update_episode(episode_id, {
                "clips": updated_clips,
                "note": "Animated captions burn-in requested. Clips tagged as approved."
            })
            result["burn_in_captions_applied"] = True
            result["clips_approved"] = len(updated_clips)
        else:
            result["burn_in_captions_applied"] = False
            result["message"] = "No clips found to tag for caption burn-in."

    # Persist the generated content back to the episode
    await db.update_episode(episode_id, {
        "generated_content": {
            "titles": result.get("titles", []),
            "notes": result.get("notes", ""),
            "social_snippets": result.get("social_snippets", []),
        },
        "progress": 60,
        "note": "AI snippets generated. Burn-in captions: " + ("enabled" if payload.burn_in_captions else "disabled"),
    })

    return result


@router.post("/{episode_id}/transcribe")
async def transcribe_episode(episode_id: str):
    """Manually trigger the Deepgram + LangGraph transcription pipeline on an existing episode."""
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    media_url = ep.get("raw_audio_url") or ep.get("raw_video_url")
    if not media_url:
        raise HTTPException(status_code=400, detail="Episode has no media URL to transcribe.")

    try:
        dg_res = await run_deepgram_transcription_pipeline(media_url, timestamps=True)
        transcript = dg_res["transcript"]
        word_timeline = dg_res["words"]

        initial_state = EpisodeState(
            raw_audio_url=media_url,
            transcript=transcript,
            generated_content={"titles": [], "notes": "", "social_snippets": []},
            status=EpisodeStatus.RESEARCH,
            human_feedback=None,
            word_timeline=word_timeline,
            edit_decision_list=[],
            selected_llm_config={}
        )
        graph_result = await app_graph.ainvoke(initial_state)

        updates = {
            "transcript": graph_result.get("transcript", transcript),
            "word_timeline": graph_result.get("word_timeline", word_timeline),
            "generated_content": graph_result.get("generated_content"),
            "edit_decision_list": graph_result.get("edit_decision_list"),
            "selected_llm_config": graph_result.get("selected_llm_config"),
            "status": EpisodeStatus.PENDING_REVIEW,
            "progress": 40,
            "note": "Manual transcription complete. Awaiting human review."
        }
        await db.update_episode(episode_id, updates)
        return {"status": "success", "transcript": updates["transcript"], "word_count": len(word_timeline)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription pipeline failed: {str(e)}")


class ScheduleEpisodeRequest(BaseModel):
    scheduled_at: str  # ISO datetime string
    platforms: List[str]
    description: Optional[str] = None
    privacy_status: Optional[str] = "public"


@router.post("/{episode_id}/schedule")
async def schedule_episode_endpoint(episode_id: str, payload: ScheduleEpisodeRequest = Body(...)):
    """Schedule an episode for distribution to selected platforms at a given datetime."""
    from datetime import datetime as _dt
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    sandbox_notes = []
    existing_schedule = ep.get("socials_schedule") or []

    for platform in payload.platforms:
        new_entry = {
            "id": f"sched-{episode_id}-{platform.replace(' ', '_')}-{len(existing_schedule)+1}",
            "platform": platform,
            "caption": payload.description or f"New episode: {ep.get('title', 'Untitled')}",
            "time": payload.scheduled_at,
            "status": "SCHEDULED",
        }
        existing_schedule.append(new_entry)
        sandbox_notes.append(f"{platform}: scheduled for {payload.scheduled_at}")

    await db.update_episode(episode_id, {
        "socials_schedule": existing_schedule,
        "status": EpisodeStatus.DISTRO,
        "stage": "Growth",
        "progress": 90,
        "note": f"Scheduled to {len(payload.platforms)} platform(s) on {payload.scheduled_at[:10]}.",
    })

    return {
        "status": "scheduled",
        "scheduled_at": payload.scheduled_at,
        "platforms": payload.platforms,
        "sandbox_notes": sandbox_notes,
    }

