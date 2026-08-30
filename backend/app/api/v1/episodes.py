from fastapi import APIRouter, File, UploadFile, Form, HTTPException, status, Body, Request
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path
import os
import secrets
import re
from app.agents.state import EpisodeState, EpisodeStatus
from app.agents.graph import app_graph
from app.models.episode import EpisodeResponse, Clip, DistributionChannel, SocialsSchedule, Episode
from app.services.db import db
from app.core.config import settings
from app.services.distribution import publish_to_youtube, generate_spotify_rss, publish_to_tiktok
from app.services.llm import generate_metadata
from pydantic import BaseModel


router = APIRouter()

def get_upload_dir() -> Path:
    if os.getenv("VERCEL"):
        upload_dir = Path("/tmp/uploads")
    else:
        upload_dir = Path("static/uploads")
    try:
        upload_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return upload_dir

async def run_deepgram_transcription_pipeline(audio_url: str, timestamps: bool = True) -> dict:
    from app.services.llm import run_local_whisper_transcription
    from app.services.transcription import get_deepgram_api_key

    deepgram_key = await get_deepgram_api_key()

    if not deepgram_key or deepgram_key.startswith("dg-...") or "mock" in deepgram_key.lower() or "sandbox" in deepgram_key.lower():
        print("No real Deepgram key configured. Running local fallback Whisper transcription...")
        return await run_local_whisper_transcription(audio_url)
    else:
        return await run_local_whisper_transcription(audio_url)

class EpisodeCreate(BaseModel):
    title: Optional[str] = "Ingested Episode"
    guest: Optional[str] = "Unknown Guest"
    raw_audio_url: Optional[str] = None
    raw_video_url: Optional[str] = None

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
    transcript: Optional[str] = None
    generated_content: Optional[Dict[str, Any]] = None

class MetadataRequest(BaseModel):
    burn_in_captions: bool = False

class UploadUrlRequest(BaseModel):
    filename: str
    content_type: Optional[str] = "video/mp4"

class ConfirmUploadRequest(BaseModel):
    title: Optional[str] = "Ingested Episode"
    guest: Optional[str] = "Unknown Guest"
    media_url: Optional[str] = None
    raw_video_url: Optional[str] = None
    raw_audio_url: Optional[str] = None
    media_type: Optional[str] = "video"
    avatar: Optional[str] = None
    podcast_id: Optional[str] = "podcast-1"

@router.get("", response_model=List[EpisodeResponse])
@router.get("/", response_model=List[EpisodeResponse])
async def get_episodes():
    return await db.get_episodes()

@router.post("/upload-url")
async def get_upload_url(payload: UploadUrlRequest = Body(...)):
    """Generate signed direct-to-storage upload URL (Vercel Blob / S3 / R2)."""
    from app.services.storage import generate_signed_upload_url
    return generate_signed_upload_url(payload.filename, payload.content_type or "video/mp4")

MAX_UPLOAD_BYTES = 512 * 1024 * 1024  # 512 MB hard limit

@router.put("/upload-direct")
async def upload_file_direct(filename: str, request: Request):
    """Receive direct file stream for local dev / fallback object storage.
    
    Streams chunks directly to disk — never buffers the full file in RAM.
    Enforces a 512 MB cap; returns 413 if exceeded.
    After writing to disk, also persists to MongoDB GridFS when DB is ready.
    """
    # Reject immediately if Content-Length header already tells us it's too big
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum allowed size is 512 MB."
        )

    clean_fn = Path(filename).name
    upload_dir = get_upload_dir()
    file_path = upload_dir / clean_fn
    total_written = 0

    try:
        with open(file_path, "wb") as f:
            async for chunk in request.stream():
                total_written += len(chunk)
                if total_written > MAX_UPLOAD_BYTES:
                    # Remove partial file and reject
                    try:
                        file_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum allowed size is 512 MB."
                    )
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[upload-direct] Stream write error: {e}")
        raise HTTPException(status_code=500, detail=f"Upload stream failed: {e}")

    # Best-effort: persist to MongoDB GridFS (non-blocking, does not fail the upload)
    try:
        if db.is_db_ready:
            from app.services.storage import store_file_gridfs
            import asyncio
            content_type = request.headers.get("content-type", "application/octet-stream")
            asyncio.ensure_future(store_file_gridfs(clean_fn, file_path, content_type))
    except Exception as gfs_err:
        print(f"[upload-direct] GridFS persist notice: {gfs_err}")

    return {"status": "success", "filename": clean_fn, "size": total_written}

@router.get("/media/{filename}")
async def serve_media_file(filename: str):
    """Serve uploaded media file for playback and processing.
    Falls back to MongoDB GridFS if the local file is not found.
    """
    clean_fn = Path(filename).name

    def _get_content_type(fn: str) -> str:
        fn_l = fn.lower()
        if fn_l.endswith(".mp3"): return "audio/mpeg"
        if fn_l.endswith(".wav"): return "audio/wav"
        if fn_l.endswith(".webm"): return "video/webm"
        if fn_l.endswith(".mkv"): return "video/x-matroska"
        if fn_l.endswith(".mov"): return "video/quicktime"
        return "video/mp4"

    # Try local disk first
    file_path = get_upload_dir() / clean_fn
    if not file_path.exists():
        file_path = Path("static/uploads") / clean_fn
    if file_path.exists():
        return FileResponse(path=file_path, media_type=_get_content_type(clean_fn), filename=clean_fn)

    # Fall back to MongoDB GridFS
    if db.is_db_ready:
        try:
            from app.services.storage import stream_file_gridfs
            gen, ct = await stream_file_gridfs(clean_fn)
            if gen:
                return StreamingResponse(gen, media_type=ct or _get_content_type(clean_fn))
        except Exception as gfs_err:
            print(f"[serve_media] GridFS read error: {gfs_err}")

    raise HTTPException(status_code=404, detail="Media file not found")

@router.post("/confirm-upload", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def confirm_episode_upload(payload: ConfirmUploadRequest = Body(...)):
    """Register episode with cloud storage URL after direct frontend upload."""
    media_url = payload.raw_video_url or payload.raw_audio_url or payload.media_url
    if not media_url:
        raise HTTPException(status_code=400, detail="Missing storage media URL.")
    
    is_video = payload.media_type == "video" or bool(payload.raw_video_url)
    date_str = datetime.now().strftime("%b %d")
    new_ep = {
        "title": payload.title or "Ingested Episode",
        "guest": payload.guest or "Unknown Guest",
        "avatar": payload.avatar or "",
        "stage": "Pre-Prod",
        "status": EpisodeStatus.RESEARCH,
        "duration": "—",
        "date": date_str,
        "progress": 10,
        "note": "Media ingested via direct cloud upload. Ready for transcription.",
        "raw_audio_url": payload.raw_audio_url or payload.raw_video_url or media_url,
        "raw_video_url": payload.raw_video_url or (media_url if is_video else None),
        "media_type": "video" if is_video else "audio",
        "podcast_id": payload.podcast_id or "podcast-1",
        "transcript": None,
        "generated_content": {"titles": [], "notes": "", "social_snippets": []},
        "human_feedback": None,
        "clips": [],
        "distribution_channels": [],
        "socials_schedule": [],
        "word_timeline": [],
        "edit_decision_list": [],
        "selected_llm_config": {}
    }
    all_eps = await db.get_episodes()
    existing_ids = []
    for ep in all_eps:
        try:
            num = int(ep["id"].split("-")[1])
            existing_ids.append(num)
        except Exception:
            pass
    next_num = max(existing_ids) + 1 if existing_ids else 1
    new_ep["id"] = f"EP-{next_num}"
    
    added_ep = await db.add_episode(new_ep)
    
    try:
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
    except Exception as appr_err:
        print(f"Approval creation notice: {appr_err}")

    return added_ep

@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(episode_id: str):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep

def get_youtube_embed_url(url: str) -> Optional[str]:
    if not url:
        return None
    import re
    patterns = [
        r'v=([0-9A-Za-z_-]{11})',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/embed\/([0-9A-Za-z_-]{11})',
        r'youtube\.com\/shorts\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return f"https://www.youtube.com/embed/{match.group(1)}"
    return url

@router.post("", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def create_episode(
    request: Request,
    title: Optional[str] = Form(None),
    guest: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    podcast_id: Optional[str] = Form("podcast-1")
):
    title_str = title if isinstance(title, str) else None
    guest_str = guest if isinstance(guest, str) else None
    url_str = url if isinstance(url, str) else None
    podcast_id_str = podcast_id if isinstance(podcast_id, str) else None

    content_type = request.headers.get("content-type", "").lower()
    try:
        json_body = await request.json()
        if isinstance(json_body, str):
            title_str = title_str or json_body
        elif isinstance(json_body, dict):
            title_str = title_str or json_body.get("title") or json_body.get("name")
            guest_str = guest_str or json_body.get("guest") or json_body.get("author")
            url_str = url_str or json_body.get("url") or json_body.get("raw_video_url") or json_body.get("raw_audio_url") or json_body.get("video_url") or json_body.get("audio_url")
            podcast_id_str = podcast_id_str or json_body.get("podcast_id") or "podcast-1"
    except Exception:
        pass

    title = (title_str or "").strip() or "Ingested Episode"
    guest = (guest_str or "").strip() or "Unknown Guest"
    url = (url_str or "").strip() or None
    podcast_id = (podcast_id_str or "").strip() or "podcast-1"

    media_path_or_url = url
    is_video = False
    if url:
        url_lower = url.lower()
        if any(domain in url_lower for domain in ["youtube.com", "youtu.be", "vimeo.com", "tiktok.com", "video"]) or any(url_lower.endswith(ext) for ext in [".mp4", ".mov", ".webm", ".mkv", ".avi", ".m3u8"]):
            is_video = True
            yt_embed = get_youtube_embed_url(url)
            if yt_embed:
                media_path_or_url = yt_embed
    elif file and hasattr(file, "filename") and file.filename:
        filename = file.filename
        clean_stem = re.sub(r'[^a-zA-Z0-9_-]', '', Path(filename).stem) or "media"
        ext = Path(filename).suffix or ".mp4"
        unique_name = f"{clean_stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{ext}"
        upload_dir = get_upload_dir()
        file_path = upload_dir / unique_name
        
        contents = await file.read()
        try:
            with open(file_path, "wb") as f:
                f.write(contents)
        except Exception as e:
            print(f"File save notice: {e}")
            
        public_url = os.getenv("PUBLIC_URL", "http://localhost:8000").rstrip("/")
        media_path_or_url = f"{public_url}/api/v1/episodes/media/{unique_name}"
        if file.content_type and (file.content_type.startswith("video/") or ext.lower() in [".mp4", ".mov", ".webm", ".mkv", ".avi"]):
            is_video = True

    if not media_path_or_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either a media file URL or remote URL must be provided. Use /upload-url for direct video upload."
        )

    date_str = datetime.now().strftime("%b %d")
    new_ep = {
        "title": title,
        "guest": guest,
        "avatar": "",
        "stage": "Pre-Prod",
        "status": EpisodeStatus.RESEARCH,
        "duration": "—",
        "date": date_str,
        "progress": 10,
        "note": "Media ingested. Ready for processing.",
        "raw_audio_url": media_path_or_url,
        "raw_video_url": media_path_or_url if is_video else None,
        "media_type": "video" if is_video else "audio",
        "podcast_id": podcast_id or "podcast-1",
        "transcript": None,
        "generated_content": {"titles": [], "notes": "", "social_snippets": []},
        "human_feedback": None,
        "clips": [],
        "distribution_channels": [],
        "socials_schedule": [],
        "word_timeline": [],
        "edit_decision_list": [],
        "selected_llm_config": {}
    }

    all_eps = await db.get_episodes()
    existing_ids = []
    for ep in all_eps:
        try:
            num = int(ep["id"].split("-")[1])
            existing_ids.append(num)
        except Exception:
            pass
    next_num = max(existing_ids) + 1 if existing_ids else 1
    new_ep["id"] = f"EP-{next_num}"
    
    added_ep = await db.add_episode(new_ep)
    return added_ep


@router.post("/ingest", response_model=EpisodeResponse, status_code=status.HTTP_201_CREATED)
async def ingest_episode(
    request: Request,
    file: Optional[UploadFile] = File(None),
    url: Optional[str] = Form(None)
):
    return await create_episode(
        request=request,
        title="Ingested Episode",
        guest="Unknown Guest",
        file=file,
        url=url
    )

@router.put("/{episode_id}", response_model=EpisodeResponse)
async def update_episode(episode_id: str, updates: EpisodeUpdate):
    upd = {k: v for k, v in updates.model_dump().items() if v is not None}
    ep = await db.update_episode(episode_id, upd)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")
    return ep

@router.delete("/{episode_id}")
async def delete_episode(episode_id: str):
    res = await db.delete_episode(episode_id)
    if not res:
        raise HTTPException(status_code=404, detail="Episode not found")
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
        raise HTTPException(
            status_code=500,
            detail=f"Transcription pipeline failed: {str(e)}"
        )

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

    settings_data = await db.get_settings()
    creds = settings_data.get("integration_credentials", {}) or {}
        
    if platform.lower() == "youtube":
        video_url = ep.get("raw_video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="No raw video URL available. Cannot publish to YouTube.")
        youtube_creds = creds.get("youtube", {}) or {}
        tokens = youtube_creds.get("tokens", {}) or {}
        access_token = tokens.get("access_token", "")
        res = await publish_to_youtube(ep["title"], video_url, "public", access_token)
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
        video_url = ep.get("raw_video_url")
        if not video_url:
            raise HTTPException(status_code=400, detail="No raw video URL available. Cannot publish to TikTok.")
        tiktok_creds = creds.get("tiktok", {}) or {}
        tokens = tiktok_creds.get("tokens", {}) or {}
        access_token = tokens.get("access_token", "")
        res = await publish_to_tiktok(ep["title"], video_url, "public", access_token)
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
    }
