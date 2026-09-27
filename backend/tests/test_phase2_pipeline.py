from pathlib import Path

import pytest

from app.rag import loader as loader_module
from app.rag.loader import LocalDocumentLoader
from app.rag.splitter import CharacterTextSplitter


def test_character_splitter_respects_size_and_overlap() -> None:
    splitter = CharacterTextSplitter(chunk_size=20, chunk_overlap=5)

    chunks = splitter.split("one two three four five six seven eight nine", {"page": 1})

    assert len(chunks) > 1
    assert all(len(chunk.content) <= 20 for chunk in chunks)
    assert all(chunk.metadata == {"page": 1} for chunk in chunks)


def test_pdf_loader_preserves_page_numbers(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakePage:
        def __init__(self, text: str) -> None:
            self.text = text

        def extract_text(self) -> str:
            return self.text

    class FakeReader:
        pages = [FakePage("page one"), FakePage("page two")]

    monkeypatch.setattr(loader_module, "PdfReader", lambda _: FakeReader())

    loaded = LocalDocumentLoader().load(Path("example.pdf"))

    assert [section.content for section in loaded.sections] == ["page one", "page two"]
    assert [section.metadata["page"] for section in loaded.sections] == [1, 2]
