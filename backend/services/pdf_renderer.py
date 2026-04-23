"""PDF rendering for tailored CVs and cover letters.

The Document Agent calls :func:`render_pdf_and_upload` to produce a
PDF from plain text and store it in Supabase Storage.  Rendering uses
WeasyPrint with a tiny embedded HTML/CSS template; the template
accepts plain-text content (whitespace preserved) so we don't have to
ship a Jinja layer for the Phase 2 happy path.
"""

from __future__ import annotations

import asyncio
import html
import uuid
from typing import Final

from backend.logging_config import get_logger
from backend.services.storage import upload_bytes

log = get_logger(__name__)

_HTML_TEMPLATE: Final[str] = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  @page {{ size: A4; margin: 18mm 16mm; }}
  body {{ font-family: 'Helvetica', 'Arial', sans-serif; color: #1f2937; font-size: 11pt; line-height: 1.45; }}
  h1.doc-title {{ font-size: 16pt; margin: 0 0 14pt 0; color: #111827; }}
  pre.doc-body {{ white-space: pre-wrap; font-family: inherit; font-size: 11pt; margin: 0; }}
</style>
</head>
<body>
  <h1 class="doc-title">{title}</h1>
  <pre class="doc-body">{body}</pre>
</body>
</html>"""


def _render_html(title: str, body: str) -> str:
    return _HTML_TEMPLATE.format(title=html.escape(title), body=html.escape(body))


def _render_pdf_sync(title: str, body: str) -> bytes:
    """Run WeasyPrint in the calling thread and return the rendered PDF bytes.

    Imported lazily so test environments that don't have the native
    deps installed can still import this module.
    """
    from weasyprint import HTML

    rendered: bytes = HTML(string=_render_html(title, body)).write_pdf()
    return rendered


async def render_pdf(content: str, *, title: str) -> bytes:
    """Render ``content`` to PDF bytes using WeasyPrint."""
    return await asyncio.to_thread(_render_pdf_sync, title, content)


async def render_pdf_and_upload(
    content: str,
    *,
    title: str,
    storage_path: str,
) -> str:
    """Render ``content`` to PDF and upload to Storage at ``storage_path``.

    Returns the storage path on success.
    """
    log.info("pdf.render_start", title=title, storage_path=storage_path)
    payload = await render_pdf(content, title=title)
    await upload_bytes(storage_path, payload, content_type="application/pdf")
    log.info("pdf.render_uploaded", storage_path=storage_path, bytes=len(payload))
    return storage_path


def storage_path_for_doc(
    *, user_id: str | uuid.UUID, doc_kind: str, doc_id: str | uuid.UUID
) -> str:
    """Canonical storage path for an application document PDF.

    ``doc_kind`` is one of ``"cv"`` or ``"cover_letter"``. Keeping the
    naming centralised here means the Document Agent and the download
    endpoint never disagree about where files live.
    """
    return f"applications/{user_id}/{doc_id}/{doc_kind}.pdf"


__all__ = [
    "render_pdf",
    "render_pdf_and_upload",
    "storage_path_for_doc",
]
