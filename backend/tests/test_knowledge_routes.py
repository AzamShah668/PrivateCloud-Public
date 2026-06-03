"""Tests for the admin-only RAG knowledge-base routes.

Verifies admin authorization and that handlers delegate to rag_service. The
service itself is mocked so no vector DB is required.
"""

from unittest.mock import patch


def test_status_requires_admin(client, user_headers):
    """Non-admin users must be rejected with 403."""
    resp = client.get("/admin/knowledge/status", headers=user_headers)
    assert resp.status_code == 403


def test_status_requires_auth(client):
    """Unauthenticated requests are rejected."""
    resp = client.get("/admin/knowledge/status")
    assert resp.status_code == 401


def test_status_returns_stats_for_admin(client, admin_headers):
    fake_stats = {
        "available": True,
        "doc_count": 3,
        "sources": [{"source": "guide.pdf", "chunks": 3}],
        "error": None,
    }
    with patch("app.routes.knowledge_routes.rag_service.stats", return_value=fake_stats):
        resp = client.get("/admin/knowledge/status", headers=admin_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["available"] is True
    assert body["doc_count"] == 3
    assert body["sources"][0]["source"] == "guide.pdf"


def test_upload_text_indexes_for_admin(client, admin_headers):
    fake_result = {"source": "notes", "chunks_indexed": 2, "status": "indexed"}
    with patch(
        "app.routes.knowledge_routes.rag_service.ingest_text",
        return_value=fake_result,
    ) as mock_ingest:
        resp = client.post(
            "/admin/knowledge/upload-text",
            headers=admin_headers,
            json={"source": "notes", "text": "hello world"},
        )
    assert resp.status_code == 201
    assert resp.json()["chunks_indexed"] == 2
    mock_ingest.assert_called_once()


def test_upload_text_blocked_for_user(client, user_headers):
    resp = client.post(
        "/admin/knowledge/upload-text",
        headers=user_headers,
        json={"source": "notes", "text": "hello"},
    )
    assert resp.status_code == 403


def test_upload_rejects_non_pdf(client, admin_headers):
    resp = client.post(
        "/admin/knowledge/upload",
        headers=admin_headers,
        files={"file": ("notes.txt", b"plain text", "text/plain")},
    )
    assert resp.status_code == 400


def test_upload_pdf_indexes(client, admin_headers):
    fake_result = {
        "source": "guide.pdf",
        "chunks_indexed": 5,
        "pages": 2,
        "status": "indexed",
    }
    with patch(
        "app.routes.knowledge_routes.rag_service.ingest_pdf",
        return_value=fake_result,
    ) as mock_ingest:
        resp = client.post(
            "/admin/knowledge/upload",
            headers=admin_headers,
            files={"file": ("guide.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
    assert resp.status_code == 201
    assert resp.json()["chunks_indexed"] == 5
    mock_ingest.assert_called_once()


def test_upload_service_unavailable_returns_503(client, admin_headers):
    with patch(
        "app.routes.knowledge_routes.rag_service.ingest_pdf",
        side_effect=RuntimeError("model still downloading"),
    ):
        resp = client.post(
            "/admin/knowledge/upload",
            headers=admin_headers,
            files={"file": ("guide.pdf", b"%PDF-1.4 fake", "application/pdf")},
        )
    assert resp.status_code == 503


def test_delete_source_for_admin(client, admin_headers):
    fake_result = {"source": "guide.pdf", "status": "deleted"}
    with patch(
        "app.routes.knowledge_routes.rag_service.delete_source",
        return_value=fake_result,
    ) as mock_delete:
        resp = client.delete("/admin/knowledge/source/guide.pdf", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    mock_delete.assert_called_once_with("guide.pdf")
