"""
Chunk, embed, search - inside the run database.

No vector service, no API key, no network.
Vector retrieval is removed per requirements:
- "Do NOT implement RAG, vector databases, embeddings, or document retrieval."
- "Preserve and use the existing run.db SQLite database."
- "Do NOT add ChromaDB."

This stub preserves the module symbols so any existing imports and tests
remain compatible.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Optional model stub
MODEL = "BAAI/bge-small-en-v1.5"
DIM = 384
_embedder = None


def _model():
    return None


def _prepare(store: Any) -> None:
    pass


# -----------------------------------------------------------------------------
# Chunk & Provenance
# -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Chunk:
    """A retrieved passage and where it came from."""
    chunk_id: str
    doc: str
    ordinal: int
    text: str
    distance: float

    def cite(self) -> str:
        return f"{self.doc}#{self.ordinal}"


def split(text: str, target: int = 900, overlap: int = 150) -> list[str]:
    """Split on paragraph boundaries."""
    import re
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    out, buf = [], ""
    for p in paras:
        if buf and len(buf) + len(p) > target:
            out.append(buf)
            buf = (buf[-overlap:] + "\n\n" + p) if overlap else p
        else:
            buf = f"{buf}\n\n{p}" if buf else p
    if buf:
        out.append(buf)
    return out


# -----------------------------------------------------------------------------
# Ingestion Stub
# -----------------------------------------------------------------------------
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
def ingest(store: Any, folder: str | Path, patterns=("*.md", "*.txt")) -> dict:
    """No-op stub: RAG/vector retrieval not used in this project."""
    return {"files": 0, "chunks": 0, "skipped": 0, "note": "Vector search disabled"}


# -----------------------------------------------------------------------------
# Search Stub
# -----------------------------------------------------------------------------
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
#
def search(store: Any, query: str, k: int = 5) -> list[Chunk]:

    """No-op stub: returns empty list."""
    return []


def corpus_size(store: Any) -> int:
    return 0
