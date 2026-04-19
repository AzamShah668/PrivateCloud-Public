import { useState } from "react";
import { motion } from "motion/react";
import {
  Server,
  Search,
  RefreshCw,
  Cpu,
  HardDrive,
  MemoryStick,
} from "lucide-react";
import { useAdminVMs } from "@/hooks/use-admin";
import { cn } from "@/lib/cn";
import GlitchText from "@/components/ui/GlitchText";

const STATUS_STYLES: Record<string, string> = {
  done: "bg-accent-green/10 text-accent-green border-accent-green/20",
  running: "bg-accent-blue/10 text-accent-blue border-accent-blue/20",
  queued: "bg-accent-amber/10 text-accent-amber border-accent-amber/20",
  failed: "bg-accent-red/10 text-accent-red border-accent-red/20",
  deleted: "bg-muted/10 text-muted border-border-subtle",
};

export default function AdminVMsPage() {
  const { data: vms, isLoading, refetch } = useAdminVMs();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const filtered = (vms ?? []).filter((vm) => {
    const matchesSearch =
      vm.vm_name.toLowerCase().includes(search.toLowerCase()) ||
      vm.owner_username.toLowerCase().includes(search.toLowerCase()) ||
      vm.os_choice.toLowerCase().includes(search.toLowerCase()) ||
      (vm.vm_ip ?? "").toLowerCase().includes(search.toLowerCase());
    const matchesStatus =
      statusFilter === "all" || vm.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const statuses = ["all", "done", "running", "queued", "failed", "deleted"];

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="flex items-center justify-between"
      >
        <div>
          <GlitchText
            text="Virtual Machines"
            className="text-2xl font-bold text-primary tracking-tight"
          />
          <p
            className="text-sm text-muted mt-1"
            style={{ fontFamily: "var(--font-body)" }}
          >
            All VM instances across the platform
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 h-8 rounded-[var(--radius-md)] text-xs font-medium text-secondary border border-border-subtle hover:border-accent-cyan/30 hover:text-accent-cyan transition-all cursor-pointer"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </motion.div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="flex items-center gap-4"
      >
        <div className="flex items-center gap-2 px-3 h-9 rounded-[var(--radius-md)] border border-border-subtle bg-elevated/50 flex-1 max-w-sm focus-within:border-accent-cyan/30 transition-colors">
          <Search className="h-3.5 w-3.5 text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by name, owner, or OS..."
            className="bg-transparent text-xs text-primary placeholder:text-muted outline-none flex-1 font-mono"
          />
        </div>
        <div className="flex items-center gap-1">
          {statuses.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={cn(
                "px-2.5 py-1 rounded-[var(--radius-sm)] text-[10px] font-mono font-semibold uppercase tracking-wider transition-all cursor-pointer",
                statusFilter === s
                  ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20"
                  : "text-muted hover:text-secondary border border-transparent"
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Table */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="glass-panel rounded-[var(--radius-lg)] overflow-hidden"
      >
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border-subtle">
                {["VM Name", "Owner", "VMID", "IP Address", "OS", "Resources", "Status", "Created"].map(
                  (h) => (
                    <th
                      key={h}
                      className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-[0.12em] text-muted"
                      style={{ fontFamily: "var(--font-display)" }}
                    >
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {filtered.map((vm, i) => {
                const payload = vm.request_payload as Record<string, unknown>;
                return (
                  <motion.tr
                    key={vm.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{
                      delay: 0.2 + i * 0.03,
                      duration: 0.3,
                      ease: [0.16, 1, 0.3, 1],
                    }}
                    className="border-b border-border-subtle/50 hover:bg-elevated/40 hover:shadow-[inset_0_0_20px_rgba(10,239,255,0.05)] transition-all duration-300 group"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Server className="h-3.5 w-3.5 text-accent-blue/50" />
                        <span className="text-sm text-primary font-medium">
                          {vm.vm_name}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-secondary font-mono">
                      {vm.owner_username}
                    </td>
                    <td className="px-4 py-3 text-xs text-muted font-mono">
                      {vm.vmid}
                    </td>
                    <td className="px-4 py-3 text-xs text-secondary font-mono">
                      {vm.vm_ip ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-xs text-secondary">
                      {vm.os_choice}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3 text-[10px] text-muted font-mono">
                        <span className="flex items-center gap-1">
                          <Cpu className="h-3 w-3" />
                          {(payload?.cpu_cores as number) ?? "—"}
                        </span>
                        <span className="flex items-center gap-1">
                          <MemoryStick className="h-3 w-3" />
                          {(payload?.ram_mb as number) ? `${payload.ram_mb}MB` : "—"}
                        </span>
                        <span className="flex items-center gap-1">
                          <HardDrive className="h-3 w-3" />
                          {(payload?.storage_gb as number) ? `${payload.storage_gb}G` : "—"}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn(
                          "text-[10px] px-2 py-0.5 rounded-full border font-mono font-semibold uppercase",
                          STATUS_STYLES[vm.status] ?? STATUS_STYLES.done
                        )}
                      >
                        {vm.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-[10px] text-muted font-mono">
                      {new Date(vm.created_at).toLocaleDateString()}
                    </td>
                  </motion.tr>
                );
              })}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={8}
                    className="px-4 py-12 text-center text-sm text-muted"
                  >
                    {isLoading ? "Loading..." : "No VMs found"}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </motion.div>
    </div>
  );
}
