import { api } from "./client";

// ---------------------------------------------------------------------------
// RAG knowledge base — admin-only management of the documents the ChatOps
// agent retrieves from. Mirrors backend/app/routes/knowledge_routes.py.
// ---------------------------------------------------------------------------

export interface KnowledgeSource {
  source: string;
  chunks: number;
}

export interface KnowledgeStatus {
  available: boolean;
  doc_count: number;
  sources: KnowledgeSource[];
  error: string | null;
}

export interface IngestResult {
  source: string;
  chunks_indexed: number;
  pages: number | null;
  status: string;
}

export interface DeleteResult {
  source: string;
  status: string;
}

export async function getKnowledgeStatus(): Promise<KnowledgeStatus> {
  return api.get("admin/knowledge/status").json<KnowledgeStatus>();
}

export async function uploadKnowledgePdf(file: File): Promise<IngestResult> {
  const formData = new FormData();
  formData.append("file", file);
  // Long timeout: first upload triggers a one-time embedding-model download.
  return api
    .post("admin/knowledge/upload", { body: formData, timeout: 300_000 })
    .json<IngestResult>();
}

export async function uploadKnowledgeText(
  source: string,
  text: string,
): Promise<IngestResult> {
  return api
    .post("admin/knowledge/upload-text", {
      json: { source, text },
      timeout: 300_000,
    })
    .json<IngestResult>();
}

export async function deleteKnowledgeSource(
  source: string,
): Promise<DeleteResult> {
  return api
    .delete(`admin/knowledge/source/${encodeURIComponent(source)}`)
    .json<DeleteResult>();
}
