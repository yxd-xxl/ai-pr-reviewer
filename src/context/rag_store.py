"""RAG knowledge base — semantic search over team conventions, optional vector store."""

from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass
class RagDocument:
    source: str
    content: str
    chunk_index: int = 0


class RagStore:
    """Document store with keyword-based search (vector search optional)."""

    def __init__(self):
        self._documents: list[RagDocument] = []
        self._use_embeddings = False

        # Try loading sentence-transformers for semantic search
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._embeddings: list = []
            self._use_embeddings = True
        except ImportError:
            self._model = None
            self._embeddings = []

    def add_document(self, source: str, content: str, chunk_size: int = 500):
        """Add a document, chunking if too long."""
        if len(content) <= chunk_size:
            self._documents.append(RagDocument(source=source, content=content))
            if self._use_embeddings and self._model:
                self._embeddings.append(self._model.encode(content))
        else:
            # Chunk into overlapping pieces
            for i in range(0, len(content), chunk_size - 50):
                chunk = content[i:i + chunk_size]
                self._documents.append(RagDocument(
                    source=source, content=chunk, chunk_index=i // (chunk_size - 50),
                ))
                if self._use_embeddings and self._model:
                    self._embeddings.append(self._model.encode(chunk))

    def search(self, query: str, top_k: int = 5) -> list[RagDocument]:
        """Search for relevant documents. Uses embeddings if available, else keyword matching."""
        if not self._documents:
            return []

        if self._use_embeddings and self._embeddings and self._model:
            return self._semantic_search(query, top_k)
        return self._keyword_search(query, top_k)

    def _semantic_search(self, query: str, top_k: int) -> list[RagDocument]:
        """Cosine similarity search using embeddings."""
        import numpy as np
        query_vec = self._model.encode(query)
        scores = [
            float(np.dot(query_vec, doc_vec) /
                  (np.linalg.norm(query_vec) * np.linalg.norm(doc_vec)))
            for doc_vec in self._embeddings
        ]
        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: -x[1])
        return [self._documents[i] for i, _ in indexed[:top_k] if scores[i] > 0.3]

    def _keyword_search(self, query: str, top_k: int) -> list[RagDocument]:
        """Fallback: keyword similarity matching."""
        scored = []
        for i, doc in enumerate(self._documents):
            score = SequenceMatcher(None, query.lower(), doc.content.lower()[:500]).ratio()
            scored.append((i, score))
        scored.sort(key=lambda x: -x[1])
        return [self._documents[i] for i, s in scored[:top_k] if s > 0.1]

    def build_from_repo(self, conventions: list) -> "RagStore":
        """Build store from project conventions list."""
        for c in conventions:
            self.add_document(c.source, c.content)
        return self

    def __len__(self) -> int:
        return len(self._documents)
