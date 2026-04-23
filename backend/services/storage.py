"""Supabase Storage abstraction.

The Document Agent and the CV upload endpoint write/read PDF bytes
through this module. We also expose a text helper used by the document
agent to load the user's master CV when needed.

Tests can swap the underlying client by patching :func:`get_client`.
"""

from __future__ import annotations

from typing import Any, Final

from supabase import Client, create_client

from backend.config import get_settings
from backend.logging_config import get_logger

log = get_logger(__name__)

# Default signed-URL TTL for download endpoints (seconds).
DEFAULT_SIGNED_URL_TTL: Final[int] = 5 * 60

_client: Client | None = None


def get_client() -> Client:
    """Return a Supabase client backed by the service role key (lazy)."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(
            str(settings.SUPABASE_URL),
            settings.SUPABASE_SERVICE_KEY.get_secret_value(),
        )
    return _client


def reset_for_tests() -> None:
    """Drop the cached Supabase client so tests can inject a fake."""
    global _client
    _client = None


def _bucket_name() -> str:
    return get_settings().SUPABASE_STORAGE_BUCKET


async def upload_bytes(
    storage_path: str,
    content: bytes,
    *,
    content_type: str = "application/pdf",
    upsert: bool = True,
) -> str:
    """Upload raw bytes to Storage and return the storage path.

    ``storage_path`` should already include the bucket-relative folder
    (e.g. ``"users/<uid>/cv/master.pdf"``). Uploads run in the default
    threadpool because the supabase-py client is synchronous.
    """
    import asyncio

    bucket = _bucket_name()
    options: dict[str, str] = {
        "content-type": content_type,
        "x-upsert": "true" if upsert else "false",
    }

    def _sync_upload() -> Any:
        client = get_client()
        return client.storage.from_(bucket).upload(
            path=storage_path,
            file=content,
            file_options=options,
        )

    try:
        await asyncio.to_thread(_sync_upload)
        log.info(
            "storage.uploaded",
            bucket=bucket,
            path=storage_path,
            bytes=len(content),
            content_type=content_type,
        )
    except Exception:
        log.exception("storage.upload_failed", bucket=bucket, path=storage_path)
        raise
    return storage_path


async def download_bytes(storage_path: str) -> bytes:
    """Fetch raw bytes for the file at ``storage_path``."""
    import asyncio

    bucket = _bucket_name()

    def _sync_download() -> bytes:
        client = get_client()
        result = client.storage.from_(bucket).download(storage_path)
        return bytes(result)

    return await asyncio.to_thread(_sync_download)


async def download_text(storage_path: str, encoding: str = "utf-8") -> str:
    """Convenience: decode the downloaded file as text."""
    payload = await download_bytes(storage_path)
    return payload.decode(encoding, errors="ignore")


async def create_signed_url(storage_path: str, *, ttl_seconds: int = DEFAULT_SIGNED_URL_TTL) -> str:
    """Return a short-lived signed URL for the object at ``storage_path``."""
    import asyncio

    bucket = _bucket_name()

    def _sync_sign() -> str:
        client = get_client()
        result = client.storage.from_(bucket).create_signed_url(
            path=storage_path, expires_in=ttl_seconds
        )
        if isinstance(result, dict):
            return str(result.get("signedURL") or result.get("signed_url") or "")
        return str(result)

    url = await asyncio.to_thread(_sync_sign)
    if not url:
        raise RuntimeError(f"signed URL not returned for {storage_path}")
    return url


__all__ = [
    "DEFAULT_SIGNED_URL_TTL",
    "create_signed_url",
    "download_bytes",
    "download_text",
    "get_client",
    "reset_for_tests",
    "upload_bytes",
]
