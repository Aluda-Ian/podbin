from beanie import Document, PydanticObjectId
from pydantic import Field
from typing import Optional, Union
from datetime import datetime

class Notification(Document):
    id: Optional[Union[PydanticObjectId, str]] = Field(default=None)
    user_id: str
    type: str  # "success" | "error" | "warning" | "info"
    title: str
    message: str
    read: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    episode_id: Optional[str] = None
    action_url: Optional[str] = None

    class Settings:
        name = "notifications"

