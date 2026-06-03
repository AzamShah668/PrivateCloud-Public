import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { HTTPError } from "ky";
import {
  getAdminStats,
  listAllUsers,
  listAllVMs,
  listAuditLogs,
  listSettings,
  updateUserRole,
  updateUserQuota,
  suspendUser,
  deleteUser,
  reactivateUser,
  updateSetting,
  type AuditLogFilters,
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

export function useAdminUsers(includeDeleted = false) {
  return useQuery({
    queryKey: ["admin", "users", { includeDeleted }],
    queryFn: () => listAllUsers(includeDeleted),
    refetchInterval: 30_000,
  });
}

export function useAdminVMs(verifyProxmox = false) {
  return useQuery({
    queryKey: ["admin", "vms", { verifyProxmox }],
    queryFn: () => listAllVMs(verifyProxmox),
    refetchInterval: 10_000,
  });
}

export function useAdminAuditLogs(filters: AuditLogFilters = {}) {
  return useQuery({
    queryKey: ["admin", "audit-logs", filters],
    queryFn: () => listAuditLogs(filters),
    refetchInterval: 30_000,
  });
}

export function useAdminSettings() {
  return useQuery({
    queryKey: ["admin", "settings"],
    queryFn: listSettings,
    refetchInterval: 60_000,
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

// ---------------------------------------------------------------------------
// I3: User lifecycle mutations
// ---------------------------------------------------------------------------

export function useSuspendUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => suspendUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      qc.invalidateQueries({ queryKey: ["admin", "audit-logs"] });
      toast.success("User suspended");
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to suspend user"));
    },
  });
}

export function useDeleteUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => deleteUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      qc.invalidateQueries({ queryKey: ["admin", "stats"] });
      qc.invalidateQueries({ queryKey: ["admin", "audit-logs"] });
      toast.success("User deleted");
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to delete user"));
    },
  });
}

export function useReactivateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (userId: number) => reactivateUser(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "users"] });
      qc.invalidateQueries({ queryKey: ["admin", "audit-logs"] });
      toast.success("User reactivated");
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to reactivate user"));
    },
  });
}

// ---------------------------------------------------------------------------
// I3: Settings mutation
// ---------------------------------------------------------------------------

export function useUpdateSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: unknown }) =>
      updateSetting(key, value),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["admin", "settings"] });
      toast.success(`Setting "${vars.key}" updated`);
    },
    onError: async (err) => {
      toast.error(await extractErrorMessage(err, "Failed to update setting"));
    },
  });
}
