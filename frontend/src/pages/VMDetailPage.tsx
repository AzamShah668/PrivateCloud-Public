import { useState, type ReactNode } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { motion } from "motion/react";
import { ArrowLeft, Monitor, Hash, Calendar, AlertTriangle } from "lucide-react";
import Header from "@/components/layout/Header";
import Button from "@/components/ui/Button";
import Badge from "@/components/ui/Badge";
import Spinner from "@/components/ui/Spinner";
import LiveMetrics from "@/components/vm-detail/LiveMetrics";
import ActionBar from "@/components/vm-detail/ActionBar";
import ResizeModal from "@/components/vm-detail/ResizeModal";
import DeleteConfirm from "@/components/vm-detail/DeleteConfirm";
import { useVM, useUpdateVM, useDeleteVM } from "@/hooks/use-vms";

/** Safely extract a number from an unknown payload value */
function toNum(v: unknown, fallback: number): number {
  return typeof v === "number" ? v : fallback;
}

export default function VMDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();
  const { data: vm, isLoading, isError } = useVM(Number(jobId));
  const updateMutation = useUpdateVM();
  const deleteMutation = useDeleteVM();

  const [resizeOpen, setResizeOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner className="h-8 w-8" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center gap-3">
        <AlertTriangle className="h-8 w-8 text-accent-red" />
        <p className="text-secondary">Failed to load VM details</p>
        <Link to="/">
          <Button variant="secondary">
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Button>
        </Link>
      </div>
    );
  }

  if (!vm) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center">
        <p className="text-secondary mb-4">VM not found</p>
        <Link to="/">
          <Button variant="secondary">
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Button>
        </Link>
      </div>
    );
  }

  // The list endpoint enriches with live_status, cpu_usage etc.
  // The single-get endpoint returns VMJob — these fields may be undefined.
  const liveStatus = ("live_status" in vm && typeof vm.live_status === "string")
    ? vm.live_status
    : vm.status;
  const payload = vm.request_payload ?? {};
  const currentCpu = toNum(payload.cpu_cores, 2);
  const currentRam = toNum(payload.ram_mb, 2048);

  function handleAction(action: "start" | "stop" | "restart") {
    updateMutation.mutate({ jobId: vm!.id, payload: { action } });
  }

  function handleResize(cpuCores: number, ramMb: number) {
    updateMutation.mutate(
      { jobId: vm!.id, payload: { action: "resize", cpu_cores: cpuCores, ram_mb: ramMb } },
      { onSuccess: () => setResizeOpen(false) },
    );
  }

  function handleDelete() {
    deleteMutation.mutate(vm!.id, {
      onSuccess: () => navigate("/"),
    });
  }

  return (
    <div className="flex flex-col h-full">
      <Header
        title={vm.vm_name}
        subtitle={`VMID ${vm.vmid}`}
        actions={
          <div className="flex items-center gap-3">
            <Badge status={liveStatus} />
            <Link to="/">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4" />
                Back
              </Button>
            </Link>
          </div>
        }
      />

      <main className="flex-1 overflow-y-auto p-6 space-y-6">
        {/* Actions */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        >
          <ActionBar
            liveStatus={liveStatus}
            onStart={() => handleAction("start")}
            onStop={() => handleAction("stop")}
            onRestart={() => handleAction("restart")}
            onResize={() => setResizeOpen(true)}
            onDelete={() => setDeleteOpen(true)}
            isPending={updateMutation.isPending}
          />
        </motion.div>

        {/* Live Metrics */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden"
        >
          <div
            className="absolute top-0 left-6 right-6 h-[1px]"
            style={{
              background: "linear-gradient(90deg, transparent, rgba(10,239,255,0.1), transparent)",
            }}
          />
          <h3
            className="text-xs font-bold uppercase tracking-[0.15em] text-primary mb-4"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Live Metrics
          </h3>
          <LiveMetrics vm={vm} />
        </motion.div>

        {/* Info Section */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden"
        >
          <div
            className="absolute top-0 left-6 right-6 h-[1px]"
            style={{
              background: "linear-gradient(90deg, transparent, rgba(10,239,255,0.1), transparent)",
            }}
          />
          <h3
            className="text-xs font-bold uppercase tracking-[0.15em] text-primary mb-4"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Information
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <InfoRow
              icon={<Monitor className="h-3.5 w-3.5" />}
              label="Operating System"
              value={vm.os_choice}
            />
            <InfoRow
              icon={<Hash className="h-3.5 w-3.5" />}
              label="Job ID"
              value={String(vm.id)}
            />
            <InfoRow
              icon={<Hash className="h-3.5 w-3.5" />}
              label="Proxmox VMID"
              value={String(vm.vmid)}
            />
            <InfoRow
              icon={<Calendar className="h-3.5 w-3.5" />}
              label="Created"
              value={new Date(vm.created_at).toLocaleString()}
            />
          </div>

          {vm.error_message && (
            <div className="mt-4 rounded-[var(--radius-md)] bg-accent-red/5 border border-accent-red/20 p-3">
              <p className="text-xs text-accent-red font-medium mb-0.5">Error</p>
              <p className="text-xs text-secondary font-mono">{vm.error_message}</p>
            </div>
          )}
        </motion.div>
      </main>

      {/* Modals */}
      <ResizeModal
        open={resizeOpen}
        onClose={() => setResizeOpen(false)}
        onConfirm={handleResize}
        currentCpu={currentCpu}
        currentRam={currentRam}
        isPending={updateMutation.isPending}
      />

      <DeleteConfirm
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        onConfirm={handleDelete}
        vmName={vm.vm_name}
        isPending={deleteMutation.isPending}
      />
    </div>
  );
}

function InfoRow({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <span className="text-muted mt-0.5">{icon}</span>
      <div>
        <p className="text-[9px] text-muted uppercase tracking-[0.1em] font-semibold">{label}</p>
        <p className="text-sm text-primary font-mono">{value}</p>
      </div>
    </div>
  );
}
