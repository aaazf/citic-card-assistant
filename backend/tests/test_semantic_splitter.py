import pytest

from app.providers.base import ChatResult
from app.rag.semantic import SmartSplitter, StructuralTextSplitter
from app.rag.splitter import RecursiveTextSplitter


class StubLLM:
    def __init__(self, content: str | None = None, raises: bool = False) -> None:
        self.content = content or "[[1, 2], [3, 4]]"
        self.raises = raises
        self.calls = 0

    async def chat(self, messages: object) -> ChatResult:
        self.calls += 1
        if self.raises:
            raise RuntimeError("llm unavailable")
        return ChatResult(content=self.content, model="stub")


CONTRACT_TEXT = (
    "第一条 年费标准\n白金卡主卡每年人民币两千元。\n附属卡每年人民币一千元。\n"
    "第二条 免年费政策\n刷卡满五次免次年年费。\n"
    "第三条 账单与还款\n账单日为每月五日。\n还款日为账单日后二十天。\n"
    "第四条 逾期责任\n逾期按日利率万分之五计息。\n"
)


class TestStructuralTextSplitter:
    def test_splits_on_clause_anchors(self) -> None:
        chunks = StructuralTextSplitter().split(CONTRACT_TEXT)

        assert len(chunks) == 4
        assert chunks[0].content.startswith("第一条")
        assert "还款日为账单日后二十天。" in chunks[2].content

    def test_markdown_headings_start_new_units(self) -> None:
        text = "# 申请条件\n年满十八周岁。\n# 申请材料\n身份证明。\n收入证明。"

        chunks = StructuralTextSplitter().split(text)

        assert [chunk.content.split("\n")[0] for chunk in chunks] == ["# 申请条件", "# 申请材料"]


class TestSmartSplitter:
    @pytest.mark.asyncio
    async def test_semantic_groups_paragraphs(self) -> None:
        splitter = SmartSplitter(llm_provider=StubLLM("[[1, 2], [3, 4]]"), min_unit_chars=0)
        text = "段落一内容。\n段落二内容。\n段落三内容。\n段落四内容。"

        outcome = await splitter.split(text)

        assert outcome.strategy == "semantic"
        assert [chunk.content for chunk in outcome.chunks] == [
            "段落一内容。\n段落二内容。",
            "段落三内容。\n段落四内容。",
        ]
        assert all(chunk.metadata["split_strategy"] == "semantic" for chunk in outcome.chunks)

    @pytest.mark.asyncio
    async def test_falls_back_on_invalid_json(self) -> None:
        splitter = SmartSplitter(llm_provider=StubLLM("无法分组"))

        outcome = await splitter.split(CONTRACT_TEXT)

        assert outcome.strategy == "structural"
        assert outcome.chunks

    @pytest.mark.asyncio
    async def test_falls_back_on_incomplete_coverage(self) -> None:
        splitter = SmartSplitter(llm_provider=StubLLM("[[1, 2]]"))

        outcome = await splitter.split(CONTRACT_TEXT)

        assert outcome.strategy == "structural"

    @pytest.mark.asyncio
    async def test_falls_back_when_llm_raises(self) -> None:
        splitter = SmartSplitter(llm_provider=StubLLM(raises=True))

        outcome = await splitter.split(CONTRACT_TEXT)

        assert outcome.strategy == "structural"
        assert outcome.chunks

    @pytest.mark.asyncio
    async def test_no_llm_uses_structural_without_calling(self) -> None:
        splitter = SmartSplitter(llm_provider=None, min_unit_chars=0)

        outcome = await splitter.split(CONTRACT_TEXT)

        assert outcome.strategy == "structural"
        assert len(outcome.chunks) == 4

    @pytest.mark.asyncio
    async def test_guard_splits_oversized_units(self) -> None:
        guard = RecursiveTextSplitter(chunk_size=20, chunk_overlap=0)
        splitter = SmartSplitter(
            llm_provider=StubLLM("[[1, 4]]"),
            guard=guard,
            min_unit_chars=0,
        )
        text = "一234567890。\n二234567890。\n三234567890。\n四234567890。"

        outcome = await splitter.split(text)

        assert outcome.strategy == "semantic"
        assert len(outcome.chunks) > 1
        assert all(len(chunk.content) <= 20 for chunk in outcome.chunks)

    @pytest.mark.asyncio
    async def test_tiny_units_merge_with_previous(self) -> None:
        splitter = SmartSplitter(llm_provider=StubLLM("[[1, 1], [2, 3]]"), min_unit_chars=80)
        text = (
            "附注。\n"
            "这是一条足够长的业务说明内容，用来验证过短的语义单元会被合并到前一个单元之中。\n"
            "补充说明文字。"
        )

        outcome = await splitter.split(text)

        assert outcome.strategy == "semantic"
        assert len(outcome.chunks) == 1
        assert outcome.chunks[0].content.startswith("附注。")
