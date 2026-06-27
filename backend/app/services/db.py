import json
import os
from pathlib import Path
from typing import Dict, Any, List

# Locate the database file at the backend root directory
backend_root = Path(__file__).resolve().parents[2]
DB_FILE = backend_root / "db.json"

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
        "showName": "The Loverble Frontier",
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

class JSONDatabaseService:
    def __init__(self):
        self._load()

    def _load(self):
        if not os.path.exists(DB_FILE):
            self.data = SEED_DATA.copy()
            self._save()
        else:
            try:
                with open(DB_FILE, "r") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = SEED_DATA.copy()
                self._save()

    def _save(self):
        try:
            with open(DB_FILE, "w") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving database: {e}")

    # Episodes operations
    def get_episodes(self) -> List[Dict[str, Any]]:
        self._load()
        eps = self.data.get("episodes", [])
        for ep in eps:
            self._ensure_defaults(ep)
        return eps

    def get_episode(self, episode_id: str) -> Dict[str, Any]:
        self._load()
        for ep in self.data.get("episodes", []):
            if ep["id"] == episode_id:
                self._ensure_defaults(ep)
                return ep
        return None

    def _ensure_defaults(self, ep: Dict[str, Any]):
        if "clips" not in ep:
            if ep.get("id") == "EP-143":
                ep["clips"] = [
                    { "id": "clip-1", "title": "Deepfakes and Consent", "text": "We are essentially living inside a high-fidelity simulation of last year's consensus.", "startTime": "00:42", "endTime": "01:15", "platform": "TikTok", "status": "APPROVED" },
                    { "id": "clip-2", "title": "Regulatory Gaps", "text": "The law is always 5 years behind the deployment of these models.", "startTime": "12:10", "endTime": "13:05", "platform": "YouTube Shorts", "status": "PENDING" }
                ]
            else:
                ep["clips"] = []
        if "distribution_channels" not in ep:
            ep["distribution_channels"] = [
                { "name": "Spotify for Podcasters", "status": "LIVE" if ep.get("stage") == "Growth" else "PENDING", "url": "https://podcasters.spotify.com" },
                { "name": "Apple Podcasts Connect", "status": "LIVE" if ep.get("stage") == "Growth" else "PENDING", "url": "https://podcastsconnect.apple.com" },
                { "name": "YouTube Studio", "status": "PROCESSING" if ep.get("status") == "DISTRO" else ("LIVE" if ep.get("status") == "LIVE" else "PENDING"), "url": "https://studio.youtube.com" }
            ]
        if "socials_schedule" not in ep:
            if ep.get("id") == "EP-143":
                ep["socials_schedule"] = [
                    { "id": "sched-1", "platform": "TikTok", "caption": "Living in a simulation... Ep. 143 is live!", "time": "2026-06-27T10:00:00", "status": "SCHEDULED" }
                ]
            else:
                ep["socials_schedule"] = []
        if "podcast_id" not in ep:
            ep["podcast_id"] = "podcast-1"
        if "media_type" not in ep:
            ep["media_type"] = "audio"

    def add_episode(self, episode: Dict[str, Any]) -> Dict[str, Any]:
        self._load()
        # Generate new episode ID based on current maximum
        existing_ids = []
        for ep in self.data.get("episodes", []):
            try:
                num = int(ep["id"].split("-")[1])
                existing_ids.append(num)
            except Exception:
                pass
        next_num = max(existing_ids) + 1 if existing_ids else 1
        ep_id = f"EP-{next_num}"
        episode["id"] = ep_id
        
        self.data["episodes"].insert(0, episode)
        self._save()
        return episode

    def update_episode(self, episode_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        self._load()
        for idx, ep in enumerate(self.data.get("episodes", [])):
            if ep["id"] == episode_id:
                self.data["episodes"][idx].update(updates)
                self._save()
                return self.data["episodes"][idx]
        return None

    def delete_episode(self, episode_id: str) -> bool:
        self._load()
        initial_len = len(self.data["episodes"])
        self.data["episodes"] = [ep for ep in self.data["episodes"] if ep["id"] != episode_id]
        if len(self.data["episodes"]) < initial_len:
            self._save()
            return True
        return False

    # Approvals operations
    def get_approvals(self) -> List[Dict[str, Any]]:
        self._load()
        return [appr for appr in self.data.get("approvals", []) if appr.get("status") == "PENDING"]

    def action_approval(self, approval_id: str, action: str, updated_content: str = None) -> Dict[str, Any]:
        self._load()
        for idx, appr in enumerate(self.data.get("approvals", [])):
            if appr["id"] == approval_id:
                if action == "approve":
                    self.data["approvals"][idx]["status"] = "APPROVED"
                elif action == "reject":
                    self.data["approvals"][idx]["status"] = "REJECTED"
                elif action == "edit" and updated_content is not None:
                    self.data["approvals"][idx]["quote"] = updated_content
                
                self._save()
                return self.data["approvals"][idx]
        return None

    # Agents operations
    def get_agents(self) -> List[Dict[str, Any]]:
        self._load()
        return self.data.get("agents", [])

    def toggle_agent(self, name: str) -> Dict[str, Any]:
        self._load()
        for idx, ag in enumerate(self.data.get("agents", [])):
            if ag["name"].lower() == name.lower():
                current_status = ag.get("status", "idle")
                new_status = "idle" if current_status == "active" else "active"
                self.data["agents"][idx]["status"] = new_status
                self.data["agents"][idx]["task"] = "Idle" if new_status == "idle" else f"Resumed work on task"
                self._save()
                return self.data["agents"][idx]
        return None

    # Settings operations
    def get_settings(self) -> Dict[str, Any]:
        self._load()
        return self.data.get("settings", {})

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        self._load()
        self.data["settings"].update(updates)
        self._save()
        return self.data["settings"]

    # Users operations
    def get_users(self) -> List[Dict[str, Any]]:
        self._load()
        if "users" not in self.data:
            self.data["users"] = SEED_DATA.get("users", [])
            self._save()
        # Ensure everyone has a suspended status default to False
        modified = False
        for user in self.data["users"]:
            if "suspended" not in user:
                user["suspended"] = False
                modified = True
        if modified:
            self._save()
        return self.data["users"]

    def update_user_role(self, user_id: str, role: str) -> Dict[str, Any]:
        self._load()
        users = self.get_users()
        for u in users:
            if u["id"] == user_id:
                u["role"] = role
                self._save()
                return u
        return None

    def suspend_user(self, user_id: str, suspended: bool) -> Dict[str, Any]:
        self._load()
        users = self.get_users()
        for u in users:
            if u["id"] == user_id:
                u["suspended"] = suspended
                self._save()
                return u
        return None

    def invite_user(self, name: str, email: str, role: str) -> Dict[str, Any]:
        self._load()
        users = self.get_users()
        for u in users:
            if u["email"] == email:
                return u
        new_id = f"user-{len(users) + 1}"
        new_user = {
            "id": new_id,
            "name": name,
            "email": email,
            "role": role,
            "password": "password123",
            "podcast_ids": ["podcast-1"],
            "suspended": False
        }
        self.data["users"].append(new_user)
        self._save()
        return new_user

    # API Keys Operations
    def get_api_keys(self) -> Dict[str, str]:
        self._load()
        if "api_keys" not in self.data:
            self.data["api_keys"] = {
                "deepgram": "",
                "openai": "",
                "elevenlabs": ""
            }
            self._save()
        return self.data["api_keys"]

    def update_api_keys(self, keys: Dict[str, str]) -> Dict[str, str]:
        self._load()
        if "api_keys" not in self.data:
            self.data["api_keys"] = {}
        self.data["api_keys"].update(keys)
        self._save()
        return self.data["api_keys"]

    # Admin Analytics
    def get_admin_analytics(self) -> Dict[str, Any]:
        self._load()
        episodes = self.get_episodes()
        total_episodes = len(episodes)
        total_costs = round(total_episodes * 5.35 + 12.80, 2)
        return {
            "total_episodes": total_episodes,
            "system_error_rate": "1.2%",
            "total_api_costs": f"${total_costs}",
            "cost_history": [6, 9, 4, 11, 7, 13, 10, 14, 9, 12, 16, 11, 18, 15]
        }

db = JSONDatabaseService()
