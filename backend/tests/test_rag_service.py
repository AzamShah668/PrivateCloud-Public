"""Unit tests for the RAG knowledge-base service.

The heavy vector layer (ChromaDB + sentence-transformers) is mocked, so these
tests run without those dependencies installed — exactly the lazy-init contract
rag_service is built around.
"""

from unittest.mock import MagicMock

import pytest

from app.services.rag_service import RagError, RagService


def _ready_service(collection: MagicMock) -> RagService:
    """Build a RagService that is already 'initialized' with a fake collection."""
    svc = RagService()
    svc._initialized = True
    svc._collection = collection
    # Non-zero count by default so search() does not short-circuit as "empty".
    if not isinstance(collection.count.return_value, int):
        collection.count.return_value = 100
    # Minimal splitter stub: split on double-newline so tests are deterministic.
    splitter = MagicMock()
    splitter.split_text.side_effect = lambda text: [
        p for p in text.split("\n\n") if p.strip()
    ]
    svc._splitter = splitter
    return svc


# --- _safe_id ----------------------------------------------------------------

def test_safe_id_sanitizes_unsafe_characters():
    assert RagService._safe_id("my doc!.pdf") == "my_doc_.pdf"


def test_safe_id_falls_back_to_doc_for_empty():
    assert RagService._safe_id("///") == "doc"


# --- availability / degradation ---------------------------------------------

def test_search_raises_when_unavailable(monkeypatch):
    svc = RagService()
    monkeypatch.setattr(svc, "_ensure_ready", lambda: False)
    svc._init_error = "deps missing"
    with pytest.raises(RagError, match="deps missing"):
        svc.search("anything")


def test_ingest_text_raises_when_unavailable(monkeypatch):
    svc = RagService()
    monkeypatch.setattr(svc, "_ensure_ready", lambda: False)
    svc._init_error = "deps missing"
    with pytest.raises(RuntimeError, match="deps missing"):
        svc.ingest_text("hello", source="x")


def test_stats_reports_unavailable(monkeypatch):
    svc = RagService()
    monkeypatch.setattr(svc, "_ensure_ready", lambda: False)
    svc._init_error = "boom"
    stats = svc.stats()
    assert stats["available"] is False
    assert stats["doc_count"] == 0
    assert stats["error"] == "boom"


# --- ingestion ---------------------------------------------------------------

def test_ingest_text_chunks_and_upserts():
    collection = MagicMock()
    svc = _ready_service(collection)

    result = svc.ingest_text("chunk one\n\nchunk two", source="notes.txt")

    assert result == {"source": "notes.txt", "chunks_indexed": 2, "status": "indexed"}
    # Old chunks cleared before re-indexing (idempotent ingest).
    collection.delete.assert_called_once_with(where={"source": "notes.txt"})
    upsert_kwargs = collection.upsert.call_args.kwargs
    assert upsert_kwargs["documents"] == ["chunk one", "chunk two"]
    assert upsert_kwargs["ids"] == ["notes.txt_0", "notes.txt_1"]
    assert upsert_kwargs["metadatas"][0] == {"source": "notes.txt", "chunk": 0}


def test_ingest_text_empty_returns_empty_status():
    collection = MagicMock()
    svc = _ready_service(collection)
    result = svc.ingest_text("   ", source="blank")
    assert result["status"] == "empty"
    assert result["chunks_indexed"] == 0
    collection.upsert.assert_not_called()


# --- retrieval ---------------------------------------------------------------

def test_search_maps_chroma_results_to_matches():
    collection = MagicMock()
    collection.query.return_value = {
        "documents": [["doc a", "doc b"]],
        "metadatas": [[{"source": "guide.pdf"}, {"source": "faq.pdf"}]],
        "distances": [[0.1, 0.42]],
    }
    svc = _ready_service(collection)

    matches = svc.search("how do I reset?", top_k=2)

    assert matches == [
        {"content": "doc a", "source": "guide.pdf", "distance": 0.1},
        {"content": "doc b", "source": "faq.pdf", "distance": 0.42},
    ]
    collection.query.assert_called_once_with(query_texts=["how do I reset?"], n_results=2)


def test_search_blank_query_returns_empty():
    collection = MagicMock()
    svc = _ready_service(collection)
    assert svc.search("   ") == []
    collection.query.assert_not_called()


def test_search_empty_collection_returns_empty():
    collection = MagicMock()
    collection.count.return_value = 0
    svc = _ready_service(collection)
    assert svc.search("q") == []
    collection.query.assert_not_called()


def test_search_self_heals_and_retries_once(monkeypatch):
    svc = RagService()
    monkeypatch.setattr(svc, "_ensure_ready", lambda: True)
    reset_calls = {"n": 0}
    monkeypatch.setattr(svc, "_reset", lambda: reset_calls.__setitem__("n", reset_calls["n"] + 1))

    attempts = {"n": 0}

    def flaky(_query, _top_k):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("hnsw segment reader: Nothing found on disk")
        return [{"content": "ok", "source": "s", "distance": 0.1}]

    monkeypatch.setattr(svc, "_run_query", flaky)

    out = svc.search("q")
    assert out and out[0]["content"] == "ok"
    assert attempts["n"] == 2  # failed once, retried, succeeded
    assert reset_calls["n"] == 1  # client was reset between attempts


def test_search_raises_on_persistent_failure(monkeypatch):
    svc = RagService()
    monkeypatch.setattr(svc, "_ensure_ready", lambda: True)
    monkeypatch.setattr(svc, "_reset", lambda: None)

    def always_fail(_query, _top_k):
        raise RuntimeError("boom")

    monkeypatch.setattr(svc, "_run_query", always_fail)
    with pytest.raises(RagError, match="boom"):
        svc.search("q")


# --- management --------------------------------------------------------------

def test_delete_source_delegates_to_collection():
    collection = MagicMock()
    svc = _ready_service(collection)
    result = svc.delete_source("guide.pdf")
    assert result == {"source": "guide.pdf", "status": "deleted"}
    collection.delete.assert_called_once_with(where={"source": "guide.pdf"})
