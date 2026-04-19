import { useState } from "react";
import { motion } from "motion/react";
import {
  Search,
  RefreshCw,
  Filter,
  Activity,
  Shield,
  User,
  Plus,
  Play,
  Square,
  RotateCcw,
  Trash2,
} from "lucide-react";
import { useAdminAuditLogs } from "@/hooks/use-admin";
import { cn } from "@/lib/cn";
import GlitchText from "@/components/ui/GlitchText";

const ACTION_ICONS: Record<string, React.ReactNode> = {
  "vm.create": <Plus className="h-3.5 w-3.5" />,
  "vm.start": <Play className="h-3.5 w-3.5" />,
  "vm.stop": <Square className="h-3.5 w-3.5" />,
  "vm.restart": <RotateCcw className="h-3.5 w-3.5" />,
  "vm.delete": <Trash2 className="h-3.5 w-3.5" />,
  "admin.update_role": <Shield className="h-3.5 w-3.5" />,
  "admin.update_quota": <User className="h-3.5 w-3.5" />,
  "user.login": <User className="h-3.5 w-3.5" />,
  "user.register": <Plus className="h-3.5 w-3.5" />,
};

const ACTION_COLORS: Record<string, string> = {
  "vm.create": "text-accent-green",
  "vm.start": "text-accent-cyan",
  "vm.stop": "text-accent-amber",
  "vm.restart": "text-accent-blue",
  "vm.delete": "text-accent-red",
  "admin.update_role": "text-accent-amber",
  "admin.update_quota": "text-accent-cyan",
  "user.login": "text-accent-green",
  "user.register": "text-accent-blue",
};

export default function AdminAuditLogsPage() {
  const { data: logs, isLoading, refetch } = useAdminAuditLogs();
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("all");

  const uniqueActions = [
    "all",
    ...new Set((logs ?? []).map((l) => l.action)),
  ];

  const filtered = (logs ?? []).filter((log) => {
    const matchesSearch =
      log.action.toLowerCase().includes(search.toLowerCase()) ||
      log.target_type.toLowerCase().includes(search.toLowerCase()) ||
      (log.target_id ?? "").toLowerCase().includes(search.toLowerCase());
    const matchesAction =
      actionFilter === "all" || log.action === actionFilter;
    return matchesSearch && matchesAction;
  });

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
            text="Audit Logs"
            className="text-2xl font-bold text-primary tracking-tight"
          />
          <p
            className="text-sm text-muted mt-1"
            style={{ fontFamily: "var(--font-body)" }}
          >
            Complete activity trail across the platform
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
        className="flex items-center gap-4 flex-wrap"
      >
        <div className="flex items-center gap-2 px-3 h-9 rounded-[var(--radius-md)] border border-border-subtle bg-elevated/50 flex-1 max-w-sm focus-within:border-accent-cyan/30 transition-colors">
          <Search className="h-3.5 w-3.5 text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search actions, targets..."
            className="bg-transparent text-xs text-primary placeholder:text-muted outline-none flex-1 font-mono"
          />
        </div>

        <div className="flex items-center gap-1 flex-wrap">
          <Filter className="h-3.5 w-3.5 text-muted mr-1" />
          {uniqueActions.slice(0, 8).map((a) => (
            <button
              key={a}
              onClick={() => setActionFilter(a)}
              className={cn(
                "px-2 py-1 rounded-[var(--radius-sm)] text-[10px] font-mono font-semibold transition-all cursor-pointer",
                actionFilter === a
                  ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20"
                  : "text-muted hover:text-secondary border border-transparent"
              )}
            >
              {a}
            </button>
          ))}
        </div>
      </motion.div>

      {/* Log entries */}
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
                {["", "Action", "Target", "Details", "User ID", "Timestamp"].map(
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
              {filtered.map((log, i) => (
                <motion.tr
                  key={log.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{
                    delay: 0.2 + i * 0.02,
                    duration: 0.3,
                    ease: [0.16, 1, 0.3, 1],
                  }}
                  className="border-b border-border-subtle/50 hover:bg-elevated/40 hover:shadow-[inset_0_0_15px_rgba(10,239,255,0.03)] transition-all duration-300 group"
                >
                  <td className="px-4 py-3 w-8">
                    <span
                      className={cn(
                        "opacity-60",
                        ACTION_COLORS[log.action] ?? "text-muted"
                      )}
                    >
                      {ACTION_ICONS[log.action] ?? (
                        <Activity className="h-3.5 w-3.5" />
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "text-xs font-mono font-semibold",
                        ACTION_COLORS[log.action] ?? "text-secondary"
                      )}
                    >
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-secondary">
                    {log.target_type}
                    {log.target_id && (
                      <span className="text-muted">:{log.target_id}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 max-w-[200px]">
                    <span className="text-[10px] text-muted font-mono truncate block">
                      {JSON.stringify(log.details).slice(0, 60)}
                      {JSON.stringify(log.details).length > 60 ? "..." : ""}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted font-mono">
                    {log.user_id}
                  </td>
                  <td className="px-4 py-3 text-[10px] text-muted font-mono whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                </motion.tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-4 py-12 text-center text-sm text-muted"
                  >
                    {isLoading ? "Loading..." : "No audit logs found"}
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
