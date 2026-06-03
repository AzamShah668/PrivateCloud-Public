# 07 — RAG Knowledge Base for the ChatOps Agent

**Commit:** *uncommitted (working tree)* · **Date:** 2026-05-26 · **Sprint:** 5
**Files:** `backend/app/services/rag_service.py` (new), `backend/app/routes/knowledge_routes.py` (new), `backend/app/services/llm_agent.py`, `backend/app/main.py`, `backend/requirements.txt`, `docker-compose.yml`, `frontend/src/api/knowledge.ts` (new), `frontend/src/hooks/use-knowledge.ts` (new), `frontend/src/pages/admin/AdminKnowledgePage.tsx` (new), `frontend/src/components/dashboard/AIChatOps.tsx`, sidebar/App.tsx, plus 3 pytest files.

The ChatOps agent used to answer questions about Proxmox and the platform from
the LLM's training data alone, which meant occasional hallucinations about
features or commands that don't exist. This commit gives the agent a curated,
admin-managed knowledge base: PDF/Markdown documents that the agent retrieves
from on demand and synthesises answers from.

## The problem

Two complaints kept surfacing:
- *"It told me to run `qm migrate` which isn't enabled here."* — the LLM made up plausible-sounding Proxmox commands that don't exist in our setup.
- *"How do I do X in *our* platform?"* — the agent had no knowledge of our specific endpoints, quotas, conventions, or workarounds.

Fine-tuning would be expensive and stale immediately. RAG keeps the doc set
under admin control with near-zero ongoing cost.

## The stack — three choices that mattered

| Layer | Choice | Why |
|---|---|---|
| Vector store | **ChromaDB self-hosted** (in `docker-compose.yml`) | No external API calls, no per-query cost, data stays on our infra |
| Embeddings | **SentenceTransformers `all-MiniLM-L6-v2`** loaded into the backend container | Local CPU model, ~80 MB, $0 per embedding; OpenAI embeddings would have been ~$0.0001 each but require a network round-trip per query |
| Generation | **OpenRouter** (existing) | Only the final synthesis call needs an LLM; we already had the key |

The big architectural decision was **agentic retrieval, not pipeline retrieval**.
Pipeline RAG would inject the top-K chunks into every system prompt regardless
of whether the question needs them. Agentic RAG exposes the retriever as a
**tool the LLM decides to call when relevant**:

```python
# llm_agent.py — the tool definition the agent sees
{
  "type": "function",
  "function": {
    "name": "search_knowledge_base",
    "description": "Search the admin-uploaded knowledge base for documentation, "
                   "procedures, troubleshooting, or platform-specific answers.",
    "parameters": {
      "type": "object",
      "properties": {"query": {"type": "string"}},
      "required": ["query"]
    }
  }
}
```

Asked *"create an ubuntu vm"*, the agent ignores RAG and calls `create_vm`.
Asked *"how do I expand a Windows VM's disk?"*, the agent calls
`search_knowledge_base("expand windows VM disk")`, gets back the relevant chunks,
and synthesises an answer rooted in our docs.

## The retriever — chunking, embedding, search

`rag_service.py` exposes three operations:

```python
def ingest_document(file_path: str, doc_id: str, metadata: dict) -> int:
    """Split → embed → upsert into ChromaDB collection. Returns chunk count."""

def search(query: str, top_k: int = 4) -> list[dict]:
    """Embed the query, run cosine similarity, return chunks with sources."""

def delete_document(doc_id: str) -> None:
    """Remove all chunks belonging to a doc_id."""
```

Chunking is **paragraph-aware with a sliding overlap** (≈800 chars, 100-char
overlap), so a fact that straddles a paragraph break still lands in at least
one chunk. PDFs are extracted to text with `pypdf` before chunking. Each chunk
carries `{doc_id, source_filename, page_or_offset}` so we can cite sources in
the agent's answer.

## The admin upload UI

`AdminKnowledgePage.tsx` is a drag-and-drop uploader gated by `require_admin`,
plus a list view with delete buttons. The upload calls
`POST /admin/knowledge/upload` (multipart), which runs `ingest_document` and
returns the chunk count so the admin sees confirmation that indexing worked.

```typescript
// api/knowledge.ts
export async function uploadDocument(file: File): Promise<{doc_id: string, chunks: number}> {
  const fd = new FormData();
  fd.append("file", file);
  return api.post("admin/knowledge/upload", { body: fd }).json();
}
```

## Why ChromaDB lives in its own container (and why that bit us)

Initial mistake: I tried to embed ChromaDB inside the FastAPI process. Worked
locally, but the on-disk persistence path conflicted with the container's
filesystem layout and the index was wiped on every container rebuild. Moving
Chroma to its own service in `docker-compose.yml` with a named volume fixed
it — and made the backend container much smaller, since the embedding model
loads on-demand into a process that doesn't also have to manage the vector store.

```yaml
# docker-compose.yml (excerpt)
chromadb:
  image: chromadb/chroma:latest
  volumes:
    - chromadb_data:/chroma/chroma
  ports:
    - "8001:8000"
```

## Tests

Three pytest files cover the layers:
- `test_rag_service.py` — chunking, embedding shape, search filter
- `test_knowledge_routes.py` — auth, upload, list, delete
- `test_llm_agent_rag.py` — the tool-calling round-trip (mocked OpenRouter)

## Teaching summary

| | |
|---|---|
| **Trigger** | LLM hallucinated platform-specific commands; needed grounding in OUR docs. |
| **Pattern** | Agentic RAG — retriever exposed as a tool the LLM calls *when relevant*, not a pre-pended chunk dump on every turn. |
| **Stack** | ChromaDB (self-hosted) + SentenceTransformers (local) + OpenRouter (existing). |
| **Cost** | ~$0 per query for embedding and search; only generation tokens are paid. |
| **Lesson** | Self-hosted vector store needs its own container + persistent volume — embedding inside the API process loses data on every rebuild. |

See journal `019-rag-knowledge-base-integration.md` and `docs/knowledge/10-rag-knowledge-base.md`.
