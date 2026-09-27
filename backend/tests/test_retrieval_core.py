import pytest

from app.models.chunk import ChunkRecord
from app.providers.base import ChatResult
from app.rag.bm25 import BM25Retriever, tokenize
from app.rag.router import RelevanceRouter
from app.rag.splitter import RecursiveTextSplitter
from app.rag.types import RetrievedChunk, RouteMode
from app.services.rag_service import RAGService
from app.services.retrieval_service import RetrievalService
from tests.fakes import FakeEmbeddingProvider, InMemoryVectorStore


def make_record(
    chunk_id: str,
    content: str,
    document_id: str = "doc-1",
    knowledge_base_id: str = "kb-1",
    chunk_index: int = 0,
) -> ChunkRecord:
    return ChunkRecord(
        id=chunk_id,
        document_id=document_id,
        knowledge_base_id=knowledge_base_id,
        content=content,
        metadata={"filename": f"{document_id}.txt", "chunk_index": chunk_index},
        embedding=[0.1, 0.2],
    )


class AnsweringLLM:
    async def chat(self, messages: object) -> ChatResult:
        del messages
        return ChatResult(content="回答", model="fake")


class TestRecursiveTextSplitter:
    def test_prefers_sentence_boundaries(self) -> None:
        splitter = RecursiveTextSplitter(chunk_size=30, chunk_overlap=0)
        text = "第一条规则内容。第二条规则内容。第三条规则内容。第四条规则内容。"

        chunks = splitter.split(text)

        assert len(chunks) > 1
        assert all(chunk.content.endswith("。") for chunk in chunks[:-1])

    def test_preserves_newlines(self) -> None:
        splitter = RecursiveTextSplitter(chunk_size=800, chunk_overlap=0)
        text = "第一节 申请条件\n申请人需年满十八周岁。\n\n第二节 申请材料\n身份证明与收入证明。"

        chunks = splitter.split(text)

        assert len(chunks) == 1
        assert "\n\n" in chunks[0].content

    def test_hard_splits_when_no_boundary(self) -> None:
        splitter = RecursiveTextSplitter(chunk_size=10, chunk_overlap=0)
        text = "啊" * 25

        chunks = splitter.split(text)

        assert [len(chunk.content) for chunk in chunks] == [10, 10, 5]

    def test_overlap_carries_previous_tail(self) -> None:
        splitter = RecursiveTextSplitter(chunk_size=10, chunk_overlap=4)
        text = "第一句短。第二句也短。第三句同样短。第四句收尾。"

        chunks = splitter.split(text)

        assert len(chunks) > 1
        assert chunks[1].content.startswith(chunks[0].content[-4:])

    def test_empty_text_returns_no_chunks(self) -> None:
        splitter = RecursiveTextSplitter()

        assert splitter.split("   \n  ") == []


class TestTokenize:
    def test_chinese_bigrams_and_unigrams(self) -> None:
        tokens = tokenize("年费")

        assert "年" in tokens
        assert "费" in tokens
        assert "年费" in tokens

    def test_alnum_terms_stay_whole(self) -> None:
        assert "618" in tokenize("京东618大促")


class TestBM25Retriever:
    def build_store(self) -> InMemoryVectorStore:
        store = InMemoryVectorStore()
        store.add(
            [
                make_record("c1", "信用卡年费减免规则：刷卡满五次免次年年费。"),
                make_record("c2", "积分可通过消费累积，积分可兑换礼品。", chunk_index=1),
                make_record("c3", "账单日为每月五日，还款日为账单日后二十天。", chunk_index=2),
            ]
        )
        return store

    def test_chinese_business_term_ranks_first(self) -> None:
        retriever = BM25Retriever()

        results = retriever.search(self.build_store(), "年费怎么减免", 3)

        assert results
        assert "年费" in results[0].content

    def test_short_numeric_keyword_hits(self) -> None:
        store = InMemoryVectorStore()
        store.add(
            [
                make_record("c1", "京东618大促电商项目"),
                make_record("c2", "无关的其他内容记录", chunk_index=1),
            ]
        )

        results = BM25Retriever().search(store, "618", 2)

        assert results
        assert results[0].chunk_id == "c1"

    def test_where_filter_scopes_results(self) -> None:
        store = self.build_store()
        store.add([make_record("c9", "另一知识库的年费说明。", knowledge_base_id="kb-2")])

        results = BM25Retriever().search(store, "年费", 5, where={"knowledge_base_id": "kb-2"})

        assert [result.chunk_id for result in results] == ["c9"]

    def test_index_rebuilds_after_add(self) -> None:
        store = self.build_store()
        retriever = BM25Retriever()
        first = retriever.search(store, "年费", 3)
        store.add([make_record("c4", "年费补充：白金卡年费另行规定。", chunk_index=3)])

        second = retriever.search(store, "年费", 10)

        assert len(second) == len(first) + 1


class LowVectorBm25Store:
    collection_name = "low-vector-bm25"

    def __init__(self) -> None:
        self.record = make_record("resume:0", "京东618大促电商项目", document_id="resume")

    def count(self) -> int:
        return 1

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: object = None,
    ) -> list[RetrievedChunk]:
        del embedding, top_k, where
        return [
            RetrievedChunk(
                chunk_id=self.record.id,
                document_id=self.record.document_id,
                content=self.record.content,
                score=0.15,
                metadata=self.record.metadata,
            )
        ]

    def list_all_chunks(self) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                chunk_id=self.record.id,
                document_id=self.record.document_id,
                content=self.record.content,
                score=0.0,
                metadata=self.record.metadata,
            )
        ]


@pytest.mark.asyncio
async def test_bm25_rescues_exact_keyword_with_low_vector_score() -> None:
    service = RAGService(
        retrieval_service=RetrievalService(
            FakeEmbeddingProvider(),
            LowVectorBm25Store(),  # type: ignore[arg-type]
            bm25_retriever=BM25Retriever(),
        ),
        llm_provider=AnsweringLLM(),  # type: ignore[arg-type]
        router=RelevanceRouter(0.5),
    )

    answer = await service.answer("618")

    assert answer.route is RouteMode.KNOWLEDGE
    assert answer.citations[0].score >= 0.5


@pytest.mark.asyncio
async def test_vector_only_result_keeps_vector_score_for_routing() -> None:
    store = InMemoryVectorStore()
    store.add([make_record("c1", "完全由向量命中的内容，与查询词没有字面重叠")])
    service = RAGService(
        retrieval_service=RetrievalService(
            FakeEmbeddingProvider(),
            store,
            bm25_retriever=BM25Retriever(),
        ),
        llm_provider=AnsweringLLM(),  # type: ignore[arg-type]
        router=RelevanceRouter(0.5),
    )

    answer = await service.answer("向量检索测试问题")

    assert answer.route is RouteMode.KNOWLEDGE
    assert answer.citations[0].score == 1.0
