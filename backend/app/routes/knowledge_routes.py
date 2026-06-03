# =============================================================================
# backend/app/routes/knowledge_routes.py
# =============================================================================
# Admin-only management of the RAG knowledge base that powers the ChatOps
# agent's ability to answer conceptual / "how does X work" questions.
#
# Admins upload source material (PDFs, or raw text) here; the documents are
# chunked, embedded, and stored in the vector database. Every logged-in user
# can then query that knowledge implicitly through the chat agent — but only
# admins can add, list, or remove the underlying source documents.
#
# Endpoints (all require the `require_admin` dependency):
#   GET    /admin/knowledge/status              → availability + indexed sources
#   POST   /admin/knowledge/upload              → upload a PDF, index it
#   POST   /admin/knowledge/upload-text         → index raw text under a name
#   DELETE /admin/knowledge/source/{source}     → remove one source document
# =============================================================================

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.auth import require_admin
from app.models.user import UserInDB
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/knowledge", tags=["Admin — Knowledge Base"])

# Reject uploads larger than this to protect memory / ingest time.
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


# ---------------------------------------------------------------------------
# Response / request schemas
# ---------------------------------------------------------------------------

class KnowledgeSource(BaseModel):
    source: str
    chunks: int


class KnowledgeStatus(BaseModel):
    available: bool
    doc_count: int
    sources: list[KnowledgeSource]
    error: str | None = None


class IngestResult(BaseModel):
    source: str
    chunks_indexed: int
    pages: int | None = None
    status: str


class TextIngestRequest(BaseModel):
    source: str = Field(..., min_length=1, max_length=200, description="Name to file this text under.")
    text: str = Field(..., min_length=1, description="Raw text to chunk and index.")


class DeleteResult(BaseModel):
    source: str
    status: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/status", response_model=KnowledgeStatus, summary="Knowledge base status")
def knowledge_status(_admin: UserInDB = Depends(require_admin)) -> KnowledgeStatus:
    """Return whether the vector store is available and what's indexed."""
    return KnowledgeStatus(**rag_service.stats())


@router.post(
    "/upload",
    response_model=IngestResult,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF document into the knowledge base",
)
async def upload_pdf(
    file: UploadFile = File(...),
    _admin: UserInDB = Depends(require_admin),
) -> IngestResult:
    """
    Accept a PDF, extract its text, chunk it (500/50), embed each chunk, and
    store it in the vector database under the file's name.
    """
    filename = file.filename or "uploaded.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported by this endpoint. Use /upload-text for plain text.",
        )

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.",
        )
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        result = rag_service.ingest_pdf(contents, source=filename)
    except RuntimeError as exc:
        # Vector store unavailable (deps missing / model not downloaded yet).
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("PDF ingest failed for %s: %s", filename, exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not process PDF: {exc!s}",
        )

    if result.get("status") == "no_text":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No extractable text found. This looks like a scanned/image-only PDF.",
        )

    return IngestResult(**result)


@router.post(
    "/upload-text",
    response_model=IngestResult,
    status_code=status.HTTP_201_CREATED,
    summary="Index raw text into the knowledge base",
)
def upload_text(
    payload: TextIngestRequest,
    _admin: UserInDB = Depends(require_admin),
) -> IngestResult:
    """Chunk and index a block of raw text (e.g. pasted notes) under a source name."""
    try:
        result = rag_service.ingest_text(payload.text, source=payload.source)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    return IngestResult(**result)


@router.delete(
    "/source/{source}",
    response_model=DeleteResult,
    summary="Remove a source document from the knowledge base",
)
def delete_source(
    source: str,
    _admin: UserInDB = Depends(require_admin),
) -> DeleteResult:
    """Delete every chunk belonging to a single source document."""
    try:
        result = rag_service.delete_source(source)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    return DeleteResult(**result)
