from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from app.agents.state import EpisodeStatus

class EpisodeResponse(BaseModel):
    raw_audio_url: Optional[str] = None
    transcript: Optional[str] = None
    generated_content: Optional[Dict[str, Any]] = Field(default_factory=dict)
    status: EpisodeStatus
    human_feedback: Optional[str] = None

    class Config:
        from_attributes = True
