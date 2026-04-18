import { motion } from "motion/react";
import {
  Play,
  Square,
  ExternalLink,
  MoreHorizontal,
  CircleDot,
  AlertTriangle,
  Pause,
} from "lucide-react";
import { Link } from "react-router-dom";
import Badge from "@/components/ui/Badge";
import type { VMEnriched } from "@/api/vms";

interface MyInstancesProps {
  vms?: VMEnriched[];
}

function StatusIcon({ status }: { status: string }) {
  if (status === "running") return <CircleDot className="h-3.5 w-3.5 text-accent-green" />;
  if (status === "stopped") return <Square className="h-3.5 w-3.5 text-accent-amber" />;
  if (status === "failed") return <AlertTriangle className="h-3.5 w-3.5 text-accent-red" />;
  return <Pause className="h-3.5 w-3.5 text-muted" />;
}

export default function MyInstances({ vms }: MyInstancesProps) {
  const instances = (vms ?? []).filter((vm) => vm.status !== "deleted");

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden h-full"
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-6 right-6 h-[1px]"
        style={{
          background: "linear-gradient(90deg, transparent, rgba(10,239,255,0.15), transparent)",
        }}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2
          className="text-sm font-bold tracking-wide text-primary"
          style={{ fontFamily: "var(--font-display)" }}
        >
          My Instances
        </h2>
        <span className="text-xs text-muted font-mono">
          {instances.length} total
        </span>
      </div>

      {instances.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div
            className="h-16 w-16 rounded-full flex items-center justify-center mb-4"
            style={{
              background: "radial-gradient(circle, rgba(10,239,255,0.08) 0%, transparent 70%)",
              border: "1px solid rgba(10,239,255,0.1)",
            }}
          >
            <CircleDot className="h-7 w-7 text-accent-cyan/40" />
          </div>
          <p className="text-sm text-secondary mb-1" style={{ fontFamily: "var(--font-body)" }}>
            No instances yet
          </p>
          <p className="text-xs text-muted">
            Deploy your first compute instance to get started
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {instances.slice(0, 6).map((vm, i) => (
            <motion.div
              key={vm.id}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                delay: 0.1 + i * 0.06,
                duration: 0.35,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="group flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] hover:bg-elevated/40 transition-all duration-200 nav-glow"
            >
              {/* Status icon */}
              <StatusIcon status={vm.live_status ?? vm.status} />

              {/* Name + ID + IP */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-primary truncate" style={{ fontFamily: "var(--font-body)" }}>
                  {vm.vm_name}
                </p>
                <p className="text-[10px] text-muted font-mono">
                  {vm.vm_ip ? vm.vm_ip : `ID: ${vm.vmid}`}
                </p>
              </div>

              {/* Status badge */}
              <Badge status={vm.live_status ?? vm.status} />

              {/* Actions */}
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                {vm.live_status === "running" ? (
                  <button
                    className="p-1.5 rounded-[var(--radius-sm)] text-accent-amber/60 hover:text-accent-amber hover:bg-accent-amber/10 transition-colors cursor-pointer"
                    title="Stop"
                  >
                    <Square className="h-3 w-3" />
                  </button>
                ) : (
                  <button
                    className="p-1.5 rounded-[var(--radius-sm)] text-accent-green/60 hover:text-accent-green hover:bg-accent-green/10 transition-colors cursor-pointer"
                    title="Start"
                  >
                    <Play className="h-3 w-3" />
                  </button>
                )}
                <Link
                  to={`/vms/${vm.id}`}
                  className="p-1.5 rounded-[var(--radius-sm)] text-accent-cyan/60 hover:text-accent-cyan hover:bg-accent-cyan/10 transition-colors"
                  title="Details"
                >
                  <ExternalLink className="h-3 w-3" />
                </Link>
                <button className="p-1.5 rounded-[var(--radius-sm)] text-muted hover:text-primary hover:bg-elevated transition-colors cursor-pointer">
                  <MoreHorizontal className="h-3 w-3" />
                </button>
              </div>
            </motion.div>
          ))}
        </div>
      )}
    </motion.div>
  );
}
