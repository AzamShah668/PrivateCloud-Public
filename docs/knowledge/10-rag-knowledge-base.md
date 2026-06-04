# RAG Knowledge Base (Agentic RAG in ChatOps)

> How the ChatOps agent answers *informational* questions by retrieving from
> admin-uploaded documents, in addition to *acting* on VMs.
> Added: Sprint 4, 2026-05-26.

## The idea — one agent, two modes

The existing `CloudAgentService` (OpenAI function-calling agent on OpenRouter)
gained a 5th tool, `search_knowledge_base`, alongside the 4 VM action tools.
The LLM picks per message:

- **Action** ("deploy/stop/delete my VM") → existing VM tools (unchanged).
- **Information** ("how does X work?", "what is a golden image?") →
  `search_knowledge_base` → retrieve chunks → the **same OpenRouter model**
  writes a grounded answer citing sources.

This is **agentic RAG**: RAG-as-a-tool, so the same chat box both does things
and answers things. See [[04-frontend-architecture]] for the chat UI.

## Pipeline (full, textbook RAG)

**Ingest** (admin uploads a PDF):
extract (`pypdf`) → chunk (`RecursiveCharacterTextSplitter`, 500/50) →
embed (`all-MiniLM-L6-v2` via ChromaDB's built-in **ONNX** embedder) → upsert.

**Retrieve + generate** (user asks):
embed query → ChromaDB cosine similarity (top-4) → inject chunks into a
grounding system prompt → **OpenRouter model** synthesizes the answer.

Ported from the `verventech-rag/verventech_pdf_rag` lab (Devops-batch1).

## Key decisions

- **Embeddings run locally, not on OpenRouter.** OpenRouter serves only
  chat/completions — it has **no embeddings endpoint**. Embeddings are always a
  separate model anyway. So the *answer* model = OpenRouter (unified with the
  agent), but the *retrieval* model = local, free, offline.
- **ONNX, not torch.** We use ChromaDB's **built-in default embedding function**
  (`DefaultEmbeddingFunction` = `all-MiniLM-L6-v2` as a small ONNX model via
  `onnxruntime`, already a chromadb dependency). This was a deliberate switch
  away from `sentence-transformers`, which drags in **PyTorch (~1.5-2.5 GB)** for
  the *same* model and quality. Result: backend image ~889 MB instead of ~2.5-3
  GB, and a ~1-2 min build instead of ~6 min. **Do not re-add torch /
  sentence-transformers** unless a model genuinely requires it.
- **ChromaDB**, self-hosted (on-brand for "PrivateCloud" — vectors never leave
  the box). Persisted to a Docker named volume `chroma_data`.
- **Admin-only ingestion.** All users query implicitly via chat; only admins
  add/list/remove source documents (`require_admin`).
- **Lazy + import-guarded.** chromadb/sentence-transformers/torch are imported
  only on first use, so the API still boots if the model isn't downloaded yet.
  `rag_service.is_available()` reflects that state; routes return 503 when down.

## Code map

| Concern | Location |
|---|---|
| Vector store service (ingest/search/stats/delete) | `backend/app/services/rag_service.py` |
| Admin ingest/manage routes (`/admin/knowledge/*`) | `backend/app/routes/knowledge_routes.py` |
| `search_knowledge_base` tool + grounded synthesis | `backend/app/services/llm_agent.py` (`_answer_from_knowledge`) |
| Router registration | `backend/app/main.py` |
| Admin UI (upload/list/delete) | `frontend/src/pages/admin/AdminKnowledgePage.tsx` |
| API client / hooks | `frontend/src/api/knowledge.ts`, `frontend/src/hooks/use-knowledge.ts` |
| Chat "📚 From Knowledge Base" indicator | `frontend/src/components/dashboard/AIChatOps.tsx` |
| Tests | `backend/tests/test_rag_service.py`, `test_knowledge_routes.py`, `test_llm_agent_rag.py` |

## Endpoints (admin-only)

- `GET    /admin/knowledge/status` — availability + per-source chunk counts
- `POST   /admin/knowledge/upload` — multipart PDF (max 20 MB)
- `POST   /admin/knowledge/upload-text` — index raw text under a name
- `DELETE /admin/knowledge/source/{name}` — remove a document

`POST /ai/chat` is unchanged on the surface; knowledge answers come back with
`execution_status: "knowledge"` and `data: [source names]`.

## Env / infra

- `CHROMA_PATH` (default `./data/chroma`; in Docker `/home/appuser/app/data/chroma`)
- Docker volumes: `chroma_data` (vectors), `model_cache` (mounted at
  `~/.cache`, holds Chroma's ONNX model under `~/.cache/chroma/onnx_models`).
  See [[02-docker-infrastructure]].
- Deps: `chromadb` (+ its bundled `onnxruntime`), `pypdf`,
  `langchain-text-splitters`. **No** sentence-transformers/torch.
- `bcrypt==4.0.1` is pinned because chromadb pulls in bcrypt; see
  [[07-debugging-journal]] Issue 7.

## Resilience / efficiency features

- **Self-healing search**: `search()` resets the ChromaDB client and retries once
  on any query failure (e.g. a stale in-memory index after an out-of-band write),
  and short-circuits when the collection is empty. See [[07-debugging-journal]]
  Issue 9.
- **Error vs no-results are distinct**: `search()` raises `RagError` on a genuine
  failure; an empty result is just `[]`. The agent reports a search *failure*
  differently from an empty knowledge base, so a crash is never mislabeled as
  "no documents".
- **Cached stats**: `stats()` caches the per-source chunk breakdown keyed on the
  total count, so the admin UI's 30s poll does not re-scan every chunk's metadata
  unless something changed.
- **Lazy + degrade-never-crash**: heavy imports and the model load happen on
  first use; if they fail the API still serves, and `is_available()` reflects it.

## Gotchas (also in [[08-pending-work]])

- **First query/upload downloads the ONNX model** (~80 MB, needs network once).
  Cached in the `model_cache` volume afterward.
- **Volume permissions**: the non-root `appuser` must own `data/chroma` and
  `~/.cache` or chromadb fails with SQLite "unable to open database file"
  (code 14). The Dockerfile pre-creates + chowns them. See
  [[07-debugging-journal]] Issue 8.
- **Image-only/scanned PDFs** have no text layer → upload returns 422 "no_text"
  (no OCR).
