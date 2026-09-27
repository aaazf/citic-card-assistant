import re
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class TextChunk:
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class TextSplitter(Protocol):
    def split(self, text: str, metadata: dict[str, Any] | None = None) -> list[TextChunk]: ...


class CharacterTextSplitter:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be between zero and chunk_size.")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str, metadata: dict[str, Any] | None = None) -> list[TextChunk]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        chunks: list[TextChunk] = []
        start = 0
        while start < len(normalized):
            end = min(start + self.chunk_size, len(normalized))
            if end < len(normalized):
                boundary = normalized.rfind(" ", start, end)
                if boundary > start + self.chunk_size // 2:
                    end = boundary
            content = normalized[start:end].strip()
            if content:
                chunks.append(TextChunk(content=content, metadata=dict(metadata or {})))
            if end >= len(normalized):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return chunks


class RecursiveTextSplitter:
    """Splits Chinese-friendly text along structural boundaries.

    Tries separators from coarse to fine (paragraph, newline, sentence,
    clause, space) and only hard-splits when no boundary keeps a chunk
    within chunk_size. Newlines are preserved. Each chunk after the first
    carries a short tail of the previous chunk as overlap.
    """

    SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", ";", "，", " ", ""]

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 120) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be greater than zero.")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be between zero and chunk_size.")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str, metadata: dict[str, Any] | None = None) -> list[TextChunk]:
        normalized = text.strip()
        if not normalized:
            return []
        pieces = self._split(normalized, self.SEPARATORS)
        chunks: list[TextChunk] = []
        previous_tail = ""
        for piece in pieces:
            content = (previous_tail + piece).strip()
            if content:
                chunks.append(TextChunk(content=content, metadata=dict(metadata or {})))
            previous_tail = piece[-self.chunk_overlap:] if self.chunk_overlap else ""
        return chunks

    def _split(self, text: str, separators: list[str]) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        separator: str | None = None
        level = len(separators) - 1
        for index, candidate in enumerate(separators):
            if candidate == "":
                break
            if candidate in text:
                separator = candidate
                level = index
                break
        if separator is None:
            return [
                text[start:start + self.chunk_size]
                for start in range(0, len(text), self.chunk_size)
            ]
        remaining = separators[level + 1:]
        chunks: list[str] = []
        current = ""
        raw_pieces = text.split(separator)
        pieces = [piece + separator for piece in raw_pieces[:-1]]
        if raw_pieces[-1]:
            pieces.append(raw_pieces[-1])
        for piece in pieces:
            candidate = f"{current}{piece}" if current else piece
            if len(candidate) <= self.chunk_size:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(piece) > self.chunk_size:
                chunks.extend(self._split(piece, remaining))
                current = ""
            else:
                current = piece
        if current:
            chunks.append(current)
        return chunks
