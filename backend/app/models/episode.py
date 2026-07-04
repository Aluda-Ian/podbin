from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from app.agents.state import EpisodeStatus
from beanie import Document


class Clip(BaseModel):
    id: str
    title: str
    text: str
    startTime: str
    endTime: str
    platform: str
    status: str

class DistributionChannel(BaseModel):
    name: str
    status: str
    url: str

class SocialsSchedule(BaseModel):
    id: str
    platform: str
    caption: str
    time: str
    status: str

class EpisodeResponse(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    guest: Optional[str] = None
    avatar: Optional[str] = None
    stage: Optional[str] = None
    duration: Optional[str] = None
    date: Optional[str] = None
    progress: Optional[int] = 0
    note: Optional[str] = None
    bars: Optional[List[int]] = None
    prediction: Optional[str] = None
    raw_audio_url: Optional[str] = None
    raw_video_url: Optional[str] = None
    media_type: Optional[str] = "audio"  # "audio" | "video"
    podcast_id: Optional[str] = "podcast-1"
    transcript: Optional[str] = None
    generated_content: Optional[Dict[str, Any]] = Field(default_factory=dict)
    status: EpisodeStatus
    human_feedback: Optional[str] = None
    clips: Optional[List[Clip]] = None
    distribution_channels: Optional[List[DistributionChannel]] = None
    socials_schedule: Optional[List[SocialsSchedule]] = None
    word_timeline: Optional[List[Dict[str, Any]]] = None
    edit_decision_list: Optional[List[Dict[str, Any]]] = None
    selected_llm_config: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        protected_namespaces = ()


class Episode(Document):
    id: str = Field(default=None)
    title: str
    guest: str
    avatar: str = "guest1"
    stage: str = "Pre-Prod"
    duration: str = "—"
    date: str
    progress: int = 0
    note: str = ""
    bars: Optional[List[int]] = None
    prediction: Optional[str] = None
    raw_audio_url: Optional[str] = None
    raw_video_url: Optional[str] = None
    media_type: str = "audio"
    podcast_id: str = "podcast-1"
    transcript: Optional[str] = None
    generated_content: Dict[str, Any] = Field(default_factory=dict)
    status: EpisodeStatus = EpisodeStatus.RESEARCH
    human_feedback: Optional[str] = None
    clips: List[Clip] = Field(default_factory=list)
    distribution_channels: List[DistributionChannel] = Field(default_factory=list)
    socials_schedule: List[SocialsSchedule] = Field(default_factory=list)
    word_timeline: List[Dict[str, Any]] = Field(default_factory=list)
    edit_decision_list: List[Dict[str, Any]] = Field(default_factory=list)
    selected_llm_config: Dict[str, Any] = Field(default_factory=dict)

    class Settings:
        name = "episodes"

