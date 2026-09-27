import re

from app.providers.embedding import EmbeddingProvider
from app.rag.bm25 import BM25Retriever, get_shared_bm25_retriever
from app.rag.types import RetrievedChunk
from app.vectorstores.base import VectorStore

FILLER_QUERIES = {
    "1",
    "2",
    "3",
    "4",
    "5",
    "你好",
    "在吗",
    "嗨",
    "哈喽",
    "hello",
    "hi",
    "test",
    "测试",
}

STOP_TERMS = {
    "什么",
    "怎么",
    "为什么",
    "如何",
    "介绍",
    "总结",
    "问题",
    "经历",
    "项目经历",
}


def is_retrieval_worthy(query: str) -> bool:
    normalized = query.strip().lower()
    if not normalized or normalized in FILLER_QUERIES:
        return False
    if re.fullmatch(r"[\W_]+", normalized):
        return False
    if re.fullmatch(r"\d{1,2}", normalized):
        return False
    if len(normalized) == 1:
        return False
    return True


def extract_search_terms(query: str) -> list[str]:
    normalized = query.strip().lower()
    terms = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]{2,}", normalized)
    unique = []
    for term in terms:
        if term in STOP_TERMS or term in unique:
            continue
        unique.append(term)
    if not unique and normalized:
        unique.append(normalized)
    return unique[:5]


class RetrievalService:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        bm25_retriever: BM25Retriever | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self._bm25_retriever = bm25_retriever or get_shared_bm25_retriever()

    async def retrieve(
        self,
        query: str,
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        embeddings = await self.embedding_provider.embed([query])
        if not embeddings:
            return []
        return self.vector_store.query(embeddings[0], top_k=top_k, where=where)

    async def keyword_search(
        self,
        query: str,
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        terms = extract_search_terms(query)
        if not terms:
            return []
        return self.vector_store.keyword_search(terms, top_k=top_k, where=where)

    async def bm25_search(
        self,
        query: str,
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        """BM25 sparse retrieval over an in-memory index of the store's chunks.

        Falls back to the store's literal keyword search when the store
        cannot enumerate its chunks.
        """
        terms = extract_search_terms(query)
        if not terms:
            return []
        if hasattr(self.vector_store, "list_all_chunks"):
            return self._bm25_retriever.search(self.vector_store, query, top_k, where=where)
        return self.vector_store.keyword_search(terms, top_k=top_k, where=where)
