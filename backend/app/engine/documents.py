"""Text extraction for uploaded CVs. The file itself is not stored."""
from __future__ import annotations

import io


def extract_text(filename: str, raw: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf") or raw[:4] == b"%PDF":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(raw))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if name.endswith(".docx"):
        from docx import Document
        doc = Document(io.BytesIO(raw))
        return "\n".join(par.text for par in doc.paragraphs)
    if name.endswith(".txt") or name.endswith(".md"):
        return raw.decode("utf-8", errors="replace")
    raise ValueError("Format non pris en charge : envoyez un PDF, un DOCX ou un TXT.")
