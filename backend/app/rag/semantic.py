import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.providers.base import ChatMessage
from app.providers.llm import LLMProvider
from app.rag.splitter import RecursiveTextSplitter, TextChunk

logger = logging.getLogger(__name__)

_PARAGRAPH_SPLIT = re.compile(r"\n+")
_STRUCTURAL_ANCHOR = re.compile(
    r"^(#{1,6}\s|第[0-9零一二三四五六七八九十百]+[条章节部分编]|[一二三四五六七八九十]+[、.．]|\d+[、.．]|[Qq问][：:])"
)

_GROUPING_PROMPT = (
    "你是文档切分器。把下面编号连续的段落按语义完整性分组，"
    "每组是一个可以独立理解的业务单元（例如一条合约条款、一组问答）。"
    "只输出严格 JSON 数组，元素为 [起始段落号, 结束段落号]（1 起，含端点），"
    "必须按顺序覆盖全部段落且每段恰好出现一次。不要输出任何其他内容。"
)


class StructuralTextSplitter:
    """Splits text into units along structural anchors (clauses, headings, Q/A)."""

    def split(self, text: str, metadata: dict[str, Any] | None = None) -> list[TextChunk]:
        units: list[str] = []
        current: list[str] = []
        for line in text.split("\n"):
            if _STRUCTURAL_ANCHOR.match(line.strip()) and current:
                units.append("\n".join(current))
                current = [line]
            else:
                current.append(line)
        if current:
            units.append("\n".join(current))
        return [
            TextChunk(content=unit.strip(), metadata=dict(metadata or {}))
            for unit in units
            if unit.strip()
        ]


class SemanticLLMSplitter:
    """Uses an LLM to group paragraphs into semantic units.

    Returns None when the text is unsuitable or the model output cannot be
    validated, so callers can fall back to structural splitting.
    """

    def __init__(self, llm_provider: LLMProvider, max_paragraphs: int = 40) -> None:
        self.llm_provider = llm_provider
        self.max_paragraphs = max_paragraphs

    async def split(
        self,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[TextChunk] | None:
        paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT.split(text) if p.strip()]
        if len(paragraphs) < 3 or len(paragraphs) > self.max_paragraphs:
            return None
        numbered = "\n".join(
            f"[{index}] {paragraph}" for index, paragraph in enumerate(paragraphs, start=1)
        )
        try:
            response = await self.llm_provider.chat(
                [
                    ChatMessage(role="system", content=_GROUPING_PROMPT),
                    ChatMessage(role="user", content=numbered),
                ]
            )
            groups = self._parse_groups(response.content, len(paragraphs))
        except Exception:
            logger.exception("semantic split failed; falling back to structural split")
            return None
        if groups is None:
            return None
        return [
            TextChunk(
                content="\n".join(paragraphs[start - 1:end]),
                metadata=dict(metadata or {}),
            )
            for start, end in groups
        ]

    @staticmethod
    def _parse_groups(content: str, paragraph_count: int) -> list[tuple[int, int]] | None:
        text = content.strip()
        fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fenced:
            text = fenced.group(1).strip()
        array = re.search(r"\[.*\]", text, re.DOTALL)
        if not array:
            return None
        try:
            payload = json.loads(array.group(0))
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, list) or not payload:
            return None
        groups: list[tuple[int, int]] = []
        for item in payload:
            if (
                not isinstance(item, list)
                or len(item) != 2
                or not all(isinstance(value, int) for value in item)
            ):
                return None
            groups.append((item[0], item[1]))
        covered: list[int] = []
        for start, end in groups:
            if start < 1 or end < start or end > paragraph_count:
                return None
            covered.extend(range(start, end + 1))
        if covered != list(range(1, paragraph_count + 1)):
            return None
        return groups


@dataclass(frozen=True)
class SplitOutcome:
    chunks: list[TextChunk] = field(default_factory=list)
    strategy: str = "structural"


class SmartSplitter:
    """Split strategy chain: semantic (LLM) -> structural -> recursive guard.

    Semantic and structural units still pass through the recursive splitter,
    which merges tiny units and hard-splits oversized ones. The chosen
    strategy is recorded in chunk metadata as ``split_strategy``.
    """

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        guard: RecursiveTextSplitter | None = None,
        min_unit_chars: int = 80,
    ) -> None:
        self.llm_provider = llm_provider
        self.guard = guard or RecursiveTextSplitter()
        self.min_unit_chars = min_unit_chars

    async def split(self, text: str, metadata: dict[str, Any] | None = None) -> SplitOutcome:
        units: list[TextChunk] | None = None
        strategy = "structural"
        if self.llm_provider is not None:
            units = await SemanticLLMSplitter(self.llm_provider).split(text, metadata)
            if units is not None:
                strategy = "semantic"
        if units is None:
            units = StructuralTextSplitter().split(text, metadata)
        merged = self._merge_small(units)
        chunks: list[TextChunk] = []
        for unit in merged:
            tagged = {**unit.metadata, "split_strategy": strategy}
            if len(unit.content) > self.guard.chunk_size:
                chunks.extend(
                    TextChunk(content=piece.content, metadata={**piece.metadata, **tagged})
                    for piece in self.guard.split(unit.content, tagged)
                )
            else:
                chunks.append(TextChunk(content=unit.content, metadata=tagged))
        return SplitOutcome(chunks=chunks, strategy=strategy)

    def _merge_small(self, units: list[TextChunk]) -> list[TextChunk]:
        merged: list[TextChunk] = []
        for unit in units:
            if merged and len(unit.content) < self.min_unit_chars:
                previous = merged[-1]
                if len(previous.content) + len(unit.content) + 1 <= self.guard.chunk_size:
                    merged[-1] = TextChunk(
                        content=f"{previous.content}\n{unit.content}",
                        metadata=previous.metadata,
                    )
                    continue
            merged.append(unit)
        return merged
