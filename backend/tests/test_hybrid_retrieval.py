import pytest

from app.providers.base import ChatResult
from app.rag.router import RelevanceRouter
from app.rag.types import RetrievedChunk, RouteMode
from app.services.rag_service import RAGService
from app.services.retrieval_service import (
    RetrievalService,
    extract_search_terms,
    is_retrieval_worthy,
)
from tests.fakes import FakeEmbeddingProvider


class LowVectorExactKeywordStore:
    def __init__(self) -> None:
        self.result = RetrievedChunk(
            chunk_id="resume:0",
            document_id="resume",
            content="京东618大促电商项目",
            score=0.15,
            metadata={"filename": "resume.pdf", "chunk_index": 0},
        )

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: object = None,
    ) -> list[RetrievedChunk]:
        del embedding, top_k, where
        return [self.result]

    def keyword_search(
        self,
        terms: list[str],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        del terms, top_k
        return [
            RetrievedChunk(
                chunk_id=self.result.chunk_id,
                document_id=self.result.document_id,
                content=self.result.content,
                score=0.9,
                metadata=self.result.metadata,
            )
        ]


class AnsweringLLM:
    async def chat(self, messages: object) -> ChatResult:
        del messages
        return ChatResult(content="京东 618 项目回答", model="fake")


class NoopReranker:
    async def rerank(
        self,
        query: str,
        results: list[RetrievedChunk],
        top_k: int,
    ) -> list[RetrievedChunk]:
        del query, top_k
        return results


def test_search_terms_keep_important_numeric_keyword() -> None:
    assert extract_search_terms("618项目经历") == ["618"]


def test_short_queries_are_not_retrieved() -> None:
    assert is_retrieval_worthy("1") is False
    assert is_retrieval_worthy("你好") is False
    assert is_retrieval_worthy("618") is True
    assert is_retrieval_worthy("AI") is True


@pytest.mark.asyncio
async def test_exact_keyword_is_merged_even_when_vector_score_is_low() -> None:
    store = LowVectorExactKeywordStore()
    service = RAGService(
        retrieval_service=RetrievalService(FakeEmbeddingProvider(), store),  # type: ignore[arg-type]
        llm_provider=AnsweringLLM(),  # type: ignore[arg-type]
        router=RelevanceRouter(0.5),
        reranker=NoopReranker(),  # type: ignore[arg-type]
    )

    answer = await service.answer("618")

    assert answer.route is RouteMode.KNOWLEDGE
    assert answer.citations[0].score == 0.9
