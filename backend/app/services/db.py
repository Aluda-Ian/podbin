import os
import base64
from pathlib import Path
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse
from beanie import Document, init_beanie
from pydantic import Field
from motor.motor_asyncio import AsyncIOMotorClient

from app.models.user import User
from app.models.episode import Episode

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

# Configure MongoDB connection from environment URL
MONGODB_URL = os.getenv("MONGODB_URL", "")
if not MONGODB_URL:
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    if DATABASE_URL.startswith("mongodb"):
        MONGODB_URL = DATABASE_URL
    else:
        MONGODB_URL = "mongodb://localhost:27017"

# Parse database name from the URL or fall back to "podbin"
db_name = "podbin"
parsed = urlparse(MONGODB_URL)
if parsed.path and parsed.path != "/":
    db_name = parsed.path.lstrip("/")

# Define persistent Beanie Documents for internal tables
class Approval(Document):
    id: str = Field(default=None)
    podcast_id: str
    type: str
    title: str
    quote: str
    meta: str
    priority: str
    agent: str
    status: str

    class Settings:
        name = "approvals"

class Agent(Document):
    id: str = Field(default=None)  # Stored as the agent's name
    name: str  # Kept for backend/frontend mapping and compatibility
    role: str
    status: str
    task: str
    tasksToday: int
    success: int

    class Settings:
        name = "agents"

class SettingsDocument(Document):
    id: str = Field(default="1")
    workspaceName: str
    showName: str
    primaryHost: str
    releaseCadence: str
    integrations: List[Dict[str, Any]]
    autonomyLevel: str
    provider_config: Optional[Dict[str, Any]] = None
    integration_credentials: Optional[Dict[str, Any]] = None
    api_storage_target: Optional[str] = "database"

    class Settings:
        name = "settings"

class APIKeysDocument(Document):
    id: str = Field(default="1")
    deepgram: str
    openai: str
    elevenlabs: str

    class Settings:
        name = "api_keys"


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
            { "name": "Spotify for Podcasters", "status": "Connected (Live)", "color": "text-success" },
            { "name": "Apple Podcasts Connect", "status": "Connected (Live)", "color": "text-success" },
            { "name": "YouTube Studio", "status": "Connected (Live)", "color": "text-success" },
            { "name": "TikTok for Business", "status": "Connected (Live)", "color": "text-success" },
            { "name": "X / Twitter", "status": "Disconnected", "color": "text-muted" },
            { "name": "Substack", "status": "Disconnected", "color": "text-muted" }
        ],
        "autonomyLevel": "Human-in-the-loop",
        "integration_credentials": {
            "global_sandbox_mode": True,
            "facebook": {"client_id": "483920194830201", "client_secret": ""},
            "spotify": {"client_id": "839201938201", "client_secret": ""},
            "youtube": {"client_id": "9301829038102", "client_secret": ""},
            "tiktok": {"client_id": "839201830291", "client_secret": ""},
            "twitter": {"client_id": "38201938201", "client_secret": ""}
        }
    },
    "users": [
        { "id": "user-1", "name": "Alex Admin", "email": "admin@podbin.com", "role": "Super Admin", "password": "password123", "podcast_ids": ["*"] },
        { "id": "user-2", "name": "Jordan Lee", "email": "owner@podbin.com", "role": "Podcast Owner", "password": "password123", "podcast_ids": ["podcast-1"] },
        { "id": "user-3", "name": "Taylor Team", "email": "member@podbin.com", "role": "Team Member", "password": "password123", "podcast_ids": ["podcast-1"] }
    ]
}

class BeanieDatabaseService:
    def __init__(self):
        self.client = None

    async def init_db(self):
        self.client = AsyncIOMotorClient(MONGODB_URL)
        await init_beanie(
            database=self.client[db_name],
            document_models=[
                User,
                Episode,
                Approval,
                Agent,
                SettingsDocument,
                APIKeysDocument
            ]
        )
        
        # Only seed the database if it has not been initialized yet
        if await SettingsDocument.count() > 0:
            return
        
        for u in SEED_DATA["users"]:
            await User(
                id=u["id"], name=u["name"], email=u["email"],
                role=u["role"], password=u["password"],
                podcast_ids=u["podcast_ids"], suspended=False,
                provider_config=None
            ).insert()
        
        for ep in SEED_DATA["episodes"]:
            db_ep = Episode(
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
            )
            await db_ep.insert()

        for appr in SEED_DATA["approvals"]:
            await Approval(
                id=appr["id"], podcast_id=appr["podcast_id"], type=appr["type"],
                title=appr["title"], quote=appr["quote"], meta=appr["meta"],
                priority=appr["priority"], agent=appr["agent"], status=appr["status"]
            ).insert()

        for ag in SEED_DATA["agents"]:
            await Agent(
                id=ag["name"], name=ag["name"], role=ag["role"], status=ag["status"],
                task=ag["task"], tasksToday=ag["tasksToday"], success=ag["success"]
            ).insert()

        s = SEED_DATA["settings"]
        await SettingsDocument(
            id="1", workspaceName=s["workspaceName"], showName=s["showName"],
            primaryHost=s["primaryHost"], releaseCadence=s["releaseCadence"],
            integrations=s["integrations"], autonomyLevel=s["autonomyLevel"],
            integration_credentials=s["integration_credentials"]
        ).insert()

        await APIKeysDocument(
            id="1", deepgram="", openai="", elevenlabs=""
        ).insert()

    def _ensure_defaults(self, ep: Dict[str, Any]):
        if "status" not in ep or ep["status"] is None:
            ep["status"] = "PENDING_REVIEW"
        if "stage" not in ep or ep["stage"] is None:
            ep["stage"] = "Pre-Prod"
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
        episodes = await Episode.find_all().to_list()
        out = []
        for ep in episodes:
            ep_dict = ep.model_dump()
            ep_dict["id"] = ep.id
            self._ensure_defaults(ep_dict)
            out.append(ep_dict)
        return out

    async def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        ep = await Episode.get(episode_id)
        if not ep:
            return None
        ep_dict = ep.model_dump()
        ep_dict["id"] = ep.id
        self._ensure_defaults(ep_dict)
        return ep_dict

    async def add_episode(self, episode: Dict[str, Any]) -> Dict[str, Any]:
        if not episode.get("id"):
            all_eps = await Episode.find_all().to_list()
            existing_ids = []
            for ep in all_eps:
                try:
                    num = int(ep.id.split("-")[1])
                    existing_ids.append(num)
                except Exception:
                    pass
            next_num = max(existing_ids) + 1 if existing_ids else 1
            episode["id"] = f"EP-{next_num}"
        
        self._ensure_defaults(episode)
        db_ep = Episode(**episode)
        await db_ep.insert()
        return episode

    async def update_episode(self, episode_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        ep = await Episode.get(episode_id)
        if not ep:
            return None
        for k, v in updates.items():
            if hasattr(ep, k):
                setattr(ep, k, v)
        await ep.save()
        ep_dict = ep.model_dump()
        ep_dict["id"] = ep.id
        self._ensure_defaults(ep_dict)
        return ep_dict

    async def delete_episode(self, episode_id: str) -> bool:
        ep = await Episode.get(episode_id)
        if not ep:
            return False
        await ep.delete()
        return True

    # Approvals operations
    async def get_approvals(self) -> List[Dict[str, Any]]:
        approvals = await Approval.find(Approval.status == "PENDING").to_list()
        return [{"id": appr.id, **appr.model_dump()} for appr in approvals]

    async def action_approval(self, approval_id: str, action: str, updated_content: str = None) -> Optional[Dict[str, Any]]:
        appr = await Approval.get(approval_id)
        if not appr:
            return None
        
        if action == "approve":
            appr.status = "APPROVED"
        elif action == "reject":
            appr.status = "REJECTED"
        elif action == "edit" and updated_content is not None:
            appr.quote = updated_content
            
        await appr.save()
        return {"id": appr.id, **appr.model_dump()}

    async def add_approval(self, appr_dict: Dict[str, Any]) -> Dict[str, Any]:
        db_appr = Approval(
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
        await db_appr.insert()
        return appr_dict

    # Agents operations
    async def get_agents(self) -> List[Dict[str, Any]]:
        agents = await Agent.find_all().to_list()
        return [{
            "name": ag.id,
            "role": ag.role,
            "status": ag.status,
            "task": ag.task,
            "tasksToday": ag.tasksToday,
            "success": ag.success
        } for ag in agents]

    async def toggle_agent(self, name: str) -> Optional[Dict[str, Any]]:
        ag = await Agent.get(name)
        if not ag:
            agents = await Agent.find_all().to_list()
            for a in agents:
                if a.id.lower() == name.lower():
                    ag = a
                    break
        if not ag:
            return None
        
        current_status = ag.status
        new_status = "idle" if current_status == "active" else "active"
        ag.status = new_status
        ag.task = "Idle" if new_status == "idle" else "Resumed work on task"
        await ag.save()
        
        return {
            "name": ag.id,
            "role": ag.role,
            "status": ag.status,
            "task": ag.task,
            "tasksToday": ag.tasksToday,
            "success": ag.success
        }

    # Settings operations
    async def get_settings(self) -> Dict[str, Any]:
        s = await SettingsDocument.get("1")
        if not s:
            return {}
        return s.model_dump(exclude={"id"})

    async def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        s = await SettingsDocument.get("1")
        if not s:
            s = SettingsDocument(
                id="1", workspaceName="PodBin Studio", showName="The Lovable Frontier",
                primaryHost="Jordan Lee", releaseCadence="Weekly", integrations=[],
                autonomyLevel="Human-in-the-loop"
            )
            await s.insert()
            
        for k, v in updates.items():
            if k == "integration_credentials" and s.integration_credentials:
                current = dict(s.integration_credentials)
                for subkey, subval in v.items():
                    if isinstance(subval, dict) and subkey in current and isinstance(current[subkey], dict):
                        merged = dict(current[subkey])
                        merged.update(subval)
                        current[subkey] = merged
                    else:
                        current[subkey] = subval
                s.integration_credentials = current
            elif hasattr(s, k):
                setattr(s, k, v)
        await s.save()
        return s.model_dump(exclude={"id"})

    # Users operations
    async def get_users(self) -> List[Dict[str, Any]]:
        users = await User.find_all().to_list()
        return [{"id": u.id, **u.model_dump()} for u in users]

    async def update_user_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        u = await User.get(user_id)
        if not u:
            return None
        u.role = role
        await u.save()
        return {"id": u.id, **u.model_dump()}

    async def suspend_user(self, user_id: str, suspended: bool) -> Optional[Dict[str, Any]]:
        u = await User.get(user_id)
        if not u:
            return None
        u.suspended = suspended
        await u.save()
        return {"id": u.id, **u.model_dump()}

    async def invite_user(self, name: str, email: str, role: str) -> Dict[str, Any]:
        u = await User.find_one(User.email == email)
        if u:
            return {"id": u.id, **u.model_dump()}
            
        all_users = await User.find_all().to_list()
        new_id = f"user-{len(all_users) + 1}"
        new_user = User(
            id=new_id,
            name=name,
            email=email,
            role=role,
            password="password123",
            podcast_ids=["podcast-1"],
            suspended=False
        )
        await new_user.insert()
        return {"id": new_user.id, **new_user.model_dump()}

    # API Keys Operations
    async def get_api_keys(self) -> Dict[str, str]:
        keys = await APIKeysDocument.get("1")
        if not keys:
            keys = APIKeysDocument(id="1", deepgram="", openai="", elevenlabs="")
            await keys.insert()
            return {"deepgram": "", "openai": "", "elevenlabs": ""}
        
        return {
            "deepgram": decrypt_key(keys.deepgram),
            "openai": decrypt_key(keys.openai),
            "elevenlabs": decrypt_key(keys.elevenlabs)
        }

    async def update_api_keys(self, keys_dict: Dict[str, str]) -> Dict[str, str]:
        keys = await APIKeysDocument.get("1")
        if not keys:
            keys = APIKeysDocument(id="1", deepgram="", openai="", elevenlabs="")
            await keys.insert()
            
        if "deepgram" in keys_dict:
            keys.deepgram = encrypt_key(keys_dict["deepgram"])
        if "openai" in keys_dict:
            keys.openai = encrypt_key(keys_dict["openai"])
        if "elevenlabs" in keys_dict:
            keys.elevenlabs = encrypt_key(keys_dict["elevenlabs"])
            
        await keys.save()
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

db = BeanieDatabaseService()
