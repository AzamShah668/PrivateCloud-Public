import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listVMs,
  getVM,
  createVM,
  updateVM,
  deleteVM,
  type CreateVMPayload,
  type UpdateVMPayload,
} from "@/api/vms";
import { toast } from "sonner";

// Poll faster while any VM is still being provisioned so the UI transitions
// out of the "Provisioning…" state promptly. Once all VMs have reached a
// terminal status, fall back to a relaxed 10s interval.
function pollIntervalForList(data: Awaited<ReturnType<typeof listVMs>> | undefined) {
  if (!data) return 10_000;
  return data.some((vm) => vm.status === "queued" || vm.status === "running")
    ? 3_000
    : 10_000;
}

function pollIntervalForSingle(data: Awaited<ReturnType<typeof getVM>> | undefined) {
  if (!data) return 10_000;
  return data.status === "queued" || data.status === "running" ? 3_000 : 10_000;
}

export function useVMs() {
  return useQuery({
    queryKey: ["vms"],
    queryFn: listVMs,
    refetchInterval: (query) => pollIntervalForList(query.state.data),
  });
}

export function useVM(jobId: number) {
  return useQuery({
    queryKey: ["vms", jobId],
    queryFn: () => getVM(jobId),
    refetchInterval: (query) => pollIntervalForSingle(query.state.data),
  });
}

export function useCreateVM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: CreateVMPayload) => createVM(payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vms"] });
      toast.success("VM creation started");
    },
    onError: (err: Error) => {
      const msg = err.message || "Failed to create VM";
      if (msg.includes("429")) {
        toast.error("Daily quota exceeded. Try again tomorrow.");
      } else if (msg.includes("503")) {
        toast.error("Cloud infrastructure temporarily unavailable");
      } else {
        toast.error(msg);
      }
    },
  });
}

export function useUpdateVM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ jobId, payload }: { jobId: number; payload: UpdateVMPayload }) =>
      updateVM(jobId, payload),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["vms"] });
      toast.success(`VM ${vars.payload.action} initiated`);
    },
    onError: (err: Error) => {
      toast.error(err.message || "Action failed");
    },
  });
}

export function useDeleteVM() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (jobId: number) => deleteVM(jobId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["vms"] });
      toast.success("VM deleted");
    },
    onError: (err: Error) => {
      toast.error(err.message || "Failed to delete VM");
    },
  });
}
