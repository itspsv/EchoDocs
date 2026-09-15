"""Chunking, local embeddings, and a FAISS index for one document at a time."""
from __future__ import annotations

import pickle
import re
import threading
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
INDEX_PATH = DATA_DIR / "index.faiss"
CHUNKS_PATH = DATA_DIR / "chunks.pkl"

CHUNK_SIZE = 800
CHUNK_OVERLAP = 150

# all-MiniLM-L6-v2 cosine similarity: on this project's own test PDF,
# on-topic queries scored 0.38-0.51 and off-topic ones scored -0.07-0.06,
# a wide, consistent gap. 0.2 sits in the middle of it so a question the
# document doesn't cover returns nothing instead of its nearest-but-
# irrelevant chunks, letting the agent's "say you don't know" instruction
# actually fire.
MIN_SCORE = 0.2

_model = None
_model_lock = threading.Lock()


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


class VectorStore:
    """Holds one document's chunks and their embeddings. A new ingest replaces it."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.index: faiss.Index | None = None
        self.chunks: list[str] = []
        self.source: str | None = None
        self._load()

    def _load(self) -> None:
        if INDEX_PATH.exists() and CHUNKS_PATH.exists():
            self.index = faiss.read_index(str(INDEX_PATH))
            with open(CHUNKS_PATH, "rb") as f:
                saved = pickle.load(f)
            self.chunks = saved["chunks"]
            self.source = saved["source"]

    def _save(self) -> None:
        faiss.write_index(self.index, str(INDEX_PATH))
        with open(CHUNKS_PATH, "wb") as f:
            pickle.dump({"chunks": self.chunks, "source": self.source}, f)

    def ingest(self, text: str, source: str) -> int:
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError(
                "no selectable text found in that document — if it's a PDF, it may be "
                "scanned pages/images rather than real text, which this doesn't OCR"
            )
        model = _get_model()
        vectors = np.asarray(model.encode(chunks, normalize_embeddings=True), dtype="float32")
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        with self._lock:
            self.index = index
            self.chunks = chunks
            self.source = source
            self._save()
        return len(chunks)

    def search(self, query: str, k: int = 4) -> list[dict]:
        with self._lock:
            if self.index is None or not self.chunks:
                return []
            model = _get_model()
            vector = np.asarray(model.encode([query], normalize_embeddings=True), dtype="float32")
            scores, indices = self.index.search(vector, min(k, len(self.chunks)))
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score < MIN_SCORE:
                continue
            results.append({"text": self.chunks[idx], "score": float(score)})
        return results


store = VectorStore()
