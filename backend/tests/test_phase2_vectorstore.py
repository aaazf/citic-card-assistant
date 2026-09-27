from pathlib import Path

from app.models.chunk import ChunkRecord
from app.vectorstores.chroma import ChromaVectorStore


def test_chroma_add_query_and_delete(tmp_path: Path) -> None:
    store = ChromaVectorStore(tmp_path / "chroma")
    records = [
        ChunkRecord(
            id="doc:0",
            document_id="doc",
            knowledge_base_id="kb",
            content="vector databases store embeddings and 618 promotion data",
            metadata={"filename": "notes.md", "chunk_index": 0},
            embedding=[1.0, 0.0, 0.0],
        ),
        ChunkRecord(
            id="doc:1",
            document_id="doc",
            knowledge_base_id="kb",
            content="unrelated content",
            metadata={"filename": "notes.md", "chunk_index": 1},
            embedding=[0.0, 1.0, 0.0],
        ),
    ]

    store.add(records)
    results = store.query([1.0, 0.0, 0.0], top_k=1)
    assert results[0].chunk_id == "doc:0"
    assert results[0].metadata["filename"] == "notes.md"
    stored = store.get_chunk("doc:0")
    assert stored is not None
    assert stored.content == "vector databases store embeddings and 618 promotion data"
    chunks = store.list_chunks("doc")
    assert [chunk.metadata["chunk_index"] for chunk in chunks] == [0, 1]
    keyword_results = store.keyword_search(["618"], top_k=3)
    assert keyword_results[0].chunk_id == "doc:0"
    assert round(keyword_results[0].score, 2) == 0.9

    store.delete_document("doc")
    assert store.query([1.0, 0.0, 0.0], top_k=2) == []

