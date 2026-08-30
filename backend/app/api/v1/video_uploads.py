"""
video_uploads.py — /api/v1/video-uploads endpoints
====================================================
CRUD routes for the VideoUpload model.
Every video is tied to the authenticated user via their JWT token.

Endpoints
---------
POST   /api/v1/video-uploads/           Create a record after uploading
GET    /api/v1/video-uploads/mine       List the caller's own uploads
GET    /api/v1/video-uploads/           List all uploads (admin only)
DELETE /api/v1/video-uploads/{id}       Delete an upload (owner or admin)
"""

from fastapi import APIRouter, HTTPException, status, Header, Body
from typing import Optional, List

from app.models.video_upload import VideoUploadCreate, VideoUploadResponse
from app.services.db import db
from app.core.security import verify_token

router = APIRouter()


# ── helpers ───────────────────────────────────────────────────────────────────

async def _get_caller(authorization: Optional[str]) -> dict:
    """
    Decode the JWT and return the caller's user dict.
    Raises 401 if the token is missing or invalid.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    try:
        user = await verify_token(authorization)
        return user
    except Exception as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


def _is_admin(user: dict) -> bool:
    return user.get("role", "") in ("Super Admin", "Admin", "ADMIN")


# ── routes ────────────────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=VideoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new video upload",
)
async def create_video_upload(
    payload: VideoUploadCreate = Body(...),
    authorization: Optional[str] = Header(None),
):
    """
    Call this endpoint **after** the file has been uploaded to storage.
    The body carries the file metadata (download_url, filename, size, etc.)
    and links it to the authenticated user.

    The user_id in the payload is *overwritten* with the caller's actual id
    from the JWT to prevent impersonation.
    """
    caller = await _get_caller(authorization)
    caller_id    = caller.get("id") or caller.get("_id") or caller.get("sub", "")
    caller_email = caller.get("email", "")

    data = payload.model_dump()
    data["user_id"]    = caller_id       # enforce ownership from JWT
    data["user_email"] = caller_email

    saved = await db.create_video_upload(data)
    return VideoUploadResponse(**saved)


@router.get(
    "/mine",
    response_model=List[VideoUploadResponse],
    summary="List the caller's video uploads",
)
async def list_my_video_uploads(
    authorization: Optional[str] = Header(None),
):
    """Return all video uploads belonging to the authenticated user, newest first."""
    caller    = await _get_caller(authorization)
    caller_id = caller.get("id") or caller.get("_id") or caller.get("sub", "")

    uploads = await db.get_video_uploads_by_user(caller_id)
    return [VideoUploadResponse(**u) for u in uploads]


@router.get(
    "/",
    response_model=List[VideoUploadResponse],
    summary="List all video uploads (admin only)",
)
async def list_all_video_uploads(
    authorization: Optional[str] = Header(None),
):
    """Admin-only endpoint that returns every VideoUpload across all users."""
    caller = await _get_caller(authorization)
    if not _is_admin(caller):
        raise HTTPException(status_code=403, detail="Admin access required")

    uploads = await db.get_all_video_uploads()
    return [VideoUploadResponse(**u) for u in uploads]


@router.delete(
    "/{video_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a video upload record",
)
async def delete_video_upload(
    video_id: str,
    authorization: Optional[str] = Header(None),
):
    """
    Delete a VideoUpload document by its MongoDB id.
    • The owner can always delete their own upload.
    • Admins can delete any upload.
    • Anyone else gets a 403.
    """
    caller    = await _get_caller(authorization)
    caller_id = caller.get("id") or caller.get("_id") or caller.get("sub", "")

    # Admins can delete anything; regular users only their own
    owner_filter = None if _is_admin(caller) else caller_id

    deleted = await db.delete_video_upload(video_id, user_id=owner_filter)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Video upload not found or you do not have permission to delete it",
        )
    return {"message": f"Video upload {video_id} deleted successfully"}
