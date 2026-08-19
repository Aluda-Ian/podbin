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
    deepgram: Optional[str] = ""
    openai: Optional[str] = ""
    elevenlabs: Optional[str] = ""

    class Settings:
        name = "api_keys"





class BeanieDatabaseService:
    def __init__(self):
        self.client = None
        from app.core.security import hash_password
        self._in_memory_users = self._load_users_from_file()
        self._in_memory_episodes = self._load_episodes_from_file()
        self._in_memory_approvals = []

    def _load_users_from_file(self) -> List[Dict[str, Any]]:
        file_path = Path("static") / "users_data.json"
        if file_path.exists():
            try:
                import json
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception as e:
                print(f"Error loading users file: {e}")
        from app.core.security import hash_password
        default_users = [
            {
                "id": "user-1",
                "name": "Ian Aluda",
                "email": "info@vendatechnologies.com",
                "role": "Super Admin",
                "password": hash_password("@Munangwe212"),
                "podcast_ids": ["*"],
                "suspended": False,
                "is_verified": True
            },
            {
                "id": "user-2",
                "name": "Demo Admin",
                "email": "admin@podbin.com",
                "role": "Admin",
                "password": hash_password("admin123"),
                "podcast_ids": ["*"],
                "suspended": False,
                "is_verified": True
            },
            {
                "id": "user-3",
                "name": "Sarah Chen",
                "email": "owner@podbin.com",
                "role": "Podcast Owner",
                "password": hash_password("owner123"),
                "podcast_ids": ["podcast-1"],
                "suspended": False,
                "is_verified": True
            }
        ]
        return default_users

    def _save_users_to_file(self):
        try:
            import json
            file_path = Path("static") / "users_data.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._in_memory_users, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving users file: {e}")
        self._in_memory_approvals = []

    def _load_episodes_from_file(self) -> List[Dict[str, Any]]:
        file_path = Path("static") / "episodes_data.json"
        if file_path.exists():
            try:
                import json
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception as e:
                print(f"Error loading episodes file: {e}")
        return []

    def _save_episodes_to_file(self):
        try:
            import json
            file_path = Path("static") / "episodes_data.json"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._in_memory_episodes, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving episodes file: {e}")
        self._in_memory_agents = [
            {"name": "Research Agent", "role": "Research & Intelligence", "status": "idle", "task": "Idle", "tasksToday": 14, "success": 98},
            {"name": "Booking Agent", "role": "Guest Outreach", "status": "idle", "task": "Idle", "tasksToday": 8, "success": 95},
            {"name": "Production Agent", "role": "Audio & Video Editing", "status": "idle", "task": "Idle", "tasksToday": 22, "success": 100},
            {"name": "Repurposing Agent", "role": "Social Clips Generation", "status": "idle", "task": "Idle", "tasksToday": 35, "success": 97},
            {"name": "Distribution Agent", "role": "Multi-Platform Syndication", "status": "idle", "task": "Idle", "tasksToday": 12, "success": 100}
        ]
        self._in_memory_settings = {
            "workspaceName": "PodBin Studio",
            "showName": "The Lovable Frontier",
            "primaryHost": "Jordan Lee",
            "releaseCadence": "Weekly",
            "integrations": [],
            "autonomyLevel": "Human-in-the-loop",
            "operational_tier": "FREE",
            "orchestrator_model": "Podule Copilot (Free)"
        }
        self._in_memory_api_keys = {"deepgram": "", "openai": "", "elevenlabs": ""}
        self._in_memory_notifs = []

    @property
    def is_configured(self) -> bool:
        return bool(MONGODB_URL and MONGODB_URL.startswith("mongodb"))

    async def init_db(self):
        if not self.is_configured:
            return
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
        
        # Seed default users
        try:
            from app.core.security import hash_password
            admin_user = await User.find_one(User.email == "info@vendatechnologies.com")
            if not admin_user:
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

            owner_user = await User.find_one(User.email == "owner@podbin.com")
            if not owner_user:
                all_users = await User.find_all().to_list()
                new_owner = User(
                    id=f"user-{len(all_users) + 1}",
                    name="Sarah Chen",
                    email="owner@podbin.com",
                    role="Podcast Owner",
                    password=hash_password("owner123"),
                    podcast_ids=["podcast-1"],
                    suspended=False,
                    is_verified=True
                )
                await new_owner.insert()
        except Exception as e:
            print(f"User seeding notice: {e}")

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
        if not self.is_configured or self.client is None:
            return self._in_memory_episodes
        try:
            episodes = await Episode.find_all().to_list()
            out = []
            for ep in episodes:
                ep_dict = ep.model_dump()
                ep_dict["id"] = ep.id
                self._ensure_defaults(ep_dict)
                out.append(ep_dict)
            return out
        except Exception:
            return self._in_memory_episodes

    async def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        episodes = await self.get_episodes()
        for ep in episodes:
            if ep.get("id") == episode_id:
                return ep
        return None

    async def add_episode(self, episode: Dict[str, Any]) -> Dict[str, Any]:
        if not episode.get("id"):
            episode["id"] = f"EP-{len(self._in_memory_episodes) + 1}"
        self._ensure_defaults(episode)
        
        # Always maintain in-memory list and write to disk file
        existing_idx = next((i for i, ep in enumerate(self._in_memory_episodes) if ep.get("id") == episode["id"]), None)
        if existing_idx is not None:
            self._in_memory_episodes[existing_idx] = episode
        else:
            self._in_memory_episodes.append(episode)
        self._save_episodes_to_file()
        
        if self.is_configured and self.client is not None:
            try:
                db_ep = Episode(**episode)
                await db_ep.insert()
            except Exception:
                pass
        return episode

    async def update_episode(self, episode_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        target_ep = None
        for ep in self._in_memory_episodes:
            if ep.get("id") == episode_id:
                ep.update(updates)
                target_ep = ep
                break
        self._save_episodes_to_file()

        if self.is_configured and self.client is not None:
            try:
                ep = await Episode.get(episode_id)
                if ep:
                    for k, v in updates.items():
                        if hasattr(ep, k):
                            setattr(ep, k, v)
                    await ep.save()
                    ep_dict = ep.model_dump()
                    ep_dict["id"] = ep.id
                    self._ensure_defaults(ep_dict)
                    return ep_dict
            except Exception:
                pass
        return target_ep

    async def delete_episode(self, episode_id: str) -> bool:
        self._in_memory_episodes = [ep for ep in self._in_memory_episodes if ep.get("id") != episode_id]
        self._save_episodes_to_file()

        if self.is_configured and self.client is not None:
            try:
                ep = await Episode.get(episode_id)
                if ep:
                    await ep.delete()
            except Exception:
                pass
        return True

    # Approvals operations
    async def get_approvals(self) -> List[Dict[str, Any]]:
        if not self.is_configured or self.client is None:
            return self._in_memory_approvals
        try:
            approvals = await Approval.find(Approval.status == "PENDING").to_list()
            return [{"id": appr.id, **appr.model_dump()} for appr in approvals]
        except Exception:
            return self._in_memory_approvals

    async def action_approval(self, approval_id: str, action: str, updated_content: str = None) -> Optional[Dict[str, Any]]:
        if not self.is_configured or self.client is None:
            for a in self._in_memory_approvals:
                if a.get("id") == approval_id:
                    if action == "approve":
                        a["status"] = "APPROVED"
                    elif action == "reject":
                        a["status"] = "REJECTED"
                    elif action == "edit" and updated_content is not None:
                        a["quote"] = updated_content
                    return a
            return None
        try:
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
        except Exception:
            return None

    async def add_approval(self, appr_dict: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured or self.client is None:
            self._in_memory_approvals.append(appr_dict)
            return appr_dict
        try:
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
        except Exception:
            self._in_memory_approvals.append(appr_dict)
            return appr_dict

    # Agents operations
    async def get_agents(self) -> List[Dict[str, Any]]:
        if not self.is_configured or self.client is None:
            return self._in_memory_agents
        try:
            agents = await Agent.find_all().to_list()
            if not agents:
                return self._in_memory_agents
            return [{
                "name": ag.id,
                "role": ag.role,
                "status": ag.status,
                "task": ag.task,
                "tasksToday": ag.tasksToday,
                "success": ag.success
            } for ag in agents]
        except Exception:
            return self._in_memory_agents

    async def toggle_agent(self, name: str) -> Optional[Dict[str, Any]]:
        for ag in self._in_memory_agents:
            if ag["name"].lower() == name.lower():
                current_status = ag.get("status", "idle")
                new_status = "idle" if current_status == "active" else "active"
                ag["status"] = new_status
                ag["task"] = "Idle" if new_status == "idle" else "Resumed work on task"
                return ag
        return None

    # Settings operations
    async def get_settings(self) -> Dict[str, Any]:
        smtp_data = {
            "host": "mail.vendatechnologies.com",
            "port": 465,
            "username": "smtp@vendatechnologies.com",
            "password": "@Munangwe212",
            "from_email": "smtp@vendatechnologies.com",
            "status": "Active & Operational (Port 465 SSL)"
        }
        res = dict(self._in_memory_settings)
        res["smtp"] = smtp_data
        if not self.is_configured or self.client is None:
            return res
        try:
            s = await SettingsDocument.get("1")
            if not s:
                return res
            data = s.model_dump(exclude={"id"})
            data["smtp"] = smtp_data
            return data
        except Exception:
            return res

    async def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        self._in_memory_settings.update(updates)
        if not self.is_configured or self.client is None:
            return self._in_memory_settings
        try:
            s = await SettingsDocument.get("1")
            if not s:
                s = SettingsDocument(
                    id="1", workspaceName="PodBin Studio", showName="The Lovable Frontier",
                    primaryHost="Jordan Lee", releaseCadence="Weekly", integrations=[],
                    autonomyLevel="Human-in-the-loop"
                )
                await s.insert()
            for k, v in updates.items():
                if hasattr(s, k):
                    setattr(s, k, v)
            await s.save()
            return s.model_dump(exclude={"id"})
        except Exception:
            return self._in_memory_settings

    # Users operations
    async def get_users(self) -> List[Dict[str, Any]]:
        if not self.is_configured or self.client is None:
            return self._in_memory_users
        try:
            users = await User.find_all().to_list()
            if not users:
                return self._in_memory_users
            return [{"id": u.id, **u.model_dump()} for u in users]
        except Exception:
            return self._in_memory_users

    async def update_user_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        for u in self._in_memory_users:
            if u.get("id") == user_id:
                u["role"] = role
                self._save_users_to_file()
                return u
        return None

    async def suspend_user(self, user_id: str, suspended: bool) -> Optional[Dict[str, Any]]:
        for u in self._in_memory_users:
            if u.get("id") == user_id:
                u["suspended"] = suspended
                self._save_users_to_file()
                return u
        return None

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        new_id = f"user-{len(self._in_memory_users) + 1}"
        new_u = {
            "id": new_id,
            "name": user_data.get("name", ""),
            "email": user_data.get("email", ""),
            "role": user_data.get("role", "Team Member"),
            "password": user_data.get("password", ""),
            "podcast_ids": user_data.get("podcast_ids", ["podcast-1"]),
            "suspended": False,
            "is_verified": True
        }
        self._in_memory_users.append(new_u)
        self._save_users_to_file()
        
        if self.is_configured and self.client is not None:
            try:
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
            except Exception:
                pass
        return new_u

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        target_user = None
        for u in self._in_memory_users:
            if u.get("id") == user_id or u.get("email") == user_id:
                u.update(updates)
                target_user = u
                break
        self._save_users_to_file()

        if self.is_configured and self.client is not None:
            try:
                user = await User.get(user_id)
                if user:
                    for k, v in updates.items():
                        if hasattr(user, k):
                            setattr(user, k, v)
                    await user.save()
                    return {"id": user.id, **user.model_dump()}
            except Exception:
                pass
        return target_user

    async def invite_user(self, name: str, email: str, role: str) -> Dict[str, Any]:
        users = await self.get_users()
        for u in users:
            if u.get("email") == email:
                return u
        from app.core.security import hash_password
        return await self.create_user({"name": name, "email": email, "role": role, "password": hash_password("password123")})

    # API Keys Operations
    async def get_api_keys(self) -> Dict[str, str]:
        keys = {
            "openai": self._in_memory_api_keys.get("openai", ""),
            "deepgram": self._in_memory_api_keys.get("deepgram", ""),
            "elevenlabs": self._in_memory_api_keys.get("elevenlabs", "")
        }

        # Query MongoDB document if database is configured
        if self.is_configured and self.client is not None:
            try:
                doc = await APIKeysDocument.get("1")
                if doc:
                    if doc.openai:
                        raw = decrypt_key(doc.openai[4:]) if doc.openai.startswith("enc:") else doc.openai
                        if raw: keys["openai"] = raw
                    if doc.deepgram:
                        raw = decrypt_key(doc.deepgram[4:]) if doc.deepgram.startswith("enc:") else doc.deepgram
                        if raw: keys["deepgram"] = raw
                    if doc.elevenlabs:
                        raw = decrypt_key(doc.elevenlabs[4:]) if doc.elevenlabs.startswith("enc:") else doc.elevenlabs
                        if raw: keys["elevenlabs"] = raw
            except Exception as e:
                print(f"MongoDB API keys read warning: {e}")

        # Fallback to env file / os.getenv if still empty
        from app.services.env_manager import read_env_file
        try:
            env_file_data = read_env_file()
        except Exception:
            env_file_data = {}

        if not keys.get("openai"):
            keys["openai"] = env_file_data.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        if not keys.get("deepgram"):
            keys["deepgram"] = env_file_data.get("DEEPGRAM_API_KEY") or os.getenv("DEEPGRAM_API_KEY", "")
        if not keys.get("elevenlabs"):
            keys["elevenlabs"] = env_file_data.get("ELEVENLABS_API_KEY") or os.getenv("ELEVENLABS_API_KEY", "")

        # Update in-memory dict and process environment variables
        self._in_memory_api_keys.update(keys)
        for k, v in keys.items():
            if v:
                os.environ[f"{k.upper()}_API_KEY"] = v

        return keys

    async def update_api_keys(self, keys_dict: Dict[str, str]) -> Dict[str, str]:
        # Clean and update in-memory cache & os.environ
        for k in ["openai", "deepgram", "elevenlabs"]:
            if k in keys_dict and keys_dict[k] is not None:
                val = keys_dict[k].strip()
                # Exclude masked placeholders from overriding valid stored keys
                if val and not ("..." in val or "[masked]" in val or val.startswith(("sk-...", "dg-...", "el-..."))):
                    self._in_memory_api_keys[k] = val
                    os.environ[f"{k.upper()}_API_KEY"] = val

        # Persist to MongoDB if configured
        if self.is_configured and self.client is not None:
            try:
                doc = await APIKeysDocument.get("1")
                if not doc:
                    doc = APIKeysDocument(id="1", deepgram="", openai="", elevenlabs="")
                    await doc.insert()

                current = dict(self._in_memory_api_keys)
                
                openai_val = keys_dict.get("openai") or current.get("openai", "")
                deepgram_val = keys_dict.get("deepgram") or current.get("deepgram", "")
                elevenlabs_val = keys_dict.get("elevenlabs") or current.get("elevenlabs", "")

                if openai_val and not ("..." in openai_val or "[masked]" in openai_val):
                    doc.openai = f"enc:{encrypt_key(openai_val)}"
                if deepgram_val and not ("..." in deepgram_val or "[masked]" in deepgram_val):
                    doc.deepgram = f"enc:{encrypt_key(deepgram_val)}"
                if elevenlabs_val and not ("..." in elevenlabs_val or "[masked]" in elevenlabs_val):
                    doc.elevenlabs = f"enc:{encrypt_key(elevenlabs_val)}"

                await doc.save()
            except Exception as e:
                print(f"MongoDB API keys write warning: {e}")

        # Also persist to .env file if available
        try:
            from app.services.env_manager import update_env_file
            env_updates = {}
            if self._in_memory_api_keys.get("openai"): env_updates["OPENAI_API_KEY"] = self._in_memory_api_keys["openai"]
            if self._in_memory_api_keys.get("deepgram"): env_updates["DEEPGRAM_API_KEY"] = self._in_memory_api_keys["deepgram"]
            if self._in_memory_api_keys.get("elevenlabs"): env_updates["ELEVENLABS_API_KEY"] = self._in_memory_api_keys["elevenlabs"]
            if env_updates:
                update_env_file(env_updates)
        except Exception as e:
            print(f"Env file API keys write warning: {e}")

        return await self.get_api_keys()


    # Admin Analytics
    async def get_admin_analytics(self) -> Dict[str, Any]:
        episodes = await self.get_episodes()
        users = await self.get_users()
        return {
            "total_episodes": len(episodes),
            "total_users": len(users),
            "total_api_costs": None,
            "cost_history": []
        }

    # Notifications operations
    async def get_notifications(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        return self._in_memory_notifs[:limit]

    async def create_notification(self, notif: Dict[str, Any]) -> Dict[str, Any]:
        notif["id"] = f"notif-{len(self._in_memory_notifs) + 1}"
        self._in_memory_notifs.insert(0, notif)
        return notif

    async def mark_notification_read(self, notif_id: str) -> Optional[Dict[str, Any]]:
        for n in self._in_memory_notifs:
            if n.get("id") == notif_id:
                n["read"] = True
                return n
        return None

    async def mark_all_notifications_read(self, user_id: str) -> int:
        count = 0
        for n in self._in_memory_notifs:
            if n.get("user_id") == user_id and not n.get("read"):
                n["read"] = True
                count += 1
        return count

    async def get_unread_count(self, user_id: str) -> int:
        return sum(1 for n in self._in_memory_notifs if n.get("user_id") == user_id and not n.get("read"))

    async def notify_agent_completion(self, agent_tag: str, message: str, user_id: str = "user-1", episode_id: Optional[str] = None) -> Dict[str, Any]:
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
