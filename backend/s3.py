import os
import re
import uuid
import mimetypes

from config import get_config, get_s3_client


def parse_s3_path(s3_path: str) -> tuple[str, str]:
    config = get_config()
    if s3_path.startswith("s3://"):
        parts = s3_path[5:].split("/", 1)
        return parts[0], parts[1] if len(parts) > 1 else ""
    return config.s3_bucket, s3_path


def sanitize_filename(filename: str) -> str:
    name, ext = os.path.splitext(filename)
    # Replace spaces with hyphens, remove special chars, lowercase
    name = re.sub(r'[^\w\-]', '', name.replace(' ', '-').lower())
    # Limit length
    name = name[:50] if len(name) > 50 else name
    return f"{name}{ext.lower()}"


def download(s3_path: str) -> tuple[bytes, str, str]:
    bucket, key = parse_s3_path(s3_path)
    s3 = get_s3_client()
    
    try:
        response = s3.get_object(Bucket=bucket, Key=key)
        return response["Body"].read(), bucket, key
    except Exception as e:
        if "NoSuchKey" in str(type(e).__name__) or "NoSuchKey" in str(e):
            raise FileNotFoundError(f"File not found: {key} (bucket: {bucket})")
        raise


def upload_url(filename: str, content_type: str | None = None) -> dict:
    config = get_config()
    s3 = get_s3_client()
    
    # Generate document ID
    doc_id = str(uuid.uuid4())[:8]  # Short ID for readability
    
    # Create key: uploads/{sanitized-name}-{id}.{ext}
    name, ext = os.path.splitext(filename)
    safe_name = re.sub(r'[^\w\-]', '', name.replace(' ', '-').lower())[:50]
    key = f"uploads/{safe_name}-{doc_id}{ext.lower()}"
    
    if not content_type:
        content_type, _ = mimetypes.guess_type(filename)
        content_type = content_type or "application/octet-stream"
    
    url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": config.s3_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=3600
    )
    
    return {
        "url": url,
        "s3_path": f"s3://{config.s3_bucket}/{key}",
        "key": key,
        "content_type": content_type,
        "expires_in": 3600,
        "original_filename": filename,
    }


def view_url(s3_path: str) -> dict:
    bucket, key = parse_s3_path(s3_path)
    s3 = get_s3_client()
    
    url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=3600
    )
    
    return {
        "url": url,
        "s3_path": s3_path,
        "filename": os.path.basename(key),
        "expires_in": 3600
    }
