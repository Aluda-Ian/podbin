from typing import Optional, Dict, Any
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field

class SocialConnection(Document):
    id: str = Field(default_factory=lambda: f"soc-conn-{datetime.utcnow().timestamp()}")
    user_id: Indexed(str) = "user-1"
    platform: Indexed(str)  # "youtube", "linkedin", "twitter", "tiktok", "instagram", "facebook"
    access_token: str  # Encrypted token string
    refresh_token: Optional[str] = None  # Encrypted refresh token string
    token_expiry: Optional[datetime] = None
    account_id: Optional[str] = None
    account_name: Optional[str] = "Social Account"
    avatar_url: Optional[str] = None
    status: str = "active"  # "active", "expired", "disconnected"
    auto_posting_enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "social_connections"

    def is_token_expired(self) -> bool:
        if not self.token_expiry:
            return False
        return datetime.utcnow() >= self.token_expiry
