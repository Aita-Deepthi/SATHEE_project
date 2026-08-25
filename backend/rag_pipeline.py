"""Small, dependency-free RAG pipeline for SATHEE guidance.

The index uses token overlap with IDF weighting. It is intentionally local so
the app remains runnable without a vector database or a second service.
Documents can be added as Markdown or text files under ``knowledge/``.
"""

from dataclasses import dataclass
from pathlib import Path
import math
import re
from typing import Iterable

from knowledge_base import SATHEE_FACTS, WELL_WISHER_MESSAGE


_TOKEN_RE = re.compile(r"[a-z0-9]+")
_ROOT = Path(__file__).parent


@dataclass(frozen=True)
class Chunk:
    source: str
    text: str
    tokens: tuple[str, ...]


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _split_text(text: str, source: str, words_per_chunk: int = 180) -> Iterable[Chunk]:
    words = text.split()
    for start in range(0, len(words), words_per_chunk):
        chunk_text = " ".join(words[start:start + words_per_chunk]).strip()
        chunk_tokens = tuple(_tokens(chunk_text))
        if chunk_tokens:
            yield Chunk(f"{source} (part {start // words_per_chunk + 1})", chunk_text, chunk_tokens)


def _load_documents() -> list[tuple[str, str]]:
    documents = [
        ("SATHEE facts", SATHEE_FACTS),
        ("Well-wisher guidance", WELL_WISHER_MESSAGE),
    ]
    knowledge_dir = _ROOT / "knowledge"
    if knowledge_dir.exists():
        for path in sorted(knowledge_dir.glob("**/*")):
            if path.suffix.lower() in {".md", ".txt"} and path.is_file():
                documents.append((f"knowledge/{path.relative_to(knowledge_dir)}", path.read_text(encoding="utf-8")))
    return documents


class LocalRAG:
    def __init__(self, documents: Iterable[tuple[str, str]] | None = None):
        chunks: list[Chunk] = []
        for source, text in documents or _load_documents():
            chunks.extend(_split_text(text, source))
        self.chunks = chunks
        self.document_frequency: dict[str, int] = {}
        for chunk in chunks:
            for token in set(chunk.tokens):
                self.document_frequency[token] = self.document_frequency.get(token, 0) + 1

    def search(self, query: str, limit: int = 4) -> list[dict[str, str | float]]:
        query_tokens = set(_tokens(query))
        if not query_tokens:
            return []
        total = max(len(self.chunks), 1)
        scored = []
        for chunk in self.chunks:
            overlap = query_tokens.intersection(chunk.tokens)
            if not overlap:
                continue
            score = sum(math.log((total + 1) / (self.document_frequency.get(token, 0) + 1)) for token in overlap)
            score *= len(overlap) / math.sqrt(len(chunk.tokens))
            scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [{"source": chunk.source, "text": chunk.text, "score": round(score, 4)} for score, chunk in scored[:limit]]

    def context(self, query: str, limit: int = 4) -> str:
        results = self.search(query, limit)
        if not results:
            return "No relevant local knowledge-base passage was found."
        return "\n\n".join(f"[{item['source']}]\n{item['text']}" for item in results)


RAG = LocalRAG()


def retrieve_context(query: str, limit: int = 4) -> str:
    return RAG.context(query, limit)


def search_knowledge(query: str, limit: int = 4) -> list[dict[str, str | float]]:
    return RAG.search(query, limit)