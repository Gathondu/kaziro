"""Supabase Storage helpers for cached RapidAPI job-search JSON.

Objects are named from **sorted normalized keyword slugs** only
(see :func:`cache_object_basename`). Lookup can reuse a broader or
overlapping prior search to save RapidAPI quota.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Final, cast

from backend.config import get_settings
from backend.logging_config import get_logger
from backend.services import storage as storage_service

log = get_logger(__name__)

_SLUG_CLEAN: Final[re.Pattern[str]] = re.compile(r"[^a-z0-9]+")


def normalize_keyword_slug(text: str) -> str:
    """Lowercase slug for one user keyword phrase (stable file-name segment)."""
    raw = text.strip().lower()
    slug = _SLUG_CLEAN.sub("-", raw).strip("-")
    return slug or "keyword"


def keyword_slugs(keywords: list[str]) -> list[str]:
    """Sorted unique slugs for all non-empty keyword strings."""
    slugs = sorted({normalize_keyword_slug(k) for k in keywords if k and k.strip()})
    return slugs


def cache_object_basename(keywords: list[str]) -> str:
    """Storage object basename without ``.json`` (sorted slugs joined by ``++``)."""
    slugs = keyword_slugs(keywords)
    joined = "++".join(slugs)
    max_len = 180
    if len(joined) <= max_len:
        return joined
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()[:20]
    return f"{joined[: max_len - 21]}++{digest}"


def slug_set_from_cache_stem(stem: str) -> set[str]:
    """Recover slug set from a cache filename stem."""
    if "++" in stem:
        return {p for p in stem.split("++") if p}
    return {stem} if stem else set()


def pick_best_cache_object_name(
    *,
    current_slugs: set[str],
    exact_basename: str,
    listing: list[dict[str, Any]],
) -> str | None:
    """Return the best matching ``*.json`` object name, or ``None``.

    Preference order:

    1. Exact ``{exact_basename}.json`` when present.
    2. Otherwise maximize ``|S ∩ C|`` (overlap with cached slug set ``C``).
    3. Ties: prefer smaller ``|C|`` (tighter cached query).
    4. Ties: lexicographically smallest name (deterministic).
    """
    names = [
        str(row.get("name", "")) for row in listing if str(row.get("name", "")).endswith(".json")
    ]
    exact = f"{exact_basename}.json"
    if exact in names:
        return exact

    best: str | None = None
    best_key: tuple[int, int, str] | None = None
    for name in names:
        stem = name.removesuffix(".json")
        cached = slug_set_from_cache_stem(stem)
        if not cached or not current_slugs:
            continue
        inter = current_slugs & cached
        subset = current_slugs <= cached
        if not inter and not subset:
            continue
        inter_size = len(inter)
        key = (inter_size, -len(cached), name)
        if best_key is None or key > best_key:
            best_key = key
            best = name
    return best


def parse_cache_payload(raw_json: dict[str, Any]) -> dict[str, Any]:
    """Return the upstream RapidAPI body (unwrap our envelope if present)."""
    inner = raw_json.get("upstream")
    if isinstance(inner, dict):
        return inner
    return raw_json


async def try_load_cache_json(object_name: str) -> dict[str, Any] | None:
    """Download and parse JSON from the job-posts bucket, or ``None`` on failure."""
    bucket = get_settings().SUPABASE_JOB_POSTS_BUCKET
    try:
        text = await storage_service.download_text(object_name, bucket=bucket)
    except Exception:
        log.warning("job_posts_cache.download_failed", bucket=bucket, object=object_name)
        return None
    try:
        parsed: Any = json.loads(text)
    except json.JSONDecodeError:
        log.warning("job_posts_cache.invalid_json", bucket=bucket, object=object_name)
        return None
    if isinstance(parsed, dict):
        return cast(dict[str, Any], parsed)
    log.warning("job_posts_cache.root_not_object", bucket=bucket, object=object_name)
    return None


async def list_cache_objects() -> list[dict[str, Any]]:
    bucket = get_settings().SUPABASE_JOB_POSTS_BUCKET
    return await storage_service.list_bucket_files(bucket, prefix="", limit=2000)


async def save_cache_envelope(
    *,
    object_name: str,
    keyword_slugs: list[str],
    upstream: dict[str, Any],
    fetched_at_iso: str,
) -> None:
    bucket = get_settings().SUPABASE_JOB_POSTS_BUCKET
    envelope = {
        "keyword_slugs": keyword_slugs,
        "fetched_at": fetched_at_iso,
        "upstream": upstream,
    }
    payload = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
    await storage_service.upload_bytes(
        object_name,
        payload,
        bucket=bucket,
        content_type="application/json",
        upsert=True,
    )


__all__ = [
    "cache_object_basename",
    "keyword_slugs",
    "list_cache_objects",
    "normalize_keyword_slug",
    "parse_cache_payload",
    "pick_best_cache_object_name",
    "save_cache_envelope",
    "slug_set_from_cache_stem",
    "try_load_cache_json",
]
