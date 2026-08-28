from typing import Optional, Dict, Any
from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field

class AITask(Document):
    id: Optional[str] = Field(default=None)
    episode_id: Indexed(str)
    user_id: Indexed(str) = "user-1"
    task_type: str  # "transcription", "clipping", "video_processing", "copywriting"
    status: Indexed(str) = "PENDING"  # "PENDING", "PROCESSING", "COMPLETED", "FAILED"
    progress: int = 0  # 0 to 100
    result_data: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "ai_tasks"
