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

# Configure MongoDB connection dynamically from environment URL
def get_mongodb_url() -> str:
    return os.getenv("MONGODB_URL", os.getenv("MONGODB_URI", os.getenv("NONGODB_URL", os.getenv("DATABASE_URL", "")))).strip()

def get_db_name() -> str:
    url = get_mongodb_url()
    parsed = urlparse(url)
    if parsed.path and parsed.path != "/":
        return parsed.path.lstrip("/")
    return "podule"

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
        self._in_memory_users = self._load_users_from_file()
        self._in_memory_episodes = self._load_episodes_from_file()
        self._in_memory_settings = self._load_settings_from_file()
        self._in_memory_api_keys = self._load_api_keys_from_file()
        self._in_memory_approvals = []
        self._in_memory_agents = [
            {"name": "Research Agent", "role": "Research & Intelligence", "status": "idle", "task": "Idle", "tasksToday": 14, "success": 98},
            {"name": "Booking Agent", "role": "Guest Outreach", "status": "idle", "task": "Idle", "tasksToday": 8, "success": 95},
            {"name": "Production Agent", "role": "Audio & Video Editing", "status": "idle", "task": "Idle", "tasksToday": 22, "success": 100},
            {"name": "Repurposing Agent", "role": "Social Clips Generation", "status": "idle", "task": "Idle", "tasksToday": 35, "success": 97},
            {"name": "Distribution Agent", "role": "Multi-Platform Syndication", "status": "idle", "task": "Idle", "tasksToday": 12, "success": 100}
        ]
        self._in_memory_notifs = []

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

    def get_static_file_path(self, filename: str) -> Path:
        if os.getenv("VERCEL"):
            return Path("/tmp") / filename
        return Path("static") / filename

    def _save_users_to_file(self):
        try:
            import json
            file_path = self.get_static_file_path("users_data.json")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._in_memory_users, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving users file: {e}")

    def _load_episodes_from_file(self) -> List[Dict[str, Any]]:
        file_path = self.get_static_file_path("episodes_data.json")
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
            file_path = self.get_static_file_path("episodes_data.json")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._in_memory_episodes, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving episodes file: {e}")

    def _load_settings_from_file(self) -> Dict[str, Any]:
        file_path = self.get_static_file_path("settings_data.json")
        if file_path.exists():
            try:
                import json
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                print(f"Error loading settings file: {e}")
        return {
            "workspaceName": "PodBin Studio",
            "showName": "The Lovable Frontier",
            "primaryHost": "Jordan Lee",
            "releaseCadence": "Weekly",
            "integrations": [],
            "autonomyLevel": "Human-in-the-loop",
            "operational_tier": "FREE",
            "orchestrator_model": "Podule Copilot (Free)"
        }

    def _save_settings_to_file(self):
        try:
            import json
            file_path = self.get_static_file_path("settings_data.json")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._in_memory_settings, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving settings file: {e}")

    def _load_api_keys_from_file(self) -> Dict[str, str]:
        file_path = self.get_static_file_path("api_keys_data.json")
        if file_path.exists():
            try:
                import json
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                print(f"Error loading api_keys file: {e}")
        return {"deepgram": "", "openai": "", "elevenlabs": ""}

    def _save_api_keys_to_file(self):
        try:
            import json
            file_path = self.get_static_file_path("api_keys_data.json")
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self._in_memory_api_keys, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving api_keys file: {e}")

    @property
    def is_configured(self) -> bool:
        url = get_mongodb_url()
        if not url:
            return False
        # On Vercel cloud serverless, localhost / 127.0.0.1 MongoDB URLs are unreachable and must be disabled
        if os.getenv("VERCEL") and ("localhost" in url or "127.0.0.1" in url):
            return False
        return bool(url.startswith("mongodb://") or url.startswith("mongodb+srv://"))

    @property
    def is_db_ready(self) -> bool:
        return bool(self.is_configured and getattr(self, "_beanie_initialized", False))

    async def ensure_db_initialized(self):
        if self.is_configured and not getattr(self, "_beanie_initialized", False):
            try:
                import asyncio
                await asyncio.wait_for(self.init_db(), timeout=10.0)
            except Exception as e:
                self._last_error = f"ensure_db_initialized error: {type(e).__name__} - {str(e)}"
                print(f"[DB ERROR] Lazy init_db failure or timeout: {e}")

    async def init_db(self):
        self._init_step = "Starting init_db"
        if not self.is_configured:
            self._init_step = "not_configured"
            print("[CRITICAL DB WARNING] MONGODB_URI/MONGODB_URL is not set or points to unreachable localhost on Vercel! Operating in fallback mode.")
            return

        url = get_mongodb_url()
        target_db = get_db_name()
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname or "unknown-host"
        self._init_step = f"attempting_connect_{hostname}"
        print(f"[MONGODB ATTEMPTING CONNECT] Host: {hostname} | Database: {target_db}")
        
        if not getattr(self, "_beanie_initialized", False):
            try:
                if self.client is None:
                    self.client = AsyncIOMotorClient(
                        url,
                        serverSelectionTimeoutMS=10000,
                        connectTimeoutMS=10000
                    )
                self._init_step = "calling_init_beanie"
                await init_beanie(
                    database=self.client.get_database(target_db),
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
                self._beanie_initialized = True
                self._last_error = None
                self._init_step = "beanie_initialized_success"
                print(f"[MONGODB CONNECTED SUCCESS] Successfully initialized Beanie models for DB '{target_db}' on Host '{hostname}'")
            except Exception as e:
                self._last_error = f"{type(e).__name__}: {str(e)}"
                self._init_step = f"init_beanie_failed_{type(e).__name__}"
                print(f"[MONGODB ERROR] init_beanie failed for DB '{target_db}' on Host '{hostname}': {e}")
                self.client = None
                self._beanie_initialized = False
                return
        
        # Seed default admin users ONLY if the MongoDB User collection is completely empty
        try:
            user_count = await User.count()
            if user_count == 0:
                print("[DB] User collection is empty. Seeding initial admin users into MongoDB...")
                for u in self._in_memory_users:
                    u_email = u.get("email", "").strip().lower()
                    if u_email:
                        existing = await User.find_one(User.email == u_email)
                        if not existing:
                            db_user = User(
                                id=u.get("id") or f"user-1",
                                name=u.get("name", ""),
                                email=u_email,
                                role=u.get("role", "Team Member"),
                                password=u.get("password", ""),
                                podcast_ids=u.get("podcast_ids", ["podcast-1"]),
                                suspended=u.get("suspended", False),
                                is_verified=u.get("is_verified", True)
                            )
                            await db_user.insert()
        except Exception as e:
            print(f"[DB] User seed check notice: {e}")

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
        await self.ensure_db_initialized()
        if self.is_db_ready:
            try:
                episodes = await Episode.find_all().to_list()
                mongo_episodes = []
                for ep in episodes:
                    ep_dict = ep.model_dump()
                    ep_dict["id"] = ep.id
                    self._ensure_defaults(ep_dict)
                    mongo_episodes.append(ep_dict)
                return mongo_episodes
            except Exception as e:
                print(f"[DB ERROR] MongoDB get_episodes failure: {e}")
        return self._in_memory_episodes

    async def get_episode(self, episode_id: str) -> Optional[Dict[str, Any]]:
        episodes = await self.get_episodes()
        for ep in episodes:
            if ep.get("id") == episode_id:
                return ep
        return None

    async def add_episode(self, episode: Dict[str, Any]) -> Dict[str, Any]:
        await self.ensure_db_initialized()
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
        
        if self.is_db_ready:
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

        if self.is_db_ready:
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

        if self.is_db_ready:
            try:
                ep = await Episode.get(episode_id)
                if ep:
                    await ep.delete()
            except Exception:
                pass
        return True

    # Approvals operations
    async def get_approvals(self) -> List[Dict[str, Any]]:
        await self.ensure_db_initialized()
        mongo_approvals = []
        if self.is_db_ready:
            try:
                approvals = await Approval.find(Approval.status == "PENDING").to_list()
                mongo_approvals = [{"id": appr.id, **appr.model_dump()} for appr in approvals]
            except Exception:
                pass
        
        combined = list(mongo_approvals)
        mongo_ids = {a["id"] for a in mongo_approvals if "id" in a}
        for a in self._in_memory_approvals:
            if a.get("id") not in mongo_ids:
                combined.append(a)
        return combined

    async def action_approval(self, approval_id: str, action: str, updated_content: str = None) -> Optional[Dict[str, Any]]:
        await self.ensure_db_initialized()
        if not self.is_db_ready:
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
        await self.ensure_db_initialized()
        self._in_memory_approvals.append(appr_dict)
        if self.is_db_ready:
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
            except Exception as e:
                print(f"MongoDB add_approval notice: {e}")
        return appr_dict

    # Agents operations
    async def get_agents(self) -> List[Dict[str, Any]]:
        if not self.is_db_ready:
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
        await self.ensure_db_initialized()
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
        if not self.is_db_ready:
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
        await self.ensure_db_initialized()
        self._in_memory_settings.update(updates)
        self._save_settings_to_file()
        if not self.is_db_ready:
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
        await self.ensure_db_initialized()
        if self.is_db_ready:
            try:
                users = await User.find_all().to_list()
                mongo_users = []
                for u in users:
                    u_dict = u.model_dump()
                    u_dict["id"] = u.id or u_dict.get("id")
                    mongo_users.append(u_dict)
                self._in_memory_users = mongo_users
                self._save_users_to_file()
                return mongo_users
            except Exception as e:
                print(f"[DB ERROR] MongoDB get_users failure: {e}")
        return self._in_memory_users

    async def update_user_role(self, user_id: str, role: str) -> Optional[Dict[str, Any]]:
        return await self.update_user(user_id, {"role": role})

    async def suspend_user(self, user_id: str, suspended: bool) -> Optional[Dict[str, Any]]:
        return await self.update_user(user_id, {"suspended": suspended})

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        await self.ensure_db_initialized()
        clean_email = user_data.get("email", "").strip().lower()
        
        if self.is_db_ready:
            try:
                existing = await User.find_one(User.email == clean_email)
                if existing:
                    u_dict = existing.model_dump()
                    u_dict["id"] = existing.id or u_dict.get("id")
                    return u_dict
            except Exception as e:
                print(f"[DB] find_one existing user notice: {e}")

        import secrets
        new_id = user_data.get("id") or f"user-{secrets.token_hex(6)}"
        new_u = {
            "id": new_id,
            "name": user_data.get("name", ""),
            "email": clean_email,
            "role": user_data.get("role", "Team Member"),
            "password": user_data.get("password", ""),
            "podcast_ids": user_data.get("podcast_ids", ["podcast-1"]),
            "suspended": False,
            "is_verified": True
        }

        if self.is_db_ready:
            try:
                new_user = User(
                    id=new_id,
                    name=user_data.get("name", ""),
                    email=clean_email,
                    role=user_data.get("role", "Team Member"),
                    password=user_data.get("password", ""),
                    podcast_ids=user_data.get("podcast_ids", ["podcast-1"]),
                    suspended=False,
                    is_verified=True
                )
                await new_user.insert()
                print(f"[DB ATLAS SUCCESS] Created user {clean_email} (ID: {new_id}) in MongoDB Atlas!")
                u_dict = new_user.model_dump()
                u_dict["id"] = new_id
                return u_dict
            except Exception as e:
                print(f"[DB ATLAS ERROR] MongoDB create_user failure: {e}")
                if self.is_configured:
                    raise RuntimeError(f"Failed to persist user to MongoDB Atlas: {e}")

        # Maintain in-memory and disk backup fallback if DB not configured
        self._in_memory_users = [u for u in self._in_memory_users if u.get("id") != new_id and u.get("email", "").strip().lower() != clean_email]
        self._in_memory_users.append(new_u)
        self._save_users_to_file()
        return new_u

    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        await self.ensure_db_initialized()
        clean_target = user_id.strip().lower()
        target_user = None
        for u in self._in_memory_users:
            if u.get("id") == user_id or u.get("email", "").strip().lower() == clean_target:
                u.update(updates)
                target_user = u
                break
        self._save_users_to_file()

        if self.is_db_ready:
            try:
                user = await User.get(user_id)
                if not user:
                    user = await User.find_one(User.email == clean_target)
                if user:
                    for k, v in updates.items():
                        if hasattr(user, k):
                            setattr(user, k, v)
                    await user.save()
                    return {"id": user.id, **user.model_dump()}
            except Exception as e:
                print(f"MongoDB update_user notice: {e}")
        return target_user

    async def delete_user(self, user_id: str) -> bool:
        await self.ensure_db_initialized()
        clean_target = user_id.strip().lower()
        deleted = False
        
        # Remove from in-memory / disk user store
        new_users = [
            u for u in self._in_memory_users 
            if u.get("id") != user_id and u.get("email", "").strip().lower() != clean_target
        ]
        if len(new_users) != len(self._in_memory_users):
            self._in_memory_users = new_users
            self._save_users_to_file()
            deleted = True

        # Remove from MongoDB if configured
        if self.is_db_ready:
            try:
                user = await User.get(user_id)
                if not user:
                    user = await User.find_one(User.email == clean_target)
                if user:
                    await user.delete()
                    deleted = True
            except Exception as e:
                print(f"MongoDB delete_user notice: {e}")
                
        return deleted

    async def invite_user(self, name: str, email: str, role: str) -> Dict[str, Any]:
        users = await self.get_users()
        for u in users:
            if u.get("email") == email:
                return u
        from app.core.security import hash_password
        return await self.create_user({"name": name, "email": email, "role": role, "password": hash_password("password123")})

    # API Keys Operations
    async def get_api_keys(self) -> Dict[str, str]:
        await self.ensure_db_initialized()
        
        keys = {
            "openai": self._in_memory_api_keys.get("openai", ""),
            "deepgram": self._in_memory_api_keys.get("deepgram", ""),
            "elevenlabs": self._in_memory_api_keys.get("elevenlabs", "")
        }

        def is_real_key(val: Optional[str]) -> bool:
            if not val: return False
            val_str = str(val).strip()
            return not ("..." in val_str or "[masked]" in val_str or val_str.startswith(("sk-...", "dg-...", "el-...")))

        # Query MongoDB document if database is configured
        if self.is_db_ready:
            try:
                doc = await APIKeysDocument.get("1")
                if doc:
                    if doc.openai:
                        raw = decrypt_key(doc.openai[4:]) if doc.openai.startswith("enc:") else doc.openai
                        if is_real_key(raw): keys["openai"] = raw
                    if doc.deepgram:
                        raw = decrypt_key(doc.deepgram[4:]) if doc.deepgram.startswith("enc:") else doc.deepgram
                        if is_real_key(raw): keys["deepgram"] = raw
                    if doc.elevenlabs:
                        raw = decrypt_key(doc.elevenlabs[4:]) if doc.elevenlabs.startswith("enc:") else doc.elevenlabs
                        if is_real_key(raw): keys["elevenlabs"] = raw
            except Exception as e:
                print(f"MongoDB API keys read warning: {e}")

        # Fallback to env file / os.getenv if still empty
        from app.services.env_manager import read_env_file
        try:
            env_file_data = read_env_file()
        except Exception:
            env_file_data = {}

        if not is_real_key(keys.get("openai")):
            env_val = env_file_data.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
            if is_real_key(env_val): keys["openai"] = env_val.strip()

        if not is_real_key(keys.get("deepgram")):
            env_val = env_file_data.get("DEEPGRAM_API_KEY") or os.getenv("DEEPGRAM_API_KEY", "")
            if is_real_key(env_val): keys["deepgram"] = env_val.strip()

        if not is_real_key(keys.get("elevenlabs")):
            env_val = env_file_data.get("ELEVENLABS_API_KEY") or os.getenv("ELEVENLABS_API_KEY", "")
            if is_real_key(env_val): keys["elevenlabs"] = env_val.strip()

        # Update in-memory dict and process environment variables
        self._in_memory_api_keys.update(keys)
        self._save_api_keys_to_file()

        for k, v in keys.items():
            if v and is_real_key(v):
                os.environ[f"{k.upper()}_API_KEY"] = v

        return keys

    async def update_api_keys(self, keys_dict: Dict[str, str]) -> Dict[str, str]:
        await self.ensure_db_initialized()
        
        current_keys = await self.get_api_keys()

        def is_masked_or_invalid(val: Optional[str]) -> bool:
            if not val: return True
            val_str = str(val).strip()
            return "..." in val_str or "[masked]" in val_str or val_str.startswith(("sk-...", "dg-...", "el-..."))

        resolved = {}
        for k in ["openai", "deepgram", "elevenlabs"]:
            in_val = keys_dict.get(k)
            if in_val is not None and not is_masked_or_invalid(in_val):
                clean_v = in_val.strip()
                resolved[k] = clean_v
                self._in_memory_api_keys[k] = clean_v
                os.environ[f"{k.upper()}_API_KEY"] = clean_v
            else:
                resolved[k] = current_keys.get(k, "")
                if resolved[k]:
                    self._in_memory_api_keys[k] = resolved[k]
                    os.environ[f"{k.upper()}_API_KEY"] = resolved[k]

        # Persist to disk JSON file
        self._save_api_keys_to_file()

        # Persist to MongoDB if configured
        if self.is_db_ready:
            try:
                doc = await APIKeysDocument.get("1")
                if not doc:
                    doc = APIKeysDocument(id="1", deepgram="", openai="", elevenlabs="")
                    await doc.insert()

                if resolved.get("openai"):
                    doc.openai = f"enc:{encrypt_key(resolved['openai'])}"
                if resolved.get("deepgram"):
                    doc.deepgram = f"enc:{encrypt_key(resolved['deepgram'])}"
                if resolved.get("elevenlabs"):
                    doc.elevenlabs = f"enc:{encrypt_key(resolved['elevenlabs'])}"

                await doc.save()
            except Exception as e:
                print(f"MongoDB API keys write warning: {e}")

        # Also persist to .env file if available
        try:
            from app.services.env_manager import update_env_file
            env_updates = {}
            if resolved.get("openai"): env_updates["OPENAI_API_KEY"] = resolved["openai"]
            if resolved.get("deepgram"): env_updates["DEEPGRAM_API_KEY"] = resolved["deepgram"]
            if resolved.get("elevenlabs"): env_updates["ELEVENLABS_API_KEY"] = resolved["elevenlabs"]
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
