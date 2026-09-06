import io
import uuid

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


def ensure_bucket_exists() -> None:
    if not _client.bucket_exists(settings.minio_bucket):
        _client.make_bucket(settings.minio_bucket)


def _generate_key(prefix: str, extension: str) -> str:
    return f"{prefix}/{uuid.uuid4().hex}.{extension}"


def upload_bytes(data: bytes, prefix: str, extension: str, content_type: str) -> str:
    """Uploads raw bytes under a generated key (never trusts a client-supplied filename). Returns the object key."""
    key = _generate_key(prefix, extension)
    _client.put_object(
        settings.minio_bucket,
        key,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return key


def download_bytes(key: str) -> bytes:
    response = _client.get_object(settings.minio_bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_object(key: str) -> None:
    try:
        _client.remove_object(settings.minio_bucket, key)
    except S3Error:
        pass  # already gone / never existed — deletion should be idempotent
