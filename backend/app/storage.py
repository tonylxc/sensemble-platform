"""MinIO 原始件归档（FR-4.3）。尽力而为：MinIO 不可用时返回 None，不影响主流程。"""
import io
from .config import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        from minio import Minio
        _client = Minio(settings.minio_endpoint, access_key=settings.minio_user,
                        secret_key=settings.minio_password, secure=settings.minio_secure)
    return _client


def archive_csv(object_name: str, data: bytes) -> str | None:
    """把 CSV 字节归档到 MinIO，返回对象路径；失败返回 None。"""
    if not settings.minio_enabled:
        return None
    try:
        c = _get_client()
        if not c.bucket_exists(settings.minio_bucket):
            c.make_bucket(settings.minio_bucket)
        c.put_object(settings.minio_bucket, object_name, io.BytesIO(data),
                     length=len(data), content_type="text/csv")
        return f"{settings.minio_bucket}/{object_name}"
    except Exception:
        return None
