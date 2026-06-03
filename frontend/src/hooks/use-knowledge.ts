import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { HTTPError } from "ky";
import {
  deleteKnowledgeSource,
  getKnowledgeStatus,
  uploadKnowledgePdf,
  uploadKnowledgeText,
} from "@/api/knowledge";
import { toast } from "sonner";

/** Extract a user-friendly message from a ky HTTPError or generic Error. */
async function extractErrorMessage(err: unknown, fallback: string): Promise<string> {
  if (err instanceof HTTPError) {
    try {
      const body = await err.response.json<{ detail?: string }>();
      if (body.detail) return body.detail;
    } catch {
      /* body not JSON — fall through */
    }
  }
  return err instanceof Error ? err.message || fallback : fallback;
}

export function useKnowledgeStatus() {
  return useQuery({
    queryKey: ["admin", "knowledge", "status"],
    queryFn: getKnowledgeStatus,
    refetchInterval: 30_000,
  });
}

export function useUploadKnowledgePdf() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadKnowledgePdf(file),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["admin", "knowledge"] });
      toast.success(
        `Indexed "${result.source}" — ${result.chunks_indexed} chunks added`,
      );
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to upload document"));
    },
  });
}

export function useUploadKnowledgeText() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ source, text }: { source: string; text: string }) =>
      uploadKnowledgeText(source, text),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["admin", "knowledge"] });
      toast.success(
        `Indexed "${result.source}" — ${result.chunks_indexed} chunks added`,
      );
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to index text"));
    },
  });
}

export function useDeleteKnowledgeSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (source: string) => deleteKnowledgeSource(source),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["admin", "knowledge"] });
      toast.success(`Removed "${result.source}" from the knowledge base`);
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to remove document"));
    },
  });
}
