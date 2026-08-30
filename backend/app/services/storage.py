"""
storage.py — Podule Media Storage Service
==========================================
Handles all file storage concerns:

  1. generate_signed_upload_url()  → returns a signed URL for direct-to-cloud
                                     upload (Vercel Blob or AWS S3).
                                     Falls back to the in-app chunked-upload
                                     endpoints when no cloud provider is set.

  2. store_file_gridfs()           → persists a local file into MongoDB GridFS
                                     (async, best-effort, non-blocking).

  3. stream_file_gridfs()          → returns an async byte-generator that
                                     streams a GridFS file to the HTTP client.

MongoDB GridFS notes
--------------------
• Motor's AsyncIOMotorGridFSBucket is used directly — no Beanie dependency.
• Files are stored in the "media" bucket (collections: media.files / media.chunks).
• Each chunk stored in GridFS is 255 KB (MongoDB default).
• Files of any size are supported; the 16 MB BSON document limit does NOT apply
  to GridFS because the binary data lives in the chunks collection, not in a
  single document.
• Both store and stream functions are safe no-ops when MongoDB is unavailable.
"""

from __future__ import annotations

import os
import secrets
import re
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, Any, Optional, Tuple

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_CLEAN_RE = re.compile(r"[^a-zA-Z0-9_-]")


def _unique_filename(original: str) -> str:
    """Return a collision-safe filename derived from *original*."""
    stem = _CLEAN_RE.sub("", Path(original).stem) or "media"
    ext  = Path(original).suffix or ".mp4"
    ts   = datetime.now().strftime("%Y%m%d%H%M%S")
    rand = secrets.token_hex(4)
    return f"{stem}_{ts}_{rand}{ext}"


def _public_url() -> str:
    return os.getenv("PUBLIC_URL", "https://podule.vendatechnologies.com").rstrip("/")


# ---------------------------------------------------------------------------
# 1. Signed / direct upload URL generation
# ---------------------------------------------------------------------------

def generate_signed_upload_url(
    filename: str,
    content_type: str = "video/mp4",
) -> Dict[str, Any]:
    """
    Return a dict describing where and how the client should upload *filename*.

    Priority order:
      1. Vercel Blob  (BLOB_READ_WRITE_TOKEN is set)
      2. AWS S3       (S3_BUCKET or AWS_STORAGE_BUCKET_NAME is set)
      3. Direct       (chunked in-app upload — works with any server)

    The returned dict always has these keys:
      upload_url      – where to PUT/POST the file
      download_url    – where to GET the file after upload
      filename        – the server-side filename (may differ from the original)
      storage_provider– one of: "vercel-blob", "s3", "direct-stream"
      method          – HTTP method the client should use ("PUT" or "POST")
      headers         – dict of request headers to include in the upload
    """
    unique_name  = _unique_filename(filename)
    blob_token   = os.getenv("BLOB_READ_WRITE_TOKEN")
    s3_bucket    = os.getenv("S3_BUCKET") or os.getenv("AWS_STORAGE_BUCKET_NAME")

    # ── Vercel Blob ──────────────────────────────────────────────────────────
    if blob_token:
        return {
            "upload_url":       f"https://blob.vercel-storage.com/{unique_name}",
            "download_url":     f"https://public.blob.vercel-storage.com/{unique_name}",
            "filename":         unique_name,
            "storage_provider": "vercel-blob",
            "method":           "PUT",
            "headers": {
                "Authorization": f"Bearer {blob_token}",
                "x-api-version": "7",
                "content-type":  content_type or "application/octet-stream",
            },
        }

    # ── AWS S3 (pre-signed PUT) ──────────────────────────────────────────────
    if s3_bucket:
        try:
            import boto3  # type: ignore[import-untyped]

            region     = os.getenv("AWS_REGION", "us-east-1")
            s3         = boto3.client(
                "s3",
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=region,
            )
            presigned: str = s3.generate_presigned_url(
                "put_object",
                Params={"Bucket": s3_bucket, "Key": f"uploads/{unique_name}", "ContentType": content_type},
                ExpiresIn=3600,
            )
            region_suffix = f".{region}" if region else ""
            download_url  = f"https://{s3_bucket}.s3{region_suffix}.amazonaws.com/uploads/{unique_name}"
            return {
                "upload_url":       presigned,
                "download_url":     download_url,
                "filename":         unique_name,
                "storage_provider": "s3",
                "method":           "PUT",
                "headers":          {"Content-Type": content_type or "application/octet-stream"},
            }
        except Exception as exc:
            print(f"[Storage] S3 presigned URL error: {exc}")

    # ── Direct (chunked in-app upload) ───────────────────────────────────────
    base = _public_url()
    return {
        "upload_url":       f"{base}/api/v1/episodes/upload-direct?filename={unique_name}",
        "download_url":     f"{base}/api/v1/episodes/media/{unique_name}",
        "filename":         unique_name,
        "storage_provider": "direct-stream",
        "method":           "PUT",
        "headers":          {"Content-Type": content_type or "application/octet-stream"},
    }


# ---------------------------------------------------------------------------
# 2. MongoDB GridFS — store a local file
# ---------------------------------------------------------------------------

async def store_file_gridfs(
    filename: str,
    file_path: "Path | str",
    content_type: str = "application/octet-stream",
) -> bool:
    """
    Upload *file_path* into MongoDB GridFS under *filename*.

    • Uses Motor's AsyncIOMotorGridFSBucket — no Beanie dependency.
    • Reads the file in 256 KB chunks to keep RAM usage flat regardless of
      file size.
    • If a file with the same name already exists in GridFS it is deleted
      first so the bucket stays clean.
    • Returns True on success, False on any error (MongoDB unavailable, file
      missing, etc.).  Errors are logged but never raised — callers treat this
      as a best-effort persistence layer.
    """
    try:
        # Late imports keep startup fast and avoid circular dependencies
        from motor.motor_asyncio import AsyncIOMotorGridFSBucket  # type: ignore[import-untyped]
        from app.services.db import db as _db

        if not _db.is_db_ready or _db.client is None:
            print("[GridFS] Skipped — MongoDB not ready")
            return False

        local = Path(file_path)
        if not local.exists():
            print(f"[GridFS] Source file not found: {local}")
            return False

        db_name  = os.getenv("MONGODB_DB", "podule")
        motor_db = _db.client[db_name]
        bucket   = AsyncIOMotorGridFSBucket(motor_db, bucket_name="media")

        # Delete any previous version with the same name
        try:
            async for existing in bucket.find({"filename": filename}):
                await bucket.delete(existing._id)
                print(f"[GridFS] Removed old version of '{filename}'")
        except Exception as del_err:
            print(f"[GridFS] Cleanup warning: {del_err}")

        # Stream file → GridFS in 256 KB blocks
        READ_CHUNK = 256 * 1024
        async with await bucket.open_upload_stream(
            filename,
            metadata={"content_type": content_type},
        ) as gfs_stream:
            with open(local, "rb") as fh:
                while True:
                    block = fh.read(READ_CHUNK)
                    if not block:
                        break
                    await gfs_stream.write(block)

        size_mb = local.stat().st_size / 1_048_576
        print(f"[GridFS] Stored '{filename}' ({size_mb:.2f} MB)")
        return True

    except Exception as exc:
        print(f"[GridFS] store_file_gridfs failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# 3. MongoDB GridFS — stream a file to the HTTP client
# ---------------------------------------------------------------------------

async def stream_file_gridfs(
    filename: str,
) -> Tuple[Optional[AsyncGenerator[bytes, None]], Optional[str]]:
    """
    Locate *filename* in MongoDB GridFS and return an async byte-generator
    together with the stored MIME type.

    Usage (FastAPI)::

        gen, ct = await stream_file_gridfs("episode.mp4")
        if gen:
            return StreamingResponse(gen, media_type=ct)

    Returns ``(None, None)`` when:
      • MongoDB is not connected
      • The file does not exist in GridFS
      • Any other error occurs (logged, not raised)
    """
    try:
        from motor.motor_asyncio import AsyncIOMotorGridFSBucket  # type: ignore[import-untyped]
        from app.services.db import db as _db

        if not _db.is_db_ready or _db.client is None:
            return None, None

        db_name  = os.getenv("MONGODB_DB", "podule")
        motor_db = _db.client[db_name]
        bucket   = AsyncIOMotorGridFSBucket(motor_db, bucket_name="media")

        # Find the file metadata document
        grid_file = None
        async for doc in bucket.find({"filename": filename}):
            grid_file = doc
            break

        if grid_file is None:
            return None, None

        content_type: str = (grid_file.metadata or {}).get(
            "content_type", "application/octet-stream"
        )

        async def _byte_stream() -> AsyncGenerator[bytes, None]:
            """Yield the GridFS file in 256 KB chunks."""
            READ_CHUNK = 256 * 1024
            dl_stream  = await bucket.open_download_stream_by_name(filename)
            while True:
                chunk = await dl_stream.read(READ_CHUNK)
                if not chunk:
                    break
                yield chunk

        return _byte_stream(), content_type

    except Exception as exc:
        print(f"[GridFS] stream_file_gridfs failed: {exc}")
        return None, None
