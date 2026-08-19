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
from app.models.notification import Notification

# Secure key encryption helper
ENCRYPTION_SALT = os.getenv("ENCRYPTION_SALT", "podule_secure_salt")

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
MONGODB_URL = os.getenv("MONGODB_URL", os.getenv("DATABASE_URL", ""))

# Parse database name from the URL or fall back to "podule"
db_name = "podule"
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
    operational_tier: Optional[str] = "FREE"
    orchestrator_model: Optional[str] = "Podule Copilot (Free)"
    transcription_model: Optional[str] = "Faster-Whisper (Local CPU)"
    tts_model: Optional[str] = "gTTS (Free)"
    image_model: Optional[str] = "Stable Diffusion (Free)"
    video_model: Optional[str] = "FFmpeg Auto Crop (Free)"
    avatar_model: Optional[str] = "Simulated Avatar (Free)"

    class Settings:
        name = "settings"

class APIKeysDocument(Document):
    id: str = Field(default="1")
    deepgram: str
    openai: str
    elevenlabs: str

    class Settings:
        name = "api_keys"




class BeanieDatabaseService:
    def __init__(self):
        self.client = None

    @property
    def is_configured(self) -> bool:
        return bool(MONGODB_URL and MONGODB_URL.startswith("mongodb"))

    async def init_db(self):
        if not self.is_configured:
            raise RuntimeError("A valid remote MongoDB URI (MONGODB_URL or DATABASE_URL) must be provided in the environment.")
        self.client = AsyncIOMotorClient(MONGODB_URL)
        await init_beanie(
            database=self.client[db_name],
            document_models=[
                User,
                Episode,
                Approval,
                Agent,
                SettingsDocument,
                APIKeysDocument,
                Notification
            ]
        )
        
        # Seed default super admin
        admin_user = await User.find_one(User.email == "info@vendatechnologies.com")
        if not admin_user:
            from app.core.security import hash_password
            all_users = await User.find_all().to_list()
            new_admin = User(
                id=f"user-{len(all_users) + 1}",
                name="Ian Aluda",
                email="info@vendatechnologies.com",
                role="Super Admin",
                password=hash_password("@Munangwe212"),
                podcast_ids=["*"],
                suspended=False,
                is_verified=True
            )
            await new_admin.insert()

        # Seed initial completed agent activity notifications
        existing_notifs = await Notification.find_all().to_list()
        if not existing_notifs:
            initial_agent_logs = [
                ("AGENT_RESEARCH", "Drafting talking points for Andrej K. — Ep. 144"),
                ("AGENT_BOOKING", "Confirmed Sarah Chen for Tue 14:00 UTC"),
                ("AGENT_PROD", "De-essing vocal track on segment 04"),
                ("AGENT_REPURPOSE", "Generated 6 vertical clips from Ep. 142"),
                ("AGENT_DISTRO", "Pushed to Spotify, Apple, YouTube — syndication 100%"),
                ("AGENT_RESEARCH", "Indexing 23 source articles for Climate Tech pivot")
            ]
            for tag, msg in initial_agent_logs:
                await Notification(
                    user_id="user-1",
                    type="success",
                    title=tag,
                    message=msg,
                    read=False
                ).insert()

    def _ensure_defaults(self, ep: Dict[str, Any]):
        if "status" not in ep or ep["status"] is None:
            ep["status"] = "PENDING_REVIEW"
        if "stage" not in ep or ep["stage"] is None:
            ep["stage"] = "Pre-Prod"
        if "clips" not in ep or ep["clips"] is None:
            ep["clips"] = []
        if "distribution_channels" not in ep or ep["distribution_channels"] is None:
            ep["distribution_channels"] = []
        if "socials_schedule" not in ep or ep["socials_schedule"] is None:
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

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        all_users = await User.find_all().to_list()
        new_id = f"user-{len(all_users) + 1}"
        new_user = User(
            id=new_id,
            name=user_data.get("name", ""),
            email=user_data.get("email", ""),
            role=user_data.get("role", "Team Member"),
            password=user_data.get("password", ""),
            podcast_ids=user_data.get("podcast_ids", ["podcast-1"]),
            suspended=False
        )
        await new_user.insert()
        return {"id": new_user.id, **new_user.model_dump()}

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        u = await User.get(user_id)
        if not u:
            return None
        for k, v in updates.items():
            if hasattr(u, k):
                setattr(u, k, v)
        await u.save()
        return {"id": u.id, **u.model_dump()}

    async def invite_user(self, name: str, email: str, role: str) -> Dict[str, Any]:
        u = await User.find_one(User.email == email)
        if u:
            return {"id": u.id, **u.model_dump()}
        return await self.create_user({"name": name, "email": email, "role": role, "password": "password123"})

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
        users = await self.get_users()
        return {
            "total_episodes": total_episodes,
            "total_users": len(users),
            "total_api_costs": None,
            "cost_history": []
        }

    # Notifications operations
    async def get_notifications(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        notifs = await Notification.find(Notification.user_id == user_id).sort(-Notification.created_at).limit(limit).to_list()
        return [{"id": n.id, **n.model_dump()} for n in notifs]

    async def create_notification(self, notif: Dict[str, Any]) -> Dict[str, Any]:
        db_n = Notification(**notif)
        await db_n.insert()
        return {"id": db_n.id, **db_n.model_dump()}

    async def mark_notification_read(self, notif_id: str) -> Optional[Dict[str, Any]]:
        n = await Notification.get(notif_id)
        if not n:
            return None
        n.read = True
        await n.save()
        return {"id": n.id, **n.model_dump()}

    async def mark_all_notifications_read(self, user_id: str) -> int:
        result = await Notification.find(Notification.user_id == user_id, Notification.read == False).update_many({"$set": {"read": True}})
        return result.modified_count

    async def get_unread_count(self, user_id: str) -> int:
        return await Notification.find(Notification.user_id == user_id, Notification.read == False).count()

    async def notify_agent_completion(self, agent_tag: str, message: str, user_id: str = "user-1", episode_id: Optional[str] = None) -> Dict[str, Any]:
        """Record an agent completion event as a persistent system notification."""
        notif_data = {
            "user_id": user_id,
            "type": "success",
            "title": agent_tag,
            "message": message,
            "episode_id": episode_id,
            "read": False
        }
        return await self.create_notification(notif_data)

db = BeanieDatabaseService()
