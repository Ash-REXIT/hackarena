"""Extract text from uploaded knowledge-base files."""

from __future__ import annotations

import io
from pathlib import Path

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


def extract_text(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {suffix}. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

    if suffix in {".txt", ".md"}:
        return content.decode("utf-8", errors="ignore").strip()

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise ValueError("PDF support requires pypdf. Run: pip install pypdf") from exc
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(pages).strip()
        if not text:
            raise ValueError("Could not extract text from PDF.")
        return text

    if suffix == ".docx":
        try:
            from docx import Document
        except ImportError as exc:
            raise ValueError("DOCX support requires python-docx. Run: pip install python-docx") from exc
        document = Document(io.BytesIO(content))
        paragraphs = [para.text.strip() for para in document.paragraphs if para.text.strip()]
        text = "\n\n".join(paragraphs).strip()
        if not text:
            raise ValueError("Could not extract text from DOCX.")
        return text

    raise ValueError(f"Unsupported file type: {suffix}")
