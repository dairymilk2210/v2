import asyncio
import mimetypes
import os
from pathlib import Path
from io import BytesIO

import boto3
from botocore.exceptions import ClientError

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

STORAGE_DIR = Path(os.environ.get("FILE_STORAGE_DIR", Path(__file__).parent.parent / "uploads")).resolve()
APP_NAME = "poonji-finance"
S3_BUCKET = os.environ.get("S3_BUCKET", "")


def _s3():
    if not S3_BUCKET:
        raise RuntimeError("S3_BUCKET is required for cloud storage")
    return boto3.client("s3", region_name=os.environ.get("AWS_REGION") or None,
                        endpoint_url=os.environ.get("S3_ENDPOINT_URL") or None)


def _storage_mode() -> str:
    if S3_BUCKET:
        return "s3"
    if os.environ.get("RENDER"):
        raise RuntimeError("S3_BUCKET must be configured on Render; local uploads are ephemeral")
    return "local"

def _object_path(path: str) -> Path:
    target = (STORAGE_DIR / path).resolve()
    if target != STORAGE_DIR and STORAGE_DIR not in target.parents:
        raise ValueError("Invalid storage path")
    return target


def put_object(path: str, data: bytes, content_type: str) -> dict:
    if _storage_mode() == "s3":
        _s3().upload_fileobj(BytesIO(data), S3_BUCKET, path,
                             ExtraArgs={"ContentType": content_type, "ServerSideEncryption": "AES256"})
        return {"path": path, "size": len(data), "content_type": content_type}
    target = _object_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"path": path, "size": len(data), "content_type": content_type}


def get_object(path: str) -> tuple[bytes, str]:
    if _storage_mode() == "s3":
        try:
            obj = _s3().get_object(Bucket=S3_BUCKET, Key=path)
            return obj["Body"].read(), obj.get("ContentType") or "application/octet-stream"
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") not in {"NoSuchKey", "404"}:
                raise
            # Old uploads remain readable while the existing Render disk is migrated.
            if not _object_path(path).is_file():
                raise
    target = _object_path(path)
    content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return target.read_bytes(), content_type


async def put_object_async(path: str, data: bytes, content_type: str) -> dict:
    return await asyncio.to_thread(put_object, path, data, content_type)


async def get_object_async(path: str) -> tuple[bytes, str]:
    return await asyncio.to_thread(get_object, path)
