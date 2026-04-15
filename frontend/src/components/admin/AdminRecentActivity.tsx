import { motion } from "motion/react";
import { Activity, Server, User, Shield, Trash2, Play, Square, RotateCcw, Plus } from "lucide-react";
import type { AuditLog, VMJobAdmin } from "@/api/admin";
import { cn } from "@/lib/cn";

interface AdminRecentActivityProps {
  logs: AuditLog[];
  vms: VMJobAdmin[];
}

const ACTION_ICONS: Record<string, React.ReactNode> = {
  "vm.create": <Plus className="h-3.5 w-3.5" />,
  "vm.start": <Play className="h-3.5 w-3.5" />,
  "vm.stop": <Square className="h-3.5 w-3.5" />,
  "vm.restart": <RotateCcw className="h-3.5 w-3.5" />,
  "vm.delete": <Trash2 className="h-3.5 w-3.5" />,
  "admin.update_role": <Shield className="h-3.5 w-3.5" />,
  "admin.update_quota": <User className="h-3.5 w-3.5" />,
};

const ACTION_COLORS: Record<string, string> = {
  "vm.create": "text-accent-green",
  "vm.start": "text-accent-cyan",
  "vm.stop": "text-accent-amber",
  "vm.restart": "text-accent-blue",
  "vm.delete": "text-accent-red",
  "admin.update_role": "text-accent-amber",
  "admin.update_quota": "text-accent-cyan",
};

function formatTimeAgo(dateStr: string): string {
  const parsed = new Date(dateStr);
  if (isNaN(parsed.getTime())) return "unknown";
  const diff = Date.now() - parsed.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

const STATUS_STYLES: Record<string, string> = {
  done: "bg-accent-green/10 text-accent-green border-accent-green/20",
  running: "bg-accent-blue/10 text-accent-blue border-accent-blue/20",
  queued: "bg-accent-amber/10 text-accent-amber border-accent-amber/20",
  failed: "bg-accent-red/10 text-accent-red border-accent-red/20",
  deleted: "bg-muted/10 text-muted border-border-subtle",
};

export default function AdminRecentActivity({ logs, vms }: AdminRecentActivityProps) {
  const recentLogs = logs.slice(0, 8);
  const recentVMs = vms.slice(0, 6);

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Recent Activity Log — left 7 cols */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="col-span-12 xl:col-span-7 glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden"
      >
        <div
          className="absolute top-0 left-6 right-6 h-[1px] opacity-40"
          style={{
            background: "linear-gradient(90deg, transparent, rgba(20,184,166,0.4), transparent)",
          }}
        />

        <div className="flex items-center justify-between mb-4">
          <h2
            className="text-xs font-bold uppercase tracking-[0.15em] text-primary"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Recent Activity
          </h2>
          <span className="text-[10px] text-muted font-mono">
            {logs.length} events
          </span>
        </div>

        <div className="space-y-1">
          {recentLogs.map((log, i) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                delay: 0.35 + i * 0.04,
                duration: 0.35,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] hover:bg-elevated/30 transition-colors group"
            >
              <span className={cn("opacity-60", ACTION_COLORS[log.action] ?? "text-muted")}>
                {ACTION_ICONS[log.action] ?? <Activity className="h-3.5 w-3.5" />}
              </span>
              <div className="flex-1 min-w-0">
                <span className="text-xs text-primary font-medium">
                  {log.action}
                </span>
                <span className="text-xs text-muted mx-1.5">on</span>
                <span className="text-xs font-mono text-secondary">
                  {log.target_type}:{log.target_id}
                </span>
              </div>
              <span className="text-[10px] text-muted font-mono whitespace-nowrap">
                {formatTimeAgo(log.created_at)}
              </span>
            </motion.div>
          ))}

          {recentLogs.length === 0 && (
            <div className="py-8 text-center text-sm text-muted">
              No activity recorded yet
            </div>
          )}
        </div>
      </motion.div>

      {/* Recent Deployments — right 5 cols */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="col-span-12 xl:col-span-5 glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden"
      >
        <div
          className="absolute top-0 left-6 right-6 h-[1px] opacity-40"
          style={{
            background: "linear-gradient(90deg, transparent, rgba(245,158,11,0.4), transparent)",
          }}
        />

        <div className="flex items-center justify-between mb-4">
          <h2
            className="text-xs font-bold uppercase tracking-[0.15em] text-primary"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Recent Deployments
          </h2>
          <span className="text-[10px] text-muted font-mono">
            {vms.length} total
          </span>
        </div>

        <div className="space-y-1">
          {recentVMs.map((vm, i) => (
            <motion.div
              key={vm.id}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                delay: 0.4 + i * 0.04,
                duration: 0.35,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] hover:bg-elevated/30 transition-colors"
            >
              <Server className="h-3.5 w-3.5 text-accent-blue/60" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-primary font-medium truncate">
                  {vm.vm_name}
                </p>
                <p className="text-[10px] text-muted font-mono">
                  {vm.owner_username} &middot; {vm.os_choice}
                </p>
              </div>
              <span
                className={cn(
                  "text-[10px] px-2 py-0.5 rounded-full border font-mono font-semibold uppercase",
                  STATUS_STYLES[vm.status] ?? STATUS_STYLES.done
                )}
              >
                {vm.status}
              </span>
            </motion.div>
          ))}

          {recentVMs.length === 0 && (
            <div className="py-8 text-center text-sm text-muted">
              No deployments yet
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}
