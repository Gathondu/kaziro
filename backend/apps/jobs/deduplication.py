from __future__ import annotations

import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_QUERY_PARAMETERS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "referrer",
    "source",
}


def normalize_job_url(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    parsed = urlsplit(text)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return text

    hostname = parsed.hostname.lower()
    port = parsed.port
    default_port = (parsed.scheme.lower() == "http" and port == 80) or (
        parsed.scheme.lower() == "https" and port == 443
    )
    netloc = hostname if port is None or default_port else f"{hostname}:{port}"
    path = parsed.path.rstrip("/") or "/"
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_QUERY_PARAMETERS
        )
    )
    return urlunsplit((parsed.scheme.lower(), netloc, path, query, ""))


def stable_job_external_id(application_url: object, upstream_id: str) -> str:
    normalized_url = normalize_job_url(application_url)
    if not normalized_url:
        return upstream_id
    digest = hashlib.sha256(normalized_url.encode("utf-8")).hexdigest()
    return f"url:{digest}"


__all__ = ["normalize_job_url", "stable_job_external_id"]
