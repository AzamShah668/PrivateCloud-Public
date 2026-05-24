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
  Trash2,
  Ban,
  RotateCcw,
  Settings,
  LogIn,
  AlertCircle,
} from "lucide-react";
import { useAdminAuditLogs } from "@/hooks/use-admin";
import { cn } from "@/lib/cn";
import GlitchText from "@/components/ui/GlitchText";

/** All action_type enum values — aligned with backend CHECK constraint. */
const ACTION_TYPES = [
  "all",
  "user.create",
  "user.role_change",
  "user.quota_change",
  "user.suspend",
  "user.delete",
  "user.reactivate",
  "vm.create",
  "vm.delete",
  "vm.status_change",
  "settings.change",
  "admin.login",
  "system.unknown",
] as const;

const ACTION_ICONS: Record<string, React.ReactNode> = {
  "user.create": <Plus className="h-3.5 w-3.5" />,
  "user.role_change": <Shield className="h-3.5 w-3.5" />,
  "user.quota_change": <User className="h-3.5 w-3.5" />,
  "user.suspend": <Ban className="h-3.5 w-3.5" />,
  "user.delete": <Trash2 className="h-3.5 w-3.5" />,
  "user.reactivate": <RotateCcw className="h-3.5 w-3.5" />,
  "vm.create": <Plus className="h-3.5 w-3.5" />,
  "vm.delete": <Trash2 className="h-3.5 w-3.5" />,
  "vm.status_change": <Activity className="h-3.5 w-3.5" />,
  "settings.change": <Settings className="h-3.5 w-3.5" />,
  "admin.login": <LogIn className="h-3.5 w-3.5" />,
  "system.unknown": <AlertCircle className="h-3.5 w-3.5" />,
};

const ACTION_COLORS: Record<string, string> = {
  "user.create": "text-accent-blue",
  "user.role_change": "text-accent-amber",
  "user.quota_change": "text-accent-cyan",
  "user.suspend": "text-accent-amber",
  "user.delete": "text-accent-red",
  "user.reactivate": "text-accent-green",
  "vm.create": "text-accent-green",
  "vm.delete": "text-accent-red",
  "vm.status_change": "text-accent-cyan",
  "settings.change": "text-accent-amber",
  "admin.login": "text-accent-green",
  "system.unknown": "text-muted",
};

export default function AdminAuditLogsPage() {
  const [actionFilter, setActionFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const { data: logs, isLoading, refetch } = useAdminAuditLogs({
    actionType: actionFilter === "all" ? undefined : actionFilter,
    limit: 200,
  });

  const filtered = (logs ?? []).filter((log) => {
    const haystack = [
      log.action,
      log.action_type,
      log.target_type,
      log.target_id ?? "",
      log.actor_username ?? "",
      log.target_username ?? "",
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(search.toLowerCase());
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
        className="space-y-3"
      >
        <div className="flex items-center gap-2 px-3 h-9 rounded-[var(--radius-md)] border border-border-subtle bg-elevated/50 max-w-sm focus-within:border-accent-cyan/30 transition-colors">
          <Search className="h-3.5 w-3.5 text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search actions, actors, targets..."
            className="bg-transparent text-xs text-primary placeholder:text-muted outline-none flex-1 font-mono"
          />
        </div>

        <div className="flex items-center gap-1 flex-wrap">
          <Filter className="h-3.5 w-3.5 text-muted mr-1" />
          {ACTION_TYPES.map((a) => (
            <button
              key={a}
              onClick={() => setActionFilter(a)}
              className={cn(
                "px-2 py-1 rounded-[var(--radius-sm)] text-[10px] font-mono font-semibold transition-all cursor-pointer",
                actionFilter === a
                  ? "bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20"
                  : "text-muted hover:text-secondary border border-transparent",
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
                {[
                  "",
                  "Action Type",
                  "Actor",
                  "Target",
                  "Details",
                  "Timestamp",
                ].map((h) => (
                  <th
                    key={h}
                    className="px-4 py-3 text-left text-[10px] font-bold uppercase tracking-[0.12em] text-muted"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((log, i) => (
                <motion.tr
                  key={log.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{
                    delay: 0.2 + i * 0.015,
                    duration: 0.25,
                    ease: [0.16, 1, 0.3, 1],
                  }}
                  className="border-b border-border-subtle/50 hover:bg-elevated/40 hover:shadow-[inset_0_0_15px_rgba(10,239,255,0.03)] transition-all duration-300 group"
                >
                  <td className="px-4 py-3 w-8">
                    <span
                      className={cn(
                        "opacity-60",
                        ACTION_COLORS[log.action_type] ?? "text-muted",
                      )}
                    >
                      {ACTION_ICONS[log.action_type] ?? (
                        <Activity className="h-3.5 w-3.5" />
                      )}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={cn(
                        "text-xs font-mono font-semibold",
                        ACTION_COLORS[log.action_type] ?? "text-secondary",
                      )}
                    >
                      {log.action_type}
                    </span>
                    <div className="text-[10px] text-muted mt-0.5">
                      {log.action}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs font-mono">
                    <span className="text-accent-cyan">
                      {log.actor_username ?? `user#${log.user_id}`}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs font-mono text-secondary">
                    {log.target_username ? (
                      <span className="text-accent-amber">
                        {log.target_username}
                      </span>
                    ) : (
                      <>
                        {log.target_type}
                        {log.target_id && (
                          <span className="text-muted">:{log.target_id}</span>
                        )}
                      </>
                    )}
                  </td>
                  <td className="px-4 py-3 max-w-[240px]">
                    <span className="text-[10px] text-muted font-mono truncate block">
                      {JSON.stringify(log.details).slice(0, 80)}
                      {JSON.stringify(log.details).length > 80 ? "…" : ""}
                    </span>
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
