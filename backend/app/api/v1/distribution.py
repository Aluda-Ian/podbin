from fastapi import APIRouter, HTTPException, Body
from typing import List, Optional
from datetime import datetime
from app.services.db import db
from app.core.config import settings
from app.services.distribution import publish_to_youtube, generate_spotify_rss, publish_to_tiktok
from pydantic import BaseModel

router = APIRouter()


class ScheduleRequest(BaseModel):
    scheduled_at: str  # ISO datetime string
    platforms: List[str]
    title: Optional[str] = None
    description: Optional[str] = None
    privacy_status: Optional[str] = "public"


class ScheduleResponse(BaseModel):
    status: str
    scheduled_at: str
    platforms: List[str]
    sandbox_enforced: bool
    sandbox_notes: List[str]
    details: dict


@router.post("/episodes/{episode_id}/schedule", response_model=ScheduleResponse)
async def schedule_episode(episode_id: str, payload: ScheduleRequest = Body(...)):
    ep = await db.get_episode(episode_id)
    if not ep:
        raise HTTPException(status_code=404, detail="Episode not found")

    sandbox_enforced = settings.IS_SANDBOX_MODE
    sandbox_notes = []
    details = {}

    for platform in payload.platforms:
        plat = platform.lower()

        if plat == "youtube":
            actual_privacy = "private" if sandbox_enforced else (payload.privacy_status or "public")
            res = publish_to_youtube(
                payload.title or ep.get("title", "Untitled"),
                ep.get("raw_video_url") or "mock_path.mp4",
                actual_privacy,
            )
            details[platform] = res
            if sandbox_enforced:
                sandbox_notes.append(f"YouTube: privacy forced to 'private' (sandbox mode)")
            else:
                sandbox_notes.append(f"YouTube: privacy set to '{actual_privacy}'")

        elif plat == "spotify":
            all_eps = await db.get_episodes()
            rss_feed = generate_spotify_rss(all_eps)
            details[platform] = {"rss_generated": True}
            if sandbox_enforced:
                sandbox_notes.append("Spotify RSS: <sandbox enabled=\"true\"/> injected (sandbox mode)")
            else:
                sandbox_notes.append("Spotify RSS generated without sandbox restriction")

        elif plat in ("apple", "apple podcasts"):
            details[platform] = {"status": "scheduled", "platform": "Apple Podcasts Connect"}
            if sandbox_enforced:
                sandbox_notes.append(f"{platform}: Submission blocked in sandbox mode — no-op")
            else:
                sandbox_notes.append(f"{platform}: Scheduled for live distribution")

        elif plat == "tiktok":
            actual_privacy = "private" if sandbox_enforced else (payload.privacy_status or "public")
            res = publish_to_tiktok(
                payload.title or ep.get("title", "Untitled"),
                ep.get("raw_video_url") or "mock_path.mp4",
                actual_privacy,
            )
            details[platform] = res
            if sandbox_enforced:
                sandbox_notes.append("TikTok: privacy forced to 'private' (sandbox mode)")
            else:
                sandbox_notes.append(f"TikTok: privacy set to '{actual_privacy}'")

        elif plat in ("instagram", "twitter", "x", "linkedin", "facebook"):
            details[platform] = {"status": "scheduled", "platform": platform}
            if sandbox_enforced:
                sandbox_notes.append(f"{platform}: Scheduled in sandbox — post will NOT go live")
            else:
                sandbox_notes.append(f"{platform}: Scheduled for live publication")

        else:
            sandbox_notes.append(f"{platform}: Unknown platform — skipped")

    # Persist the schedule in the episode record
    existing_schedule = ep.get("socials_schedule") or []
    schedule_entry = {
        "id": f"sched-{episode_id}-{len(existing_schedule) + 1}",
        "scheduled_at": payload.scheduled_at,
        "platforms": payload.platforms,
        "sandbox_enforced": sandbox_enforced,
        "created_at": datetime.now().isoformat(),
    }
    existing_schedule.append(schedule_entry)
    await db.update_episode(episode_id, {"socials_schedule": existing_schedule})

    return ScheduleResponse(
        status="scheduled" if not sandbox_enforced else "sandbox_scheduled",
        scheduled_at=payload.scheduled_at,
        platforms=payload.platforms,
        sandbox_enforced=sandbox_enforced,
        sandbox_notes=sandbox_notes,
        details=details,
    )
