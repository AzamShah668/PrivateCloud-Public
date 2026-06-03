import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { HTTPError } from "ky";
import { toast } from "sonner";
import {
  listTemplates,
  getTemplate,
  createTemplate,
  updateTemplate,
  distributeTemplate,
  getBatchProgress,
  listClasses,
  getClass,
  createClass,
  enrollStudents,
  unenrollStudent,
  type CreateTemplateBody,
  type UpdateTemplateBody,
  type DistributeBody,
} from "@/api/templates";

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

// ---------------------------------------------------------------------------
// Templates
// ---------------------------------------------------------------------------

export function useTemplates(includeArchived = false) {
  return useQuery({
    queryKey: ["templates", { includeArchived }],
    queryFn: () => listTemplates(includeArchived),
    refetchInterval: 30_000,
  });
}

export function useTemplate(id: number) {
  return useQuery({
    queryKey: ["templates", id],
    queryFn: () => getTemplate(id),
    enabled: id > 0,
  });
}

export function useCreateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateTemplateBody) => createTemplate(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["templates"] });
      toast.success("Template published");
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to publish template"));
    },
  });
}

export function useUpdateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: UpdateTemplateBody }) =>
      updateTemplate(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["templates"] });
      toast.success("Template updated");
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to update template"));
    },
  });
}

export function useDistributeTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: number; body: DistributeBody }) =>
      distributeTemplate(id, body),
    onSuccess: (batch) => {
      qc.invalidateQueries({ queryKey: ["templates"] });
      toast.success(`Distributing to ${batch.total} student(s) — cloning started`);
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to distribute template"));
    },
  });
}

/** Poll a batch's progress while any clone is still in flight. */
export function useBatchProgress(batchId: number | null) {
  return useQuery({
    queryKey: ["clone-batch", batchId],
    queryFn: () => getBatchProgress(batchId as number),
    enabled: batchId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "in_progress" ? 4_000 : false;
    },
  });
}

// ---------------------------------------------------------------------------
// Classes
// ---------------------------------------------------------------------------

export function useClasses() {
  return useQuery({
    queryKey: ["classes"],
    queryFn: listClasses,
    refetchInterval: 30_000,
  });
}

export function useClass(id: number | null) {
  return useQuery({
    queryKey: ["classes", id],
    queryFn: () => getClass(id as number),
    enabled: id !== null,
  });
}

export function useCreateClass() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; description?: string }) => createClass(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["classes"] });
      toast.success("Class created");
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to create class"));
    },
  });
}

export function useEnrollStudents() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ classId, studentIds }: { classId: number; studentIds: number[] }) =>
      enrollStudents(classId, studentIds),
    onSuccess: (res, vars) => {
      qc.invalidateQueries({ queryKey: ["classes"] });
      qc.invalidateQueries({ queryKey: ["classes", vars.classId] });
      toast.success(`Enrolled ${res.enrolled} new student(s)`);
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to enroll students"));
    },
  });
}

export function useUnenrollStudent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ classId, studentId }: { classId: number; studentId: number }) =>
      unenrollStudent(classId, studentId),
    onSuccess: (_res, vars) => {
      qc.invalidateQueries({ queryKey: ["classes"] });
      qc.invalidateQueries({ queryKey: ["classes", vars.classId] });
      toast.success("Student unenrolled");
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to unenroll student"));
    },
  });
}
