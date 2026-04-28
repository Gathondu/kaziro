"""Build tiny PDFs with extractable text (stdlib only — works on Windows CI)."""

from __future__ import annotations

import re
import zlib


def _pdf_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def pdf_bytes_with_text(body: str) -> bytes:
    """Return a single-page PDF whose text ``pypdf`` can extract.

    Avoids WeasyPrint / GTK so tests run on Windows hosts without native
    PDF layout libraries.
    """
    text = _pdf_escape(body)
    font_obj = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    content = b"BT /F1 11 Tf 72 720 Td (" + text.encode("latin-1", errors="replace") + b") Tj ET"
    content_compressed = zlib.compress(content)

    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
    )
    objects.append(
        b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(content_compressed)
        + content_compressed
        + b"\nendstream"
    )
    objects.append(font_obj)

    xref_offset = 0
    parts: list[bytes] = [b"%PDF-1.4\n"]
    offsets: list[int] = [0]
    for i, obj in enumerate(objects, start=1):
        offsets.append(sum(len(p) for p in parts))
        parts.append(f"{i} 0 obj\n".encode("ascii"))
        parts.append(obj + b"\nendobj\n")

    xref_offset = sum(len(p) for p in parts)
    parts.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    parts.append(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        parts.append(f"{off:010d} 00000 n \n".encode("ascii"))
    parts.append(b"trailer\n")
    parts.append(f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii"))
    parts.append(b"startxref\n")
    parts.append(f"{xref_offset}\n".encode("ascii"))
    parts.append(b"%%EOF\n")
    return b"".join(parts)


def pdf_text_contains_only_master_words(
    tailored: str, master: str, *, extra_allowed: frozenset[str] = frozenset()
) -> bool:
    """Heuristic: every word in tailored appears in master or allow-list."""
    words = re.findall(r"[A-Za-z]{3,}", tailored.lower())
    master_l = master.lower()
    allowed = extra_allowed | frozenset(
        {
            "experience",
            "skills",
            "education",
            "summary",
            "work",
            "the",
            "and",
            "for",
            "with",
        }
    )
    for w in words:
        if w in allowed:
            continue
        if w not in master_l:
            return False
    return True
