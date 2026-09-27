import re

from rank_bm25 import BM25Plus

from app.rag.types import RetrievedChunk

_ALNUM_PATTERN = re.compile(r"[a-z0-9]+")
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def tokenize(text: str) -> list[str]:
    """Tokenizes mixed Chinese/English text without external segmenters.

    Alphanumeric runs stay whole; CJK text becomes unigrams plus bigrams so
    that multi-character business terms (e.g. 年费, 逾期) can match.
    """
    lowered = text.lower()
    tokens = _ALNUM_PATTERN.findall(lowered)
    cjk_chars = _CJK_PATTERN.findall(lowered)
    tokens.extend(cjk_chars)
    tokens.extend(
        first + second for first, second in zip(cjk_chars, cjk_chars[1:], strict=False)
    )
    return tokens


class BM25Retriever:
    """In-memory BM25 index over the chunks of a vector store.

    The index is rebuilt lazily whenever the underlying collection changes
    (name or chunk count), which covers document add/delete and index
    version switches. BM25Plus keeps IDF positive on small corpora, which
    BM25Okapi zeroes out.
    """

    def __init__(self) -> None:
        self._cache_key: tuple[object, int] | None = None
        self._records: list[RetrievedChunk] = []
        self._index: BM25Plus | None = None

    def invalidate(self) -> None:
        self._cache_key = None
        self._records = []
        self._index = None

    def search(
        self,
        store: object,
        query: str,
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        self._ensure_index(store)
        if self._index is None:
            return []
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self._index.get_scores(tokens)
        results: list[RetrievedChunk] = []
        for position in scores.argsort()[::-1]:
            score = float(scores[position])
            if score <= 0:
                break
            record = self._records[position]
            if where and any(
                record.metadata.get(key) != value for key, value in where.items()
            ):
                continue
            results.append(
                RetrievedChunk(
                    chunk_id=record.chunk_id,
                    document_id=record.document_id,
                    content=record.content,
                    score=score,
                    metadata=record.metadata,
                )
            )
            if len(results) >= top_k:
                break
        return results

    def _ensure_index(self, store: object) -> None:
        collection_name = getattr(store, "collection_name", None) or id(store)
        count = int(getattr(store, "count", lambda: 0)())
        key = (collection_name, count)
        if key == self._cache_key:
            return
        list_all = getattr(store, "list_all_chunks", None)
        records = list(list_all()) if callable(list_all) else []
        self._records = records
        self._index = (
            BM25Plus([tokenize(record.content) for record in records]) if records else None
        )
        self._cache_key = key


_shared_retriever = BM25Retriever()


def get_shared_bm25_retriever() -> BM25Retriever:
    return _shared_retriever
