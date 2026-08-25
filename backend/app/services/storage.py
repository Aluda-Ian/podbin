import os
import secrets
import re
from datetime import datetime
from typing import Dict, Any, Optional

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
