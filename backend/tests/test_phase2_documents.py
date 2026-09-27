
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import ProviderConfigurationError
from app.main import create_app
from tests.fakes import InMemoryVectorStore


def create_knowledge_base(client: TestClient) -> str:
    response = client.post("/api/v1/knowledge", json={"name": "Phase 2"})
    assert response.status_code == 201
    return response.json()["id"]


def test_markdown_upload_is_chunked_embedded_and_stored(
    client: TestClient,
    vector_store: InMemoryVectorStore,
) -> None:
    knowledge_base_id = create_knowledge_base(client)
    content = ("RAG search uses vector similarity. " * 80).encode()

    upload = client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("notes.md", content, "text/markdown")},
    )

    assert upload.status_code == 202
    documents = client.get(
        "/api/v1/documents",
        params={"knowledge_base_id": knowledge_base_id},
    ).json()
    assert len(documents) == 1
    assert documents[0]["status"] == "ready"
    assert documents[0]["chunk_count"] > 1
    assert len(vector_store.records) == documents[0]["chunk_count"]


def test_upload_rejects_unsupported_file_type(client: TestClient) -> None:
    knowledge_base_id = create_knowledge_base(client)

    response = client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("notes.csv", b"a,b", "text/csv")},
    )

    assert response.status_code == 400


def make_epub() -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0"?>
            <container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
              <rootfiles>
                <rootfile full-path="EPUB/content.opf" media-type="application/oebps-package+xml"/>
              </rootfiles>
            </container>""",
        )
        archive.writestr(
            "EPUB/content.opf",
            """<?xml version="1.0" encoding="UTF-8"?>
            <package xmlns="http://www.idpf.org/2007/opf" version="3.0">
              <manifest>
                <item id="chapter-1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
                <item id="chapter-2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
              </manifest>
              <spine>
                <itemref idref="chapter-1"/>
                <itemref idref="chapter-2"/>
              </spine>
            </package>""",
        )
        archive.writestr(
            "EPUB/chapter1.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml"><body>
            <h1>第一章 起点</h1><p>智能体由模型、工具和记忆组成。</p>
            </body></html>""",
        )
        archive.writestr(
            "EPUB/chapter2.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml"><body>
            <h1>第二章 工作流</h1><p>工作流负责编排多个执行步骤。</p>
            </body></html>""",
        )
    return output.getvalue()


def test_epub_upload_preserves_reading_order_and_chapter_metadata(
    client: TestClient,
    vector_store: InMemoryVectorStore,
) -> None:
    knowledge_base_id = create_knowledge_base(client)

    upload = client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("agents.epub", make_epub(), "application/epub+zip")},
    )

    assert upload.status_code == 202
    document = client.get(f"/api/v1/documents/{upload.json()['id']}").json()
    assert document["status"] == "ready"
    chunks = sorted(
        vector_store.records.values(),
        key=lambda record: int(record.metadata["chunk_index"]),
    )
    assert "第一章 起点" in chunks[0].content
    assert "第二章 工作流" in chunks[1].content
    assert chunks[0].metadata["source_type"] == "epub"
    assert chunks[0].metadata["chapter_title"] == "第一章 起点"


def test_delete_document_removes_file_and_vectors(
    client: TestClient,
    test_settings: Settings,
    vector_store: InMemoryVectorStore,
) -> None:
    knowledge_base_id = create_knowledge_base(client)
    upload = client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("notes.txt", b"local knowledge", "text/plain")},
    )
    document_id = upload.json()["id"]
    stored_files = list((test_settings.data_dir / "documents").rglob("*.txt"))
    assert len(stored_files) == 1
    assert stored_files[0].name == f"{document_id}.txt"

    deleted = client.delete(f"/api/v1/documents/{document_id}")

    assert deleted.status_code == 200
    assert vector_store.records == {}
    assert list((test_settings.data_dir / "documents").rglob("*.txt")) == []


def test_missing_embedding_provider_marks_document_failed(
    test_settings: Settings,
    vector_store: InMemoryVectorStore,
) -> None:
    def unavailable(_: object) -> None:
        raise ProviderConfigurationError("Embedding provider is not configured.")

    app: FastAPI = create_app(
        test_settings,
        vector_store=vector_store,
        embedding_provider_factory=unavailable,
    )
    with TestClient(app) as client:
        knowledge_base_id = create_knowledge_base(client)
        client.post(
            "/api/v1/documents/upload",
            data={"knowledge_base_id": knowledge_base_id},
            files={"file": ("notes.txt", b"content", "text/plain")},
        )
        document = client.get("/api/v1/documents").json()[0]

    assert document["status"] == "failed"
    assert document["error_message"] == "Embedding provider is not configured."

def test_delete_knowledge_base_cleans_documents_and_vectors(
    client: TestClient,
    test_settings: Settings,
    vector_store: InMemoryVectorStore,
) -> None:
    knowledge_base_id = create_knowledge_base(client)
    client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("notes.txt", b"content", "text/plain")},
    )

    response = client.delete(f"/api/v1/knowledge/{knowledge_base_id}")

    assert response.status_code == 200
    assert client.get("/api/v1/documents").json() == []
    assert vector_store.records == {}
    assert list((test_settings.data_dir / "documents").rglob("*.txt")) == []


def test_document_detail_content_and_chunks(client: TestClient) -> None:
    knowledge_base_id = create_knowledge_base(client)
    uploaded = client.post(
        "/api/v1/documents/upload",
        data={"knowledge_base_id": knowledge_base_id},
        files={"file": ("detail.txt", "预览原文内容".encode(), "text/plain")},
    ).json()

    detail = client.get(f"/api/v1/documents/{uploaded['id']}")
    content = client.get(f"/api/v1/documents/{uploaded['id']}/content")
    chunks = client.get(f"/api/v1/documents/{uploaded['id']}/chunks")

    assert detail.status_code == 200
    assert detail.json()["filename"] == "detail.txt"
    assert content.status_code == 200
    assert content.content.decode() == "预览原文内容"
    assert chunks.status_code == 200
    assert chunks.json()[0]["content"] == "预览原文内容"
    assert chunks.json()[0]["metadata"]["chunk_index"] == 0


def test_missing_document_detail_returns_not_found(client: TestClient) -> None:
    assert client.get("/api/v1/documents/missing").status_code == 404
    assert client.get("/api/v1/documents/missing/content").status_code == 404
    assert client.get("/api/v1/documents/missing/chunks").status_code == 404
