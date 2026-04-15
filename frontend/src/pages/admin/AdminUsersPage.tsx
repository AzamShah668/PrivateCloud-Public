import { useState } from "react";
import { motion } from "motion/react";
import {
  Search,
  RefreshCw,
  Shield,
  ShieldOff,
} from "lucide-react";
import { useAdminUsers, useUpdateUserRole, useUpdateUserQuota } from "@/hooks/use-admin";
import { cn } from "@/lib/cn";
import { toast } from "sonner";
import type { UserResponse } from "@/api/auth";

export default function AdminUsersPage() {
  const { data: users, isLoading, refetch } = useAdminUsers();
  const updateRole = useUpdateUserRole();
  const updateQuota = useUpdateUserQuota();
  const [search, setSearch] = useState("");
  const [editingQuota, setEditingQuota] = useState<number | null>(null);
  const [quotaValue, setQuotaValue] = useState("");

  const filtered = (users ?? []).filter(
    (u) =>
      u.username.toLowerCase().includes(search.toLowerCase()) ||
      u.role.toLowerCase().includes(search.toLowerCase())
  );

  function handleToggleRole(user: UserResponse) {
    const newRole = user.role === "admin" ? "user" : "admin";
    const action = newRole === "admin" ? "promote" : "demote";
    const confirmed = window.confirm(
      `Are you sure you want to ${action} "${user.username}" to ${newRole}?`
    );
    if (!confirmed) return;
    updateRole.mutate({ userId: user.id, role: newRole });
  }

  function handleSaveQuota(userId: number) {
    const num = Number(quotaValue);
    if (!Number.isInteger(num) || num < 0 || num > 100) {
      toast.error("Quota must be a whole number between 0 and 100");
      return; // keep field open so user can correct
    }
    updateQuota.mutate({ userId, dailyQuota: num });
    setEditingQuota(null);
    setQuotaValue("");
  }

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
          <h1
            className="text-2xl font-bold text-primary tracking-tight"
            style={{ fontFamily: "var(--font-display)" }}
          >
            User Management
          </h1>
          <p
            className="text-sm text-muted mt-1"
            style={{ fontFamily: "var(--font-body)" }}
          >
            Manage user roles and VM quotas
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

      {/* Search */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <div className="flex items-center gap-2 px-3 h-9 rounded-[var(--radius-md)] border border-border-subtle bg-elevated/50 max-w-sm focus-within:border-accent-cyan/30 transition-colors">
          <Search className="h-3.5 w-3.5 text-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search users..."
            className="bg-transparent text-xs text-primary placeholder:text-muted outline-none flex-1 font-mono"
          />
        </div>
      </motion.div>

      {/* Users grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {filtered.map((user, i) => (
          <motion.div
            key={user.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              delay: 0.15 + i * 0.04,
              duration: 0.4,
              ease: [0.16, 1, 0.3, 1],
            }}
            className="glass-panel glass-panel-hover rounded-[var(--radius-lg)] p-5 relative overflow-hidden group"
          >
            {/* Glow line */}
            <div
              className="absolute top-0 left-4 right-4 h-[1px] opacity-30 group-hover:opacity-60 transition-opacity"
              style={{
                background:
                  user.role === "admin"
                    ? "linear-gradient(90deg, transparent, rgba(245,158,11,0.5), transparent)"
                    : "linear-gradient(90deg, transparent, rgba(10,239,255,0.4), transparent)",
              }}
            />

            <div className="flex items-start gap-4">
              {/* Avatar */}
              <div
                className="h-11 w-11 rounded-full flex items-center justify-center text-sm font-bold uppercase shrink-0"
                style={{
                  background:
                    user.role === "admin"
                      ? "linear-gradient(135deg, rgba(245,158,11,0.15), rgba(239,68,68,0.1))"
                      : "linear-gradient(135deg, rgba(10,239,255,0.15), rgba(59,130,246,0.1))",
                  border:
                    user.role === "admin"
                      ? "1px solid rgba(245,158,11,0.2)"
                      : "1px solid rgba(10,239,255,0.2)",
                  color:
                    user.role === "admin"
                      ? "var(--color-accent-amber)"
                      : "var(--color-accent-cyan)",
                  fontFamily: "var(--font-display)",
                }}
              >
                {user.username.charAt(0)}
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="text-sm font-semibold text-primary truncate">
                    {user.username}
                  </h3>
                  <span
                    className={cn(
                      "text-[9px] px-1.5 py-0.5 rounded border font-mono font-bold uppercase tracking-wider",
                      user.role === "admin"
                        ? "bg-accent-amber/10 text-accent-amber border-accent-amber/20"
                        : "bg-elevated text-muted border-border-subtle"
                    )}
                  >
                    {user.role}
                  </span>
                </div>

                <div className="flex items-center gap-3 mt-2">
                  {/* Quota */}
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] text-muted">Quota:</span>
                    {editingQuota === user.id ? (
                      <input
                        type="number"
                        value={quotaValue}
                        onChange={(e) => setQuotaValue(e.target.value)}
                        onBlur={() => handleSaveQuota(user.id)}
                        onKeyDown={(e) =>
                          e.key === "Enter" && handleSaveQuota(user.id)
                        }
                        className="w-12 h-5 px-1 text-xs font-mono text-accent-cyan bg-elevated border border-accent-cyan/30 rounded-[var(--radius-sm)] outline-none"
                        autoFocus
                        min={0}
                        max={100}
                      />
                    ) : (
                      <button
                        onClick={() => {
                          setEditingQuota(user.id);
                          setQuotaValue(String(user.daily_quota));
                        }}
                        className="text-xs font-mono font-semibold text-accent-cyan hover:underline cursor-pointer"
                      >
                        {user.daily_quota}/day
                      </button>
                    )}
                  </div>
                  <span className="text-border-subtle">|</span>
                  <span className="text-[10px] text-muted font-mono">
                    ID: {user.id}
                  </span>
                </div>

                <p className="text-[10px] text-muted font-mono mt-1.5">
                  Joined {new Date(user.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border-subtle/30">
              <button
                onClick={() => handleToggleRole(user)}
                disabled={updateRole.isPending}
                className={cn(
                  "flex items-center gap-1.5 px-2.5 h-7 rounded-[var(--radius-sm)] text-[10px] font-semibold transition-all cursor-pointer",
                  user.role === "admin"
                    ? "text-accent-red border border-accent-red/20 hover:bg-accent-red/10"
                    : "text-accent-amber border border-accent-amber/20 hover:bg-accent-amber/10"
                )}
              >
                {user.role === "admin" ? (
                  <>
                    <ShieldOff className="h-3 w-3" />
                    Demote
                  </>
                ) : (
                  <>
                    <Shield className="h-3 w-3" />
                    Promote
                  </>
                )}
              </button>
            </div>
          </motion.div>
        ))}

        {filtered.length === 0 && (
          <div className="col-span-full py-12 text-center text-sm text-muted">
            {isLoading ? "Loading users..." : "No users found"}
          </div>
        )}
      </div>
    </div>
  );
}
