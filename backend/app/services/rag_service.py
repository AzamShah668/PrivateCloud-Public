# =============================================================================
# backend/app/services/rag_service.py
# =============================================================================
# Retrieval-Augmented Generation (RAG) knowledge base for the ChatOps agent.
#
# This is the "retriever" half of the RAG pipeline. It implements the standard
# textbook flow, ported from the verventech-rag PDF lab:
#
#   INGEST  (admin uploads a doc):  extract -> chunk -> embed -> store
#   RETRIEVE (user asks a question): embed query -> vector similarity search
#
# The "generate" half lives in llm_agent.py: the retrieved chunks are handed to
# the SAME OpenRouter model the agent already uses, which writes the grounded
# answer. Embeddings run locally (all-MiniLM-L6-v2) because OpenRouter does not
# serve an embeddings endpoint.
#
# Design notes:
#   - Everything heavy (chromadb, sentence-transformers, torch) is imported
#     LAZILY on first use, so the API process still boots if those libs or the
#     embedding model are unavailable. `is_available()` reflects that state.
#   - The embedding model downloads (~80 MB) on first ingest/query and is cached
#     on disk (HF cache volume in Docker) so it only happens once.
# =============================================================================

import logging
import os
import re
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# --- Configuration -----------------------------------------------------------
# Where ChromaDB persists vectors. In Docker this is a mounted named volume so
# the index survives container restarts.
CHROMA_PATH = os.getenv("CHROMA_PATH", "./data/chroma")
COLLECTION_NAME = os.getenv("RAG_COLLECTION", "privatecloud_knowledge")
# Embeddings use ChromaDB's built-in default model (all-MiniLM-L6-v2, ONNX).
EMBED_MODEL = "all-MiniLM-L6-v2 (chroma default ONNX)"

# Chunking parameters — identical to the verventech_pdf_rag lab.
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# How many chunks to retrieve per query by default.
DEFAULT_TOP_K = 4


class RagError(Exception):
    """Raised when a knowledge-base operation fails (as opposed to simply
    finding no matching documents). Lets callers tell a real failure apart from
    an empty/zero-result search."""


class RagService:
    """
    Self-hosted vector knowledge base backed by ChromaDB.

    Thread-safe lazy initialization: the first call that needs the vector store
    triggers a one-time load of ChromaDB + the embedding model. If that load
    fails (missing deps, no network for the model download), the service stays
    in an "unavailable" state and callers degrade gracefully instead of the API
    crashing.
    """

    def __init__(self) -> None:
        self._client = None
        self._collection = None
        self._splitter = None
        self._init_error: Optional[str] = None
        self._initialized = False
        self._lock = threading.Lock()
        # Cache for stats(): (doc_count, sources_list). Avoids re-scanning every
        # chunk's metadata on each admin poll when nothing has changed.
        self._stats_cache: Optional[tuple] = None

    # -- Lifecycle ------------------------------------------------------------

    def _reset(self) -> None:
        """
        Drop the cached ChromaDB client/collection so the next operation rebuilds
        them from disk. Used to self-heal a stale in-memory index (e.g. when the
        on-disk store was written by another process and this client's cached
        HNSW segment is out of date).
        """
        with self._lock:
            self._client = None
            self._collection = None
            self._stats_cache = None

    def _ensure_ready(self) -> bool:
        """
        Lazily build the Chroma client, collection, and text splitter.

        Returns True if the vector store is ready to use, False otherwise.
        Safe to call repeatedly; the expensive work happens only once.
        """
        if self._collection is not None:
            return True

        with self._lock:
            if self._collection is not None:
                return True

            try:
                import chromadb
                from chromadb.utils import embedding_functions
                from langchain_text_splitters import RecursiveCharacterTextSplitter

                os.makedirs(CHROMA_PATH, exist_ok=True)

                self._client = chromadb.PersistentClient(path=CHROMA_PATH)
                # ChromaDB's built-in default embedder: all-MiniLM-L6-v2 as a
                # small ONNX model run via onnxruntime. Same model/quality as
                # SentenceTransformers but WITHOUT torch (~1.5-2.5 GB lighter).
                emb_fn = embedding_functions.DefaultEmbeddingFunction()
                self._collection = self._client.get_or_create_collection(
                    name=COLLECTION_NAME,
                    embedding_function=emb_fn,
                )
                self._splitter = RecursiveCharacterTextSplitter(
                    chunk_size=CHUNK_SIZE,
                    chunk_overlap=CHUNK_OVERLAP,
                    separators=["\n\n", "\n", ".", " "],
                )
                logger.info(
                    "RAG service ready (path=%s, collection=%s, model=%s)",
                    CHROMA_PATH,
                    COLLECTION_NAME,
                    EMBED_MODEL,
                )
            except Exception as exc:  # noqa: BLE001 — degrade, never crash the API
                self._init_error = str(exc)
                logger.error("RAG service failed to initialize: %s", exc, exc_info=True)
                self._collection = None
            finally:
                self._initialized = True

            return self._collection is not None

    def is_available(self) -> bool:
        """True if the vector store is usable (deps installed, model loaded)."""
        return self._ensure_ready()

    @property
    def init_error(self) -> Optional[str]:
        """Human-readable reason the service is unavailable, if any."""
        return self._init_error

    # -- Helpers --------------------------------------------------------------

    @staticmethod
    def _safe_id(source: str) -> str:
        """Turn a source name into an id-safe slug for chunk ids."""
        return re.sub(r"[^a-zA-Z0-9_.-]", "_", source).strip("_") or "doc"

    def _index_chunks(self, chunks: List[str], source: str) -> int:
        """
        Upsert a list of text chunks under a given source name.

        Uses upsert (idempotent) so re-ingesting the same source replaces its
        chunks instead of duplicating them. Stale chunks from a previous, longer
        version of the same source are removed first.
        """
        assert self._collection is not None  # guarded by callers
        slug = self._safe_id(source)

        # Remove any prior chunks for this source so re-ingest is clean.
        try:
            self._collection.delete(where={"source": source})
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not clear old chunks for %s: %s", source, exc)

        if not chunks:
            return 0

        self._collection.upsert(
            documents=chunks,
            ids=[f"{slug}_{i}" for i in range(len(chunks))],
            metadatas=[{"source": source, "chunk": i} for i in range(len(chunks))],
        )
        return len(chunks)

    # -- Ingestion ------------------------------------------------------------

    def ingest_text(self, text: str, source: str) -> Dict[str, Any]:
        """
        Chunk and index raw text under `source`.

        Returns {source, chunks_indexed, status}.
        """
        if not self._ensure_ready():
            raise RuntimeError(
                self._init_error or "Knowledge base is not available."
            )
        if not text or not text.strip():
            return {"source": source, "chunks_indexed": 0, "status": "empty"}

        chunks = self._splitter.split_text(text)
        count = self._index_chunks(chunks, source)
        logger.info("Indexed %d chunks from text source '%s'", count, source)
        return {"source": source, "chunks_indexed": count, "status": "indexed"}

    def ingest_pdf(self, file_bytes: bytes, source: str) -> Dict[str, Any]:
        """
        Extract text from PDF bytes, chunk, and index under `source`.

        Returns {source, chunks_indexed, pages, status}.
        """
        if not self._ensure_ready():
            raise RuntimeError(
                self._init_error or "Knowledge base is not available."
            )

        import io

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_bytes))
        parts: List[str] = []
        for page in reader.pages:
            extracted = page.extract_text() or ""
            if extracted:
                parts.append(extracted)
        full_text = "\n".join(parts)

        if not full_text.strip():
            # Scanned/image-only PDFs have no extractable text layer.
            return {
                "source": source,
                "chunks_indexed": 0,
                "pages": len(reader.pages),
                "status": "no_text",
            }

        chunks = self._splitter.split_text(full_text)
        count = self._index_chunks(chunks, source)
        logger.info(
            "Indexed %d chunks from PDF '%s' (%d pages)",
            count,
            source,
            len(reader.pages),
        )
        return {
            "source": source,
            "chunks_indexed": count,
            "pages": len(reader.pages),
            "status": "indexed",
        }

    # -- Retrieval ------------------------------------------------------------

    def _run_query(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """Execute one similarity query and shape the results. May raise."""
        # Asking for more results than exist makes some ChromaDB versions throw
        # an HNSW error; an empty collection cannot be searched at all.
        count = self._collection.count()
        if count == 0:
            return []
        n = min(max(1, top_k), count)

        results = self._collection.query(query_texts=[query], n_results=n)

        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        dists = (results.get("distances") or [[]])[0]

        matches: List[Dict[str, Any]] = []
        for i, content in enumerate(docs):
            meta = metas[i] if i < len(metas) else {}
            matches.append(
                {
                    "content": content,
                    "source": (meta or {}).get("source", "unknown"),
                    "distance": dists[i] if i < len(dists) else None,
                }
            )
        return matches

    def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        """
        Vector similarity search. Returns the top-k matching chunks as
        [{content, source, distance}], ordered best-first. Returns [] when the
        query is blank or the knowledge base is empty.

        Self-heals a stale in-memory index: if a query fails (e.g. the on-disk
        store was updated by another process), the client is reset and the query
        is retried once. Raises RagError only if it still fails — so callers can
        distinguish a real failure from a legitimate zero-result search.
        """
        if not query or not query.strip():
            return []
        if not self._ensure_ready():
            raise RagError(self._init_error or "Knowledge base is not available.")

        try:
            return self._run_query(query, top_k)
        except Exception as exc:  # noqa: BLE001 — first failure: try to self-heal
            logger.warning(
                "RAG query failed (%s); resetting client and retrying once.", exc
            )
            self._reset()
            if not self._ensure_ready():
                raise RagError(
                    self._init_error or "Knowledge base unavailable after reset."
                ) from exc
            try:
                return self._run_query(query, top_k)
            except Exception as exc2:  # noqa: BLE001 — still failing: real error
                logger.error("RAG query failed after retry: %s", exc2, exc_info=True)
                raise RagError(f"Knowledge base search failed: {exc2}") from exc2

    # -- Management -----------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return {available, doc_count, sources, error} for the admin UI."""
        if not self._ensure_ready():
            return {
                "available": False,
                "doc_count": 0,
                "sources": [],
                "error": self._init_error,
            }
        try:
            count = self._collection.count()
            # The admin UI polls this every ~30s. Scanning every chunk's metadata
            # each time is wasteful, so reuse the cached source breakdown while
            # the total chunk count is unchanged (the common case between polls).
            if self._stats_cache is not None and self._stats_cache[0] == count:
                sources = self._stats_cache[1]
            else:
                got = self._collection.get(include=["metadatas"])
                metas = got.get("metadatas") or []
                per_source: Dict[str, int] = {}
                for meta in metas:
                    src = (meta or {}).get("source", "unknown")
                    per_source[src] = per_source.get(src, 0) + 1
                sources = [
                    {"source": src, "chunks": n}
                    for src, n in sorted(per_source.items())
                ]
                self._stats_cache = (count, sources)
            return {
                "available": True,
                "doc_count": count,
                "sources": sources,
                "error": None,
            }
        except Exception as exc:  # noqa: BLE001
            logger.error("RAG stats failed: %s", exc, exc_info=True)
            return {
                "available": True,
                "doc_count": 0,
                "sources": [],
                "error": str(exc),
            }

    def delete_source(self, source: str) -> Dict[str, Any]:
        """Remove all chunks belonging to a single source document."""
        if not self._ensure_ready():
            raise RuntimeError(
                self._init_error or "Knowledge base is not available."
            )
        self._collection.delete(where={"source": source})
        logger.info("Deleted all chunks for source '%s'", source)
        return {"source": source, "status": "deleted"}


# Module-level singleton — one shared vector store for the whole process.
rag_service = RagService()
