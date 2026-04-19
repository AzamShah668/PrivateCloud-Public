import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { HTTPError } from "ky";
import {
  getAdminStats,
  listAllUsers,
  listAllVMs,
  listAuditLogs,
  updateUserRole,
  updateUserQuota,
} from "@/api/admin";
import { toast } from "sonner";

/** Extract a user-friendly message from ky HTTPError or generic Error */
async function extractErrorMessage(err: unknown, fallback: string): Promise<string> {
  if (err instanceof HTTPError) {
    try {
      const body = await err.response.json<{ detail?: string }>();
      if (body.detail) return body.detail;
    } catch { /* body not JSON — fall through */ }
  }
  return err instanceof Error ? err.message || fallback : fallback;
}

export function useAdminStats() {
  return useQuery({
    queryKey: ["admin", "stats"],
    queryFn: getAdminStats,
    refetchInterval: 15_000,
  });
}

export function useAdminUsers() {
  return useQuery({
    queryKey: ["admin", "users"],
    queryFn: listAllUsers,
    refetchInterval: 30_000,
  });
}

export function useAdminVMs() {
  return useQuery({
    queryKey: ["admin", "vms"],
    queryFn: listAllVMs,
    refetchInterval: 10_000,
  });
}

export function useAdminAuditLogs() {
  return useQuery({
    queryKey: ["admin", "audit-logs"],
    queryFn: listAuditLogs,
    refetchInterval: 30_000,
  });
}

export function useUpdateUserRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, role }: { userId: number; role: string }) =>
      updateUserRole(userId, role),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      qc.invalidateQueries({ queryKey: ["admin", "stats"] });
      toast.success(`User role updated to ${vars.role}`);
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to update role"));
    },
  });
}

export function useUpdateUserQuota() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      userId,
      dailyQuota,
    }: {
      userId: number;
      dailyQuota: number;
    }) => updateUserQuota(userId, dailyQuota),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      toast.success("User quota updated");
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to update quota"));
    },
  });
}
