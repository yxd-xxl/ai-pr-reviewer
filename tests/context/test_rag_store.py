"""Tests for RAG knowledge store."""

from src.context.rag_store import RagStore, RagDocument
from src.core.types import ProjectConvention


class TestRagDocument:
    def test_fields(self):
        d = RagDocument(source="CLAUDE.md", content="Use snake_case", chunk_index=0)
        assert d.source == "CLAUDE.md"


class TestRagStore:
    def test_add_and_search(self):
        store = RagStore()
        store.add_document("CLAUDE.md", "Use snake_case for Python functions.")
        store.add_document("CONTRIBUTING.md", "Write tests before implementation.")
        results = store.search("snake_case")
        assert len(results) >= 1

    def test_search_empty_store(self):
        store = RagStore()
        assert store.search("anything") == []

    def test_chunking_large_content(self):
        store = RagStore()
        store.add_document("big.md", "x" * 1200, chunk_size=500)
        assert len(store) >= 2  # should be chunked into 3 pieces

    def test_build_from_conventions(self):
        convs = [
            ProjectConvention(source=".claude/CLAUDE.md", type="coding_style",
                             content="Use type hints everywhere."),
            ProjectConvention(source="CONTRIBUTING.md", type="project_doc",
                             content="Always add tests for new features."),
        ]
        store = RagStore().build_from_repo(convs)
        assert len(store) >= 2

    def test_keyword_fallback(self):
        store = RagStore()
        store.add_document("rules.md", "All PRs must pass CI before merge.")
        store.add_document("style.md", "Maximum line length is 100 characters.")
        results = store.search("PRs CI merge")
        assert len(results) >= 1

    def test_len(self):
        store = RagStore()
        store.add_document("a", "content a")
        store.add_document("b", "content b")
        assert len(store) == 2
