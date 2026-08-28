from typing import Optional, List, Dict, Any
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field

class SocialPost(Document):
    id: str = Field(default_factory=lambda: f"post-{datetime.utcnow().timestamp()}")
    episode_id: Optional[str] = None
    user_id: Indexed(str) = "user-1"
    platforms: List[str] = Field(default_factory=list)  # ["youtube", "linkedin", "twitter", "tiktok"]
    content: str = ""  # General text caption
    platform_captions: Dict[str, str] = Field(default_factory=dict)  # {"twitter": "...", "linkedin": "..."}
    media_urls: List[str] = Field(default_factory=list)
    scheduled_time: datetime = Field(default_factory=datetime.utcnow)
    status: Indexed(str) = "PENDING_APPROVAL"  # "DRAFT", "PENDING_APPROVAL", "SCHEDULED", "PUBLISHED", "FAILED"
    published_urls: Dict[str, str] = Field(default_factory=dict)  # {"youtube": "https://...", "linkedin": "..."}
    error_log: Optional[str] = None
    analytics_data: Dict[str, Any] = Field(default_factory=lambda: {
        "impressions": 0,
        "likes": 0,
        "shares": 0,
        "comments": 0,
        "clicks": 0
    })
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "social_posts"
