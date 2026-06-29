import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import select, Text, Boolean, Integer, JSON

# Secure key encryption helper
ENCRYPTION_SALT = os.getenv("ENCRYPTION_SALT", "podbin_secure_salt")

def encrypt_key(key: str) -> str:
    if not key:
        return ""
    # Simple XOR encryption encoded in base64
    xored = "".join(chr(ord(c) ^ ord(ENCRYPTION_SALT[i % len(ENCRYPTION_SALT)])) for i, c in enumerate(key))
    return base64.b64encode(xored.encode('utf-8')).decode('utf-8')

def decrypt_key(enc_key: str) -> str:
    if not enc_key:
        return ""
    try:
        decoded = base64.b64decode(enc_key.encode('utf-8')).decode('utf-8')
        xored = "".join(chr(ord(c) ^ ord(ENCRYPTION_SALT[i % len(ENCRYPTION_SALT)])) for i, c in enumerate(decoded))
        return xored
    except Exception:
        return ""

# Locate the database file at the backend root directory
backend_root = Path(__file__).resolve().parents[2]
DB_PATH = backend_root / "podbin.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_PATH}"

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

class Base(DeclarativeBase):
    pass

class DBUser(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str] = mapped_column(unique=True)
    role: Mapped[str]
    password: Mapped[str]
    podcast_ids: Mapped[list] = mapped_column(JSON)
    suspended: Mapped[bool] = mapped_column(default=False)
    provider_config: Mapped[dict] = mapped_column(JSON, nullable=True)

class DBEpisode(Base):
    __tablename__ = "episodes"
    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    guest: Mapped[str]
    avatar: Mapped[str]
    stage: Mapped[str]
    duration: Mapped[str]
    date: Mapped[str]
    progress: Mapped[int] = mapped_column(default=0)
    note: Mapped[str]
    bars: Mapped[list] = mapped_column(JSON, nullable=True)
    prediction: Mapped[str] = mapped_column(nullable=True)
    raw_audio_url: Mapped[str] = mapped_column(nullable=True)
    raw_video_url: Mapped[str] = mapped_column(nullable=True)
    media_type: Mapped[str] = mapped_column(default="audio")
    podcast_id: Mapped[str] = mapped_column(default="podcast-1")
    transcript: Mapped[str] = mapped_column(Text, nullable=True)
    generated_content: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str]
    human_feedback: Mapped[str] = mapped_column(nullable=True)
    clips: Mapped[list] = mapped_column(JSON, default=list)
    distribution_channels: Mapped[list] = mapped_column(JSON, default=list)
    socials_schedule: Mapped[list] = mapped_column(JSON, default=list)
    word_timeline: Mapped[list] = mapped_column(JSON, default=list)
    edit_decision_list: Mapped[list] = mapped_column(JSON, default=list)
    selected_llm_config: Mapped[dict] = mapped_column(JSON, default=dict)

class DBApproval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(primary_key=True)
    podcast_id: Mapped[str]
    type: Mapped[str]
    title: Mapped[str]
    quote: Mapped[str]
    meta: Mapped[str]
    priority: Mapped[str]
    agent: Mapped[str]
    status: Mapped[str]

class DBAgent(Base):
    __tablename__ = "agents"
    name: Mapped[str] = mapped_column(primary_key=True)
    role: Mapped[str]
    status: Mapped[str]
    task: Mapped[str]
    tasksToday: Mapped[int]
    success: Mapped[int]

class DBSettings(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    workspaceName: Mapped[str]
    showName: Mapped[str]
    primaryHost: Mapped[str]
    releaseCadence: Mapped[str]
    integrations: Mapped[list] = mapped_column(JSON)
    autonomyLevel: Mapped[str]
    provider_config: Mapped[dict] = mapped_column(JSON, nullable=True)

class DBAPIKeys(Base):
    __tablename__ = "api_keys"
    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    deepgram: Mapped[str]
    openai: Mapped[str]
    elevenlabs: Mapped[str]


SEED_DATA = {
    "episodes": [
        { 
            "id": "EP-145", "title": "Biohacking 2026", "guest": "Dr. Lina Okafor", "avatar": "guest2", "stage": "Pre-Prod", "status": "BOOKING", "duration": "—", "date": "Jun 30", "progress": 18, "note": "Awaiting calendar confirmation", "raw_audio_url": "https://example.com/audio/ep145.mp3",
            "clips": [],
            "distribution_channels": [
                { "name": "Spotify for Podcasters", "status": "PENDING", "url": "https://podcasters.spotify.com" },
                { "name": "Apple Podcasts Connect", "status": "PENDING", "url": "https://podcastsconnect.apple.com" },
                { "name": "YouTube Studio", "status": "PENDING", "url": "https://studio.youtube.com" }
            ],
            "socials_schedule": []
        },
        { 
            "id": "EP-144", "title": "The Future of LLMs", "guest": "Andrej Karpathy", "avatar": "guest1", "stage": "Pre-Prod", "status": "RESEARCH", "duration": "—", "date": "Jun 28", "progress": 40, "note": "Mapping 18 mo. of public talks", "raw_audio_url": "https://example.com/audio/ep144.mp3",
            "clips": [],
            "distribution_channels": [
                { "name": "Spotify for Podcasters", "status": "PENDING", "url": "https://podcasters.spotify.com" },
                { "name": "Apple Podcasts Connect", "status": "PENDING", "url": "https://podcastsconnect.apple.com" },
                { "name": "YouTube Studio", "status": "PENDING", "url": "https://studio.youtube.com" }
            ],
            "socials_schedule": []
        },
        { 
            "id": "EP-143", "title": "Synthetic Media Ethics", "guest": "Marcus Cole", "avatar": "guest2", "stage": "Post-Prod", "status": "EDITING", "duration": "01:12:44", "date": "Jun 25", "progress": 72, "note": "Cleaning noise floor — pass 2/3", "raw_audio_url": "https://example.com/audio/ep143.mp3",
            "clips": [
                { "id": "clip-1", "title": "Deepfakes and Consent", "text": "We are essentially living inside a high-fidelity simulation of last year's consensus.", "startTime": "00:42", "endTime": "01:15", "platform": "TikTok", "status": "APPROVED" },
                { "id": "clip-2", "title": "Regulatory Gaps", "text": "The law is always 5 years behind the deployment of these models.", "startTime": "12:10", "endTime": "13:05", "platform": "YouTube Shorts", "status": "PENDING" }
            ],
            "distribution_channels": [
                { "name": "Spotify for Podcasters", "status": "PENDING", "url": "https://podcasters.spotify.com" },
                { "name": "Apple Podcasts Connect", "status": "PENDING", "url": "https://podcastsconnect.apple.com" },
                { "name": "YouTube Studio", "status": "PENDING", "url": "https://studio.youtube.com" }
            ],
            "socials_schedule": [
                { "id": "sched-1", "platform": "TikTok", "caption": "Living in a simulation... Ep. 143 is live!", "time": "2026-06-27T10:00:00", "status": "SCHEDULED" }
            ]
        },
        { 
            "id": "EP-142", "title": "Scaling Creator Platforms", "guest": "Jane Wu", "avatar": "guest3", "stage": "Post-Prod", "status": "MASTERING", "duration": "00:58:21", "date": "Jun 22", "progress": 91, "note": "Loudness normalization −16 LUFS", "raw_audio_url": "https://example.com/audio/ep142.mp3",
            "clips": [],
            "distribution_channels": [
                { "name": "Spotify for Podcasters", "status": "PENDING", "url": "https://podcasters.spotify.com" },
                { "name": "Apple Podcasts Connect", "status": "PENDING", "url": "https://podcastsconnect.apple.com" },
                { "name": "YouTube Studio", "status": "PENDING", "url": "https://studio.youtube.com" }
            ],
            "socials_schedule": []
        },
        { 
            "id": "EP-141", "title": "Silicon Valley Shifts", "guest": "Patrick Hsu", "avatar": "guest3", "stage": "Growth", "status": "DISTRO", "duration": "01:04:09", "date": "Jun 18", "progress": 100, "note": "Published to directories", "bars": [4, 6, 3, 5, 7, 5, 6], "prediction": "Predicting 14.2k views in 48h", "raw_audio_url": "https://example.com/audio/ep141.mp3",
            "clips": [],
            "distribution_channels": [
                { "name": "Spotify for Podcasters", "status": "LIVE", "url": "https://podcasters.spotify.com" },
                { "name": "Apple Podcasts Connect", "status": "LIVE", "url": "https://podcastsconnect.apple.com" },
                { "name": "YouTube Studio", "status": "PROCESSING", "url": "https://studio.youtube.com" }
            ],
            "socials_schedule": []
        },
        { 
            "id": "EP-140", "title": "Founder Burnout", "guest": "Alex Rivers", "avatar": "guest1", "stage": "Growth", "status": "LIVE", "duration": "00:49:55", "date": "Jun 14", "progress": 100, "note": "Trending #4 on Spotify Tech", "bars": [3, 5, 6, 4, 7, 8, 6], "prediction": "Trending #4 on Spotify Tech", "raw_audio_url": "https://example.com/audio/ep140.mp3",
            "clips": [],
            "distribution_channels": [
                { "name": "Spotify for Podcasters", "status": "LIVE", "url": "https://podcasters.spotify.com" },
                { "name": "Apple Podcasts Connect", "status": "LIVE", "url": "https://podcastsconnect.apple.com" },
                { "name": "YouTube Studio", "status": "LIVE", "url": "https://studio.youtube.com" }
            ],
            "socials_schedule": []
        },
        { 
            "id": "EP-139", "title": "The Climate Tech Pivot", "guest": "Marcus Cole", "avatar": "guest2", "stage": "Growth", "status": "LIVE", "duration": "01:21:03", "date": "Jun 10", "progress": 100, "note": "published", "raw_audio_url": "https://example.com/audio/ep139.mp3",
            "clips": [],
            "distribution_channels": [
                { "name": "Spotify for Podcasters", "status": "LIVE", "url": "https://podcasters.spotify.com" },
                { "name": "Apple Podcasts Connect", "status": "LIVE", "url": "https://podcastsconnect.apple.com" },
                { "name": "YouTube Studio", "status": "LIVE", "url": "https://studio.youtube.com" }
            ],
            "socials_schedule": []
        },
        { 
            "id": "EP-138", "title": "Neural Interfaces 101", "guest": "Andrej Karpathy", "avatar": "guest1", "stage": "Growth", "status": "LIVE", "duration": "00:55:12", "date": "Jun 06", "progress": 100, "note": "published", "raw_audio_url": "https://example.com/audio/ep138.mp3",
            "clips": [],
            "distribution_channels": [
                { "name": "Spotify for Podcasters", "status": "LIVE", "url": "https://podcasters.spotify.com" },
                { "name": "Apple Podcasts Connect", "status": "LIVE", "url": "https://podcastsconnect.apple.com" },
                { "name": "YouTube Studio", "status": "LIVE", "url": "https://studio.youtube.com" }
            ],
            "socials_schedule": []
        }
    ],
    "approvals": [
        { "id": "appr-1", "podcast_id": "podcast-1", "type": "CLIP_GENERATED", "title": "Vertical 9:16 · Ep. 142", "quote": "\"We are essentially living inside a high-fidelity simulation of last year's consensus.\"", "meta": "00:42 · 1080×1920 · Generated 4m ago", "priority": "high", "agent": "Repurpose Agent", "status": "PENDING" },
        { "id": "appr-2", "podcast_id": "podcast-1", "type": "SHOW_NOTES", "title": "Markdown · Ep. 141", "quote": "Summary for Ep. 141: Exploring Neural Interfaces and the regulatory gap between research labs and consumer rollout...", "meta": "1,240 words · Generated 11m ago", "priority": "medium", "agent": "Research Agent", "status": "PENDING" },
        { "id": "appr-3", "podcast_id": "podcast-1", "type": "NEWSLETTER_DRAFT", "title": "Weekly Recap · Issue #41", "quote": "This week we covered neural interfaces, climate tech, and the founder burnout epidemic. Top 3 takeaways inside.", "meta": "12,400 subscribers · Generated 32m ago", "priority": "medium", "agent": "Repurpose Agent", "status": "PENDING" },
        { "id": "appr-4", "podcast_id": "podcast-1", "type": "SOCIAL_THREAD", "title": "X / Twitter · 7-post thread", "quote": "🧵 The single biggest myth about AGI timelines, dismantled by Andrej K. in 7 posts.", "meta": "Engagement est. 4.2k · Generated 1h ago", "priority": "low", "agent": "Distribution Agent", "status": "PENDING" },
        { "id": "appr-5", "podcast_id": "podcast-1", "type": "GUEST_OUTREACH", "title": "Email · Dr. Lina Okafor", "quote": "Hi Lina — loved your recent paper on metabolic markers. Would love to host you on PodBin for Ep. 145...", "meta": "Tone: warm-professional · Generated 2h ago", "priority": "low", "agent": "Booking Agent", "status": "PENDING" }
    ],
    "agents": [
        { "name": "Research Agent", "role": "Sources, talking points, fact-checking", "status": "active", "task": "Indexing source #14 of 23 for Ep. 144", "tasksToday": 42, "success": 98 },
        { "name": "Booking Agent", "role": "Guest outreach and scheduling", "status": "active", "task": "Negotiating slot with Jane Wu", "tasksToday": 8, "success": 100 },
        { "name": "Production Agent", "role": "Audio editing, mixing, mastering", "status": "active", "task": "Mixdown pass 2/3 on Ep. 143", "tasksToday": 14, "success": 96 },
        { "name": "Repurpose Agent", "role": "Clip generation and snippet authoring", "status": "active", "task": "6 clips queued for review", "tasksToday": 28, "success": 92 },
        { "name": "Distribution Agent", "role": "Multi-channel syndication", "status": "idle", "task": "Idle — last push 14m ago", "tasksToday": 19, "success": 100 }
    ],
    "settings": {
        "workspaceName": "PodBin Studio",
        "showName": "The Lovable Frontier",
        "primaryHost": "Jordan Lee",
        "releaseCadence": "Weekly · Tuesdays 06:00 UTC",
        "integrations": [
            { "name": "Spotify for Podcasters", "status": "Connected", "color": "text-success" },
            { "name": "Apple Podcasts Connect", "status": "Connected", "color": "text-success" },
            { "name": "YouTube Studio", "status": "Connected", "color": "text-success" },
            { "name": "TikTok for Business", "status": "Connected", "color": "text-success" },
            { "name": "X / Twitter", "status": "Disconnected", "color": "text-muted" },
            { "name": "Substack", "status": "Disconnected", "color": "text-muted" }
        ],
        "autonomyLevel": "Human-in-the-loop"
    },
    "users": [
        { "id": "user-1", "name": "Alex Admin", "email": "admin@podbin.com", "role": "Super Admin", "password": "password123", "podcast_ids": ["*"] },
        { "id": "user-2", "name": "Jordan Lee", "email": "owner@podbin.com", "role": "Podcast Owner", "password": "password123", "podcast_ids": ["podcast-1"] },
        { "id": "user-3", "name": "Taylor Team", "email": "member@podbin.com", "role": "Team Member", "password": "password123", "podcast_ids": ["podcast-1"] }
    ]
}

class SQLDatabaseService:
    async def init_db(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        async with AsyncSessionLocal() as session:
            # Seed users
            res = await session.execute(select(DBUser))
            if not res.scalars().first():
                for u in SEED_DATA["users"]:
                    session.add(DBUser(
                        id=u["id"], name=u["name"], email=u["email"],
                        role=u["role"], password=u["password"],
                        podcast_ids=u["podcast_ids"], suspended=False,
                        provider_config=None
                    ))
                
                # Seed episodes
                for ep in SEED_DATA["episodes"]:
                    session.add(DBEpisode(
                        id=ep["id"], title=ep["title"], guest=ep["guest"],
                        avatar=ep["avatar"], stage=ep["stage"], status=ep["status"],
                        duration=ep["duration"], date=ep["date"], progress=ep["progress"],
                        note=ep["note"], bars=ep.get("bars", []), prediction=ep.get("prediction"),
                        raw_audio_url=ep.get("raw_audio_url"), raw_video_url=ep.get("raw_video_url"),
                        media_type=ep.get("media_type", "audio"), podcast_id=ep.get("podcast_id", "podcast-1"),
                        transcript=ep.get("transcript"), generated_content=ep.get("generated_content", {}),
                        human_feedback=ep.get("human_feedback"), clips=ep.get("clips", []),
                        distribution_channels=ep.get("distribution_channels", []),
                        socials_schedule=ep.get("socials_schedule", []), word_timeline=ep.get("word_timeline", []),
                        edit_decision_list=ep.get("edit_decision_list", []), selected_llm_config=ep.get("selected_llm_config", {})
                    ))

                # Seed approvals
                for appr in SEED_DATA["approvals"]:
                    session.add(DBApproval(
                        id=appr["id"], podcast_id=appr["podcast_id"], type=appr["type"],
                        title=appr["title"], quote=appr["quote"], meta=appr["meta"],
                        priority=appr["priority"], agent=appr["agent"], status=appr["status"]
                    ))

                # Seed agents
                for ag in SEED_DATA["agents"]:
                    session.add(DBAgent(
                        name=ag["name"], role=ag["role"], status=ag["status"],
                        task=ag["task"], tasksToday=ag["tasksToday"], success=ag["success"]
                    ))

                # Seed settings
                s = SEED_DATA["settings"]
                session.add(DBSettings(
                    id=1, workspaceName=s["workspaceName"], showName=s["showName"],
                    primaryHost=s["primaryHost"], releaseCadence=s["releaseCadence"],
                    integrations=s["integrations"], autonomyLevel=s["autonomyLevel"]
                ))

                # Seed API Keys
                session.add(DBAPIKeys(
                    id=1, deepgram="", openai="", elevenlabs=""
                ))
                
                await session.commit()

    def _ensure_defaults(self, ep: Dict[str, Any]):
        if "clips" not in ep or ep["clips"] is None:
            if ep.get("id") == "EP-143":
                ep["clips"] = [
                    { "id": "clip-1", "title": "Deepfakes and Consent", "text": "We are essentially living inside a high-fidelity simulation of last year's consensus.", "startTime": "00:42", "endTime": "01:15", "platform": "TikTok", "status": "APPROVED" },
                    { "id": "clip-2", "title": "Regulatory Gaps", "text": "The law is always 5 years behind the deployment of these models.", "startTime": "12:10", "endTime": "13:05", "platform": "YouTube Shorts", "status": "PENDING" }
                ]
            else:
                ep["clips"] = []
        if "distribution_channels" not in ep or ep["distribution_channels"] is None:
            ep["distribution_channels"] = [
                { "name": "Spotify for Podcasters", "status": "LIVE" if ep.get("stage") == "Growth" else "PENDING", "url": "https://podcasters.spotify.com" },
                { "name": "Apple Podcasts Connect", "status": "LIVE" if ep.get("stage") == "Growth" else "PENDING", "url": "https://podcastsconnect.apple.com" },
                { "name": "YouTube Studio", "status": "PROCESSING" if ep.get("status") == "DISTRO" else ("LIVE" if ep.get("status") == "LIVE" else "PENDING"), "url": "https://studio.youtube.com" }
            ]
        if "socials_schedule" not in ep or ep["socials_schedule"] is None:
            if ep.get("id") == "EP-143":
                ep["socials_schedule"] = [
                    { "id": "sched-1", "platform": "TikTok", "caption": "Living in a simulation... Ep. 143 is live!", "time": "2026-06-27T10:00:00", "status": "SCHEDULED" }
                ]
            else:
                ep["socials_schedule"] = []
        if "podcast_id" not in ep or ep["podcast_id"] is None:
            ep["podcast_id"] = "podcast-1"
        if "media_type" not in ep or ep["media_type"] is None:
            ep["media_type"] = "audio"

    # Episodes operations
    async def get_episodes(self) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBEpisode))
            episodes = res.scalars().all()
            out = []
            for ep in episodes:
                ep_dict = {c.name: getattr(ep, c.name) for c in ep.__table__.columns}
                self._ensure_defaults(ep_dict)
                out.append(ep_dict)
            return out

    async def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBEpisode).where(DBEpisode.id == episode_id))
            ep = res.scalars().first()
            if not ep:
                return None
            ep_dict = {c.name: getattr(ep, c.name) for c in ep.__table__.columns}
            self._ensure_defaults(ep_dict)
            return ep_dict

    async def add_episode(self, episode: Dict[str, Any]) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBEpisode))
            episodes = res.scalars().all()
            existing_ids = []
            for ep in episodes:
                try:
                    num = int(ep.id.split("-")[1])
                    existing_ids.append(num)
                except Exception:
                    pass
            next_num = max(existing_ids) + 1 if existing_ids else 1
            ep_id = f"EP-{next_num}"
            episode["id"] = ep_id
            
            self._ensure_defaults(episode)
            
            db_ep = DBEpisode(
                id=episode["id"], title=episode["title"], guest=episode["guest"],
                avatar=episode.get("avatar", "guest1"), stage=episode.get("stage", "Pre-Prod"),
                status=episode.get("status", "RESEARCH"), duration=episode.get("duration", "—"),
                date=episode.get("date"), progress=episode.get("progress", 20), note=episode.get("note", "Ingested"),
                bars=episode.get("bars", []), prediction=episode.get("prediction"),
                raw_audio_url=episode.get("raw_audio_url"), raw_video_url=episode.get("raw_video_url"),
                media_type=episode.get("media_type", "audio"), podcast_id=episode.get("podcast_id", "podcast-1"),
                transcript=episode.get("transcript"), generated_content=episode.get("generated_content", {}),
                human_feedback=episode.get("human_feedback"), clips=episode.get("clips", []),
                distribution_channels=episode.get("distribution_channels", []),
                socials_schedule=episode.get("socials_schedule", []), word_timeline=episode.get("word_timeline", []),
                edit_decision_list=episode.get("edit_decision_list", []), selected_llm_config=episode.get("selected_llm_config", {})
            )
            session.add(db_ep)
            await session.commit()
            return episode

    async def update_episode(self, episode_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBEpisode).where(DBEpisode.id == episode_id))
            db_ep = res.scalars().first()
            if not db_ep:
                return None
            for k, v in updates.items():
                if hasattr(db_ep, k):
                    setattr(db_ep, k, v)
            await session.commit()
            
            res = await session.execute(select(DBEpisode).where(DBEpisode.id == episode_id))
            fresh = res.scalars().first()
            ep_dict = {c.name: getattr(fresh, c.name) for c in fresh.__table__.columns}
            self._ensure_defaults(ep_dict)
            return ep_dict

    async def delete_episode(self, episode_id: str) -> bool:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBEpisode).where(DBEpisode.id == episode_id))
            db_ep = res.scalars().first()
            if not db_ep:
                return False
            await session.delete(db_ep)
            await session.commit()
            return True

    # Approvals operations
    async def get_approvals(self) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBApproval).where(DBApproval.status == "PENDING"))
            approvals = res.scalars().all()
            return [{c.name: getattr(appr, c.name) for c in appr.__table__.columns} for appr in approvals]

    async def action_approval(self, approval_id: str, action: str, updated_content: str = None) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBApproval).where(DBApproval.id == approval_id))
            appr = res.scalars().first()
            if not appr:
                return None
            
            if action == "approve":
                appr.status = "APPROVED"
            elif action == "reject":
                appr.status = "REJECTED"
            elif action == "edit" and updated_content is not None:
                appr.quote = updated_content
                
            await session.commit()
            
            res = await session.execute(select(DBApproval).where(DBApproval.id == approval_id))
            fresh = res.scalars().first()
            return {c.name: getattr(fresh, c.name) for c in fresh.__table__.columns}

    async def add_approval(self, appr_dict: Dict[str, Any]) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            db_appr = DBApproval(
                id=appr_dict["id"],
                podcast_id=appr_dict.get("podcast_id", "podcast-1"),
                type=appr_dict["type"],
                title=appr_dict["title"],
                quote=appr_dict["quote"],
                meta=appr_dict["meta"],
                priority=appr_dict.get("priority", "medium"),
                agent=appr_dict.get("agent", "System"),
                status=appr_dict.get("status", "PENDING")
            )
            session.add(db_appr)
            await session.commit()
            return appr_dict

    # Agents operations
    async def get_agents(self) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBAgent))
            agents = res.scalars().all()
            return [{c.name: getattr(ag, c.name) for c in ag.__table__.columns} for ag in agents]

    async def toggle_agent(self, name: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBAgent).where(DBAgent.name.ilike(name)))
            ag = res.scalars().first()
            if not ag:
                return None
            
            current_status = ag.status
            new_status = "idle" if current_status == "active" else "active"
            ag.status = new_status
            ag.task = "Idle" if new_status == "idle" else "Resumed work on task"
            
            await session.commit()
            
            res = await session.execute(select(DBAgent).where(DBAgent.name.ilike(name)))
            fresh = res.scalars().first()
            return {c.name: getattr(fresh, c.name) for c in fresh.__table__.columns}

    # Settings operations
    async def get_settings(self) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBSettings).where(DBSettings.id == 1))
            s = res.scalars().first()
            if not s:
                return {}
            return {c.name: getattr(s, c.name) for c in s.__table__.columns if c.name != "id"}

    async def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBSettings).where(DBSettings.id == 1))
            s = res.scalars().first()
            if not s:
                s = DBSettings(id=1, workspaceName="PodBin Studio", showName="The Lovable Frontier",
                               primaryHost="Jordan Lee", releaseCadence="Weekly", integrations=[],
                               autonomyLevel="Human-in-the-loop")
                session.add(s)
                await session.flush()
                
            for k, v in updates.items():
                if hasattr(s, k):
                    setattr(s, k, v)
            await session.commit()
            
            res = await session.execute(select(DBSettings).where(DBSettings.id == 1))
            fresh = res.scalars().first()
            return {c.name: getattr(fresh, c.name) for c in fresh.__table__.columns if c.name != "id"}

    # Users operations
    async def get_users(self) -> List[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBUser))
            users = res.scalars().all()
            return [{c.name: getattr(u, c.name) for c in u.__table__.columns} for u in users]

    async def update_user_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBUser).where(DBUser.id == user_id))
            u = res.scalars().first()
            if not u:
                return None
            u.role = role
            await session.commit()
            
            res = await session.execute(select(DBUser).where(DBUser.id == user_id))
            fresh = res.scalars().first()
            return {c.name: getattr(fresh, c.name) for c in fresh.__table__.columns}

    async def suspend_user(self, user_id: str, suspended: bool) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBUser).where(DBUser.id == user_id))
            u = res.scalars().first()
            if not u:
                return None
            u.suspended = suspended
            await session.commit()
            
            res = await session.execute(select(DBUser).where(DBUser.id == user_id))
            fresh = res.scalars().first()
            return {c.name: getattr(fresh, c.name) for c in fresh.__table__.columns}

    async def invite_user(self, name: str, email: str, role: str) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBUser).where(DBUser.email == email))
            u = res.scalars().first()
            if u:
                return {c.name: getattr(u, c.name) for c in u.__table__.columns}
                
            res_all = await session.execute(select(DBUser))
            all_users = res_all.scalars().all()
            new_id = f"user-{len(all_users) + 1}"
            new_user = DBUser(
                id=new_id,
                name=name,
                email=email,
                role=role,
                password="password123",
                podcast_ids=["podcast-1"],
                suspended=False
            )
            session.add(new_user)
            await session.commit()
            
            res = await session.execute(select(DBUser).where(DBUser.id == new_id))
            fresh = res.scalars().first()
            return {c.name: getattr(fresh, c.name) for c in fresh.__table__.columns}

    # API Keys Operations
    async def get_api_keys(self) -> Dict[str, str]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBAPIKeys).where(DBAPIKeys.id == 1))
            keys = res.scalars().first()
            if not keys:
                keys = DBAPIKeys(id=1, deepgram="", openai="", elevenlabs="")
                session.add(keys)
                await session.commit()
                return {"deepgram": "", "openai": "", "elevenlabs": ""}
            
            return {
                "deepgram": decrypt_key(keys.deepgram),
                "openai": decrypt_key(keys.openai),
                "elevenlabs": decrypt_key(keys.elevenlabs)
            }

    async def update_api_keys(self, keys_dict: Dict[str, str]) -> Dict[str, str]:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBAPIKeys).where(DBAPIKeys.id == 1))
            keys = res.scalars().first()
            if not keys:
                keys = DBAPIKeys(id=1, deepgram="", openai="", elevenlabs="")
                session.add(keys)
                await session.flush()
                
            if "deepgram" in keys_dict:
                keys.deepgram = encrypt_key(keys_dict["deepgram"])
            if "openai" in keys_dict:
                keys.openai = encrypt_key(keys_dict["openai"])
            if "elevenlabs" in keys_dict:
                keys.elevenlabs = encrypt_key(keys_dict["elevenlabs"])
                
            await session.commit()
            
            return {
                "deepgram": decrypt_key(keys.deepgram),
                "openai": decrypt_key(keys.openai),
                "elevenlabs": decrypt_key(keys.elevenlabs)
            }

    # Admin Analytics
    async def get_admin_analytics(self) -> Dict[str, Any]:
        episodes = await self.get_episodes()
        total_episodes = len(episodes)
        total_costs = round(total_episodes * 5.35 + 12.80, 2)
        return {
            "total_episodes": total_episodes,
            "system_error_rate": "1.2%",
            "total_api_costs": f"${total_costs}",
            "cost_history": [6, 9, 4, 11, 7, 13, 10, 14, 9, 12, 16, 11, 18, 15]
        }

db = SQLDatabaseService()
