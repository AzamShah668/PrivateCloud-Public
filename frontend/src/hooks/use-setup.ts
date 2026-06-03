import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getSetupStatus, applySetup } from "@/api/setup";

/** First-run setup status. Only meaningful for admins (drives the wizard). */
export function useSetupStatus(enabled = true) {
  return useQuery({
    queryKey: ["setup", "status"],
    queryFn: getSetupStatus,
    enabled,
    staleTime: 30_000,
  });
}

export function useApplySetup() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      settings,
      testConnection,
    }: {
      settings: Record<string, unknown>;
      testConnection?: boolean;
    }) => applySetup(settings, testConnection ?? true),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["setup", "status"] });
      qc.invalidateQueries({ queryKey: ["admin", "settings"] });
    },
  });
}
