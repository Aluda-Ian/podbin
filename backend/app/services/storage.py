import os
import secrets
import re
from datetime import datetime
from typing import Dict, Any, Optional, AsyncGenerator, Tuple

def generate_signed_upload_url(filename: str, content_type: str = "video/mp4") -> Dict[str, Any]:
    """
    Generates a signed direct upload URL for cloud object storage (Vercel Blob / S3 / R2).
    Bypasses serverless function payload limits (~4.5MB).
    """
    clean_stem = re.sub(r'[^a-zA-Z0-9_-]', '', os.path.splitext(filename)[0])
    ext = os.path.splitext(filename)[1] or ".mp4"
    if not clean_stem:
        clean_stem = "media"
    unique_name = f"{clean_stem}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{secrets.token_hex(4)}{ext}"

    blob_token = os.getenv("BLOB_READ_WRITE_TOKEN")
    s3_bucket = os.getenv("S3_BUCKET") or os.getenv("AWS_STORAGE_BUCKET_NAME")

    if blob_token:
        # Vercel Blob direct upload endpoint
        upload_url = f"https://blob.vercel-storage.com/{unique_name}"
        download_url = f"https://public.blob.vercel-storage.com/{unique_name}"
        return {
            "upload_url": upload_url,
            "download_url": download_url,
            "filename": unique_name,
            "storage_provider": "vercel-blob",
            "method": "PUT",
            "headers": {
                "Authorization": f"Bearer {blob_token}",
                "x-api-version": "7",
                "content-type": content_type or "application/octet-stream"
            }
        }
    elif s3_bucket:
        try:
            import boto3
            s3_client = boto3.client(
                's3',
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name=os.getenv("AWS_REGION", "us-east-1")
            )
            presigned_url = s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': s3_bucket,
                    'Key': f"uploads/{unique_name}",
                    'ContentType': content_type
                },
                ExpiresIn=3600
            )
            region_str = f".{os.getenv('AWS_REGION')}" if os.getenv("AWS_REGION") else ""
            download_url = f"https://{s3_bucket}.s3{region_str}.amazonaws.com/uploads/{unique_name}"
            return {
                "upload_url": presigned_url,
                "download_url": download_url,
                "filename": unique_name,
                "storage_provider": "s3",
                "method": "PUT",
                "headers": {
                    "Content-Type": content_type or "application/octet-stream"
                }
            }
        except Exception as e:
            print(f"[Storage] S3 presigned URL generation notice: {e}")

    # Fallback to direct URL format for local dev / testing
    public_url = os.getenv("PUBLIC_URL", "https://podule.vendatechnologies.com").rstrip("/")
    return {
        "upload_url": f"{public_url}/api/v1/episodes/upload-direct?filename={unique_name}",
        "download_url": f"{public_url}/api/v1/episodes/media/{unique_name}",
        "filename": unique_name,
        "storage_provider": "direct-stream",
        "method": "PUT",
        "headers": {
            "Content-Type": content_type or "application/octet-stream"
        }
    }


# ─── MongoDB GridFS helpers ────────────────────────────────────────────────────

async def store_file_gridfs(filename: str, file_path, content_type: str = "application/octet-stream") -> bool:
    """
    Persist a local file into MongoDB GridFS using Motor (async).

    GridFS splits the file into 255 KB chunks so it can handle files of any size
    (well beyond MongoDB's 16 MB document limit).  This is a best-effort call —
    if MongoDB is unavailable the upload already succeeded to local disk.

    Args:
        filename:     The name to store the file under in GridFS.
        file_path:    Path-like object pointing to the already-written local file.
        content_type: MIME type stored as GridFS file metadata.

    Returns:
        True on success, False on any error.
    """
    try:
        from pathlib import Path as _Path
        from motor.motor_asyncio import AsyncIOMotorGridFSBucket
        from app.services.db import db as _db

        if not _db.is_db_ready or _db.client is None:
            return False

        db_name = os.getenv("MONGODB_DB", "podule")
        motor_db = _db.client[db_name]
        bucket = AsyncIOMotorGridFSBucket(motor_db, bucket_name="media")

        # Delete any existing file with the same name to keep GridFS clean
        try:
            async for grid_file in bucket.find({"filename": filename}):
                await bucket.delete(grid_file._id)
        except Exception:
            pass

        local = _Path(file_path)
        if not local.exists():
            return False

        CHUNK = 256 * 1024  # 256 KB read chunks
        async with await bucket.open_upload_stream(filename, metadata={"content_type": content_type}) as stream:
            with open(local, "rb") as fh:
                while True:
                    data = fh.read(CHUNK)
                    if not data:
                        break
                    await stream.write(data)

        print(f"[GridFS] Stored '{filename}' ({local.stat().st_size:,} bytes)")
        return True

    except Exception as e:
        print(f"[GridFS] store_file_gridfs error: {e}")
        return False


async def stream_file_gridfs(
    filename: str,
) -> Tuple[Optional[AsyncGenerator], Optional[str]]:
    """
    Return an async generator that streams a GridFS file in 256 KB chunks,
    along with its stored content-type.

    Returns (None, None) when the file is not found or MongoDB is unavailable.
    """
    try:
        from motor.motor_asyncio import AsyncIOMotorGridFSBucket
        from app.services.db import db as _db

        if not _db.is_db_ready or _db.client is None:
            return None, None

        db_name = os.getenv("MONGODB_DB", "podule")
        motor_db = _db.client[db_name]
        bucket = AsyncIOMotorGridFSBucket(motor_db, bucket_name="media")

        # Locate the file
        grid_out = None
        async for f in bucket.find({"filename": filename}):
            grid_out = f
            break

        if grid_out is None:
            return None, None

        content_type = (grid_out.metadata or {}).get("content_type", "application/octet-stream")

        async def _generate():
            stream = await bucket.open_download_stream_by_name(filename)
            CHUNK = 256 * 1024
            while True:
                data = await stream.read(CHUNK)
                if not data:
                    break
                yield data

        return _generate(), content_type

    except Exception as e:
        print(f"[GridFS] stream_file_gridfs error: {e}")
        return None, None
