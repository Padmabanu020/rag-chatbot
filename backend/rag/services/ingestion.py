"""Ingestion pipeline: load -> chunk -> embed -> store."""
import re
from django.conf import settings
from pypdf import PdfReader
from docx import Document as DocxDocument

from . import ollama_client, vectorstore

SUPPORTED = {"pdf", "docx", "txt", "md"}


def load_pages(path, ext):
    """Return a list of (page_number | None, text)."""
    if ext == "pdf":
        return [(i + 1, p.extract_text() or "") for i, p in enumerate(PdfReader(path).pages)]
    if ext == "docx":
        return [(None, "\n\n".join(p.text for p in DocxDocument(path).paragraphs))]
    with open(path, encoding="utf-8", errors="ignore") as fh:
        return [(None, fh.read())]


def chunk_text(text, size, overlap):
    """Sliding-window chunking that prefers paragraph/sentence boundaries."""
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            cut = max(text.rfind("\n\n", start, end), text.rfind(". ", start, end))
            if cut > start + size // 2:
                end = cut + 1
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def ingest(doc):
    """Process an uploaded Document; updates its status and chunk count."""
    try:
        chunks = []
        for page, text in load_pages(doc.file.path, doc.file_type):
            for piece in chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP):
                chunks.append({"text": piece, "page": page, "index": len(chunks)})
        if not chunks:
            raise ValueError("No extractable text found (scanned PDFs need OCR).")

        embeddings = []
        for i in range(0, len(chunks), 32):  # batch embedding calls
            embeddings += ollama_client.embed([c["text"] for c in chunks[i:i + 32]])

        vectorstore.add_chunks(doc.id, doc.name, chunks, embeddings)
        doc.chunk_count, doc.status, doc.error = len(chunks), "ready", ""
    except Exception as exc:
        doc.status, doc.error = "failed", str(exc)[:1000]
        doc.save()
        raise
    doc.save()
