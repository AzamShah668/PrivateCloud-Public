import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import { Monitor, Cpu, MemoryStick, Clock } from "lucide-react";
import Card from "@/components/ui/Card";
import StatusBadge from "./StatusBadge";
import { formatBytes, formatUptime, formatCPU } from "@/lib/format";
import type { VMEnriched } from "@/api/vms";

interface VMCardProps {
  vm: VMEnriched;
  index: number;
}

const osIcons: Record<string, string> = {
  "ubuntu-22.04": "🟠",
  "ubuntu-24.04": "🟠",
  "debian-12": "🔴",
  "centos-9": "🟣",
  "windows-11": "🔵",
};

export default function VMCard({ vm, index }: VMCardProps) {
  const navigate = useNavigate();

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{
        delay: index * 0.06,
        duration: 0.4,
        ease: [0.16, 1, 0.3, 1],
      }}
    >
      <Card hoverable onClick={() => navigate(`/vms/${vm.id}`)} className="p-5">
        {/* Top row: name + status */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="text-lg">{osIcons[vm.os_choice] ?? "💻"}</span>
            <div className="min-w-0">
              <h3
                className="text-sm font-semibold text-primary truncate"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {vm.vm_name}
              </h3>
              <p className="text-xs text-muted font-mono">VMID {vm.vmid}</p>
            </div>
          </div>
          <StatusBadge status={vm.status} liveStatus={vm.live_status} />
        </div>

        {/* OS badge */}
        <div className="mb-4">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[var(--radius-sm)] bg-elevated text-xs text-secondary border border-border-subtle">
            <Monitor className="h-3 w-3" />
            {vm.os_choice}
          </span>
        </div>

        {/* Metrics grid */}
        <div className="grid grid-cols-3 gap-3">
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] text-muted uppercase tracking-wider flex items-center gap-1">
              <Cpu className="h-3 w-3" /> CPU
            </span>
            <span className="text-xs font-medium text-primary font-mono">
              {formatCPU(vm.cpu_usage)}
            </span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] text-muted uppercase tracking-wider flex items-center gap-1">
              <MemoryStick className="h-3 w-3" /> RAM
            </span>
            <span className="text-xs font-medium text-primary font-mono">
              {vm.mem_usage != null && vm.max_mem
                ? `${formatBytes(vm.mem_usage)} / ${formatBytes(vm.max_mem)}`
                : "—"}
            </span>
          </div>
          <div className="flex flex-col gap-0.5">
            <span className="text-[10px] text-muted uppercase tracking-wider flex items-center gap-1">
              <Clock className="h-3 w-3" /> Uptime
            </span>
            <span className="text-xs font-medium text-primary font-mono">
              {formatUptime(vm.uptime)}
            </span>
          </div>
        </div>
      </Card>
    </motion.div>
  );
}
