from pathlib import Path
from typing import Any

import chromadb

from app.models.chunk import ChunkRecord
from app.rag.types import RetrievedChunk


class ChromaVectorStore:
    def __init__(
        self,
        persist_directory: Path,
        collection_name: str = "knowledge_chunks",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(persist_directory))
        collection_metadata = {"hnsw:space": "cosine", **(metadata or {})}
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata=collection_metadata,
        )

    @property
    def collection_name(self) -> str:
        return self.collection.name

    def count(self) -> int:
        return self.collection.count()

    def dimension(self) -> int | None:
        result = self.collection.get(limit=1, include=["embeddings"])
        embeddings = result.get("embeddings")
        if embeddings is None or len(embeddings) == 0:
            return None
        return len(embeddings[0])

    def add(self, records: list[ChunkRecord]) -> None:
        if not records:
            return
        embeddings = [record.embedding for record in records]
        if any(embedding is None for embedding in embeddings):
            raise ValueError("Every chunk must contain an embedding before it is stored.")
        self.collection.upsert(
            ids=[record.id for record in records],
            documents=[record.content for record in records],
            metadatas=[self._metadata(record) for record in records],
            embeddings=embeddings,
        )

    def get_chunk(self, chunk_id: str) -> ChunkRecord | None:
        result = self.collection.get(
            ids=[chunk_id],
            include=["documents", "metadatas"],
        )
        ids = result.get("ids", [])
        documents = result.get("documents", [])
        metadatas = result.get("metadatas", [])
        if not ids or not documents or not metadatas:
            return None
        metadata = dict(metadatas[0])
        return ChunkRecord(
            id=ids[0],
            document_id=str(metadata.get("document_id", "")),
            knowledge_base_id=str(metadata.get("knowledge_base_id", "")),
            content=documents[0],
            metadata=metadata,
        )

    def list_chunks(self, document_id: str) -> list[ChunkRecord]:
        result = self.collection.get(
            where={"document_id": document_id},
            include=["documents", "metadatas"],
        )
        records = []
        for chunk_id, document, metadata in zip(
            result.get("ids", []),
            result.get("documents", []),
            result.get("metadatas", []),
            strict=True,
        ):
            values = dict(metadata)
            records.append(
                ChunkRecord(
                    id=chunk_id,
                    document_id=str(values.get("document_id", "")),
                    knowledge_base_id=str(values.get("knowledge_base_id", "")),
                    content=document,
                    metadata=values,
                )
            )
        return sorted(
            records,
            key=lambda record: int(record.metadata.get("chunk_index", 0)),
        )

    def list_all_chunks(self) -> list[RetrievedChunk]:
        result = self.collection.get(
            include=["documents", "metadatas"],
        )
        records = []
        for chunk_id, document, metadata in zip(
            result.get("ids", []),
            result.get("documents", []),
            result.get("metadatas", []),
            strict=True,
        ):
            values = dict(metadata)
            records.append(
                RetrievedChunk(
                    chunk_id=chunk_id,
                    document_id=str(values.get("document_id", "")),
                    content=document,
                    score=0.0,
                    metadata=values,
                )
            )
        return records

    def keyword_search(
        self,
        terms: list[str],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        matches: dict[str, dict[str, object]] = {}
        for term in terms:
            result = self.collection.get(
                where=where,
                where_document={"$contains": term},
                include=["documents", "metadatas"],
                limit=max(top_k * 2, 10),
            )
            for chunk_id, document, metadata in zip(
                result.get("ids", []),
                result.get("documents", []),
                result.get("metadatas", []),
                strict=True,
            ):
                values = dict(metadata)
                entry = matches.setdefault(
                    chunk_id,
                    {
                        "document": document,
                        "metadata": values,
                        "count": 0,
                    },
                )
                entry["count"] = int(entry["count"]) + 1

        results = [
            RetrievedChunk(
                chunk_id=chunk_id,
                document_id=str(entry["metadata"].get("document_id", "")),
                content=str(entry["document"]),
                score=min(1.0, 0.72 + 0.18 * int(entry["count"])),
                metadata=dict(entry["metadata"]),
            )
            for chunk_id, entry in matches.items()
        ]
        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]

    def delete_document(self, document_id: str) -> None:
        self.collection.delete(where={"document_id": document_id})

    def query(
        self,
        embedding: list[float],
        top_k: int,
        where: dict[str, object] | None = None,
    ) -> list[RetrievedChunk]:
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            RetrievedChunk(
                chunk_id=chunk_id,
                document_id=str(metadata.get("document_id", "")),
                content=document,
                score=1.0 - float(distance),
                metadata=dict(metadata),
            )
            for chunk_id, document, metadata, distance in zip(
                ids, documents, metadatas, distances, strict=True
            )
        ]

    @staticmethod
    def _metadata(record: ChunkRecord) -> dict[str, Any]:
        return {
            key: value
            for key, value in {
                "document_id": record.document_id,
                "knowledge_base_id": record.knowledge_base_id,
                **record.metadata,
            }.items()
            if value is not None
        }
