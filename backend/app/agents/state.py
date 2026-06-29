from enum import Enum
from typing import Dict, Any, Optional, List
from typing_extensions import TypedDict

class EpisodeStatus(str, Enum):
    RESEARCH = "RESEARCH"
    BOOKING = "BOOKING"
    EDITING = "EDITING"
    MASTERING = "MASTERING"
    DISTRO = "DISTRO"
    LIVE = "LIVE"
    DRAFT = "DRAFT"
    PENDING_REVIEW = "PENDING_REVIEW"
    SCHEDULED = "SCHEDULED"
    PUBLISHED = "PUBLISHED"

class EpisodeState(TypedDict):
    raw_audio_url: Optional[str]
    transcript: Optional[str]
    generated_content: Optional[Dict[str, Any]]  # containing titles, notes, social snippets
    status: EpisodeStatus
    human_feedback: Optional[str]
    word_timeline: Optional[List[Dict[str, Any]]]
    edit_decision_list: Optional[List[Dict[str, Any]]]
    selected_llm_config: Optional[Dict[str, Any]]
