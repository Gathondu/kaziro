"""Supabase Storage abstraction.

The Document Agent and the CV upload endpoint write/read PDF bytes
through this module. We also expose a text helper used by the document
agent to load the user's master CV when needed.

Tests can swap the underlying client by patching :func:`get_client`.
"""

from __future__ import annotations

from typing import Any, Final, cast

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
    bucket: str | None = None,
    content_type: str = "application/pdf",
    upsert: bool = True,
) -> str:
    """Upload raw bytes to Storage and return the storage path.

    ``storage_path`` should already include the bucket-relative folder
    (e.g. ``"users/<uid>/cv/master.pdf"``). Uploads run in the default
    threadpool because the supabase-py client is synchronous.

    When ``bucket`` is omitted, uses :attr:`Settings.SUPABASE_STORAGE_BUCKET`.
    """
    import asyncio

    bucket = bucket or _bucket_name()
    options: dict[str, str] = {
        "content-type": content_type,
        "x-upsert": "true" if upsert else "false",
    }

    def _sync_upload() -> Any:
        client = get_client()
        return client.storage.from_(bucket).upload(
            path=storage_path,
            file=content,
            file_options=cast(Any, options),
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


async def download_bytes(storage_path: str, *, bucket: str | None = None) -> bytes:
    """Fetch raw bytes for the file at ``storage_path``.

    When ``bucket`` is omitted, uses :attr:`Settings.SUPABASE_STORAGE_BUCKET`.
    """
    import asyncio

    bucket = bucket or _bucket_name()

    def _sync_download() -> bytes:
        client = get_client()
        result = client.storage.from_(bucket).download(storage_path)
        return bytes(result)

    return await asyncio.to_thread(_sync_download)


async def download_text(
    storage_path: str, encoding: str = "utf-8", *, bucket: str | None = None
) -> str:
    """Convenience: decode the downloaded file as text."""
    payload = await download_bytes(storage_path, bucket=bucket)
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


async def list_bucket_files(
    bucket: str,
    *,
    prefix: str = "",
    limit: int = 1000,
) -> list[dict[str, Any]]:
    """List objects in a bucket (flat path names under ``prefix``)."""
    import asyncio

    def _sync_list() -> list[dict[str, Any]]:
        client = get_client()
        rows = client.storage.from_(bucket).list(prefix, {"limit": limit})
        return list(rows) if isinstance(rows, list) else []

    return await asyncio.to_thread(_sync_list)


async def delete_storage_paths(paths: list[str], *, bucket: str | None = None) -> None:
    """Best-effort remove objects at ``paths`` (ignores empty strings).

    Failures are logged at WARNING; callers keep DB consistency even if
    Supabase returns an error for a missing path.
    """
    import asyncio

    bucket = bucket or _bucket_name()
    cleaned = [p for p in paths if p]
    if not cleaned:
        return

    def _sync_remove() -> None:
        client = get_client()
        client.storage.from_(bucket).remove(cleaned)

    try:
        await asyncio.to_thread(_sync_remove)
        log.info("storage.removed", bucket=bucket, count=len(cleaned))
    except Exception as exc:
        log.warning(
            "storage.remove_failed",
            bucket=bucket,
            paths_count=len(cleaned),
            error=str(exc),
        )


__all__ = [
    "DEFAULT_SIGNED_URL_TTL",
    "create_signed_url",
    "delete_storage_paths",
    "download_bytes",
    "download_text",
    "get_client",
    "list_bucket_files",
    "reset_for_tests",
    "upload_bytes",
]
