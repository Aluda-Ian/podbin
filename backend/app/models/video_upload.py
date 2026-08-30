"""
video_upload.py — VideoUpload Beanie Document
==============================================
Stores metadata about every video a user uploads.
The actual binary lives in the filesystem or MongoDB GridFS;
this document holds the pointer + ownership info.

Atlas collection: video_uploads
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import BaseModel, Field


# ── Beanie Document (persisted to Atlas) ─────────────────────────────────────

class VideoUpload(Document):
    """
    One row per uploaded video file.

    Fields
    ------
    user_id      : ID of the User who uploaded this video (foreign key → users._id)
    user_email   : Denormalised email for fast display without a join
    filename     : Server-side unique filename (e.g. myvideo_20260830_a1b2.mp4)
    original_name: Original filename as supplied by the browser
    download_url : Public URL to stream / download the file
    storage      : Where the file lives: "gridfs" | "local" | "s3" | "vercel-blob"
    content_type : MIME type (e.g. video/mp4)
    size_bytes   : File size in bytes (0 if unknown)
    duration_secs: Video duration in seconds (None until probed)
    episode_id   : Optional link to an Episode document (FK → episodes._id)
    podcast_id   : Podcast workspace the video belongs to
    status       : "processing" | "ready" | "failed"
    uploaded_at  : UTC timestamp of the upload
    """

    user_id:       str
    user_email:    str                     = ""
    filename:      str
    original_name: str                     = ""
    download_url:  str                     = ""
    storage:       str                     = "local"   # gridfs | local | s3 | vercel-blob
    content_type:  str                     = "video/mp4"
    size_bytes:    int                     = 0
    duration_secs: Optional[float]         = None
    episode_id:    Optional[str]           = None
    podcast_id:    str                     = "podcast-1"
    status:        str                     = "ready"   # processing | ready | failed
    uploaded_at:   datetime                = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "video_uploads"             # Atlas collection name


# ── Pydantic response / request schemas ──────────────────────────────────────

class VideoUploadResponse(BaseModel):
    """Shape returned by the API."""
    id:            Optional[str]   = None
    user_id:       str
    user_email:    str             = ""
    filename:      str
    original_name: str             = ""
    download_url:  str             = ""
    storage:       str             = "local"
    content_type:  str             = "video/mp4"
    size_bytes:    int             = 0
    duration_secs: Optional[float] = None
    episode_id:    Optional[str]   = None
    podcast_id:    str             = "podcast-1"
    status:        str             = "ready"
    uploaded_at:   Optional[str]   = None

    class Config:
        from_attributes = True


class VideoUploadCreate(BaseModel):
    """Payload used by the confirm-upload endpoint."""
    user_id:       str
    user_email:    Optional[str]   = ""
    filename:      str
    original_name: Optional[str]   = ""
    download_url:  Optional[str]   = ""
    storage:       Optional[str]   = "local"
    content_type:  Optional[str]   = "video/mp4"
    size_bytes:    Optional[int]   = 0
    duration_secs: Optional[float] = None
    episode_id:    Optional[str]   = None
    podcast_id:    Optional[str]   = "podcast-1"
    status:        Optional[str]   = "ready"
