import { useState } from "react";
import { motion } from "motion/react";
import { RefreshCw, Save, Settings as SettingsIcon, Pencil, X } from "lucide-react";
import { useAdminSettings, useUpdateSetting } from "@/hooks/use-admin";
import { cn } from "@/lib/cn";
import { toast } from "sonner";
import type { PlatformSetting, SettingValueType } from "@/api/admin";
import GlitchText from "@/components/ui/GlitchText";

const TYPE_STYLES: Record<SettingValueType, string> = {
  integer: "bg-accent-cyan/10 text-accent-cyan border-accent-cyan/20",
  boolean: "bg-accent-amber/10 text-accent-amber border-accent-amber/20",
  json: "bg-accent-blue/10 text-accent-blue border-accent-blue/20",
  string: "bg-elevated text-muted border-border-subtle",
};

function parseValueByType(
  raw: string,
  valueType: SettingValueType,
): { ok: true; value: unknown } | { ok: false; error: string } {
  if (valueType === "integer") {
    const n = Number(raw);
    if (!Number.isInteger(n)) return { ok: false, error: "Must be an integer" };
    return { ok: true, value: n };
  }
  if (valueType === "boolean") {
    const lower = raw.trim().toLowerCase();
    if (lower === "true" || lower === "1") return { ok: true, value: true };
    if (lower === "false" || lower === "0") return { ok: true, value: false };
    return { ok: false, error: "Must be 'true' or 'false'" };
  }
  if (valueType === "json") {
    try {
      return { ok: true, value: JSON.parse(raw) };
    } catch {
      return { ok: false, error: "Invalid JSON" };
    }
  }
  return { ok: true, value: raw };
}

function formatTypedValue(setting: PlatformSetting): string {
  if (setting.value_type === "json") {
    try {
      return JSON.stringify(setting.typed_value, null, 2);
    } catch {
      return setting.value;
    }
  }
  return String(setting.typed_value ?? setting.value);
}

export default function AdminSettingsPage() {
  const { data: settings, isLoading, refetch } = useAdminSettings();
  const updateMut = useUpdateSetting();

  const [editingKey, setEditingKey] = useState<string | null>(null);
  const [draftValue, setDraftValue] = useState("");

  function startEdit(setting: PlatformSetting) {
    setEditingKey(setting.key);
    setDraftValue(formatTypedValue(setting));
  }

  function cancelEdit() {
    setEditingKey(null);
    setDraftValue("");
  }

  function handleSave(setting: PlatformSetting) {
    const parsed = parseValueByType(draftValue, setting.value_type);
    if (!parsed.ok) {
      toast.error(`${setting.key}: ${parsed.error}`);
      return;
    }
    updateMut.mutate(
      { key: setting.key, value: parsed.value },
      {
        onSuccess: () => {
          setEditingKey(null);
          setDraftValue("");
        },
      },
    );
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
          <GlitchText
            text="Platform Settings"
            className="text-2xl font-bold text-primary tracking-tight"
          />
          <p
            className="text-sm text-muted mt-1"
            style={{ fontFamily: "var(--font-body)" }}
          >
            Runtime configuration — changes take effect immediately
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

      {/* Settings list */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="space-y-3"
      >
        {(settings ?? []).map((setting, i) => {
          const isEditing = editingKey === setting.key;
          const typeClass = TYPE_STYLES[setting.value_type] ?? TYPE_STYLES.string;

          return (
            <motion.div
              key={setting.key}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                delay: 0.15 + i * 0.04,
                duration: 0.35,
                ease: [0.16, 1, 0.3, 1],
              }}
              className="glass-panel rounded-[var(--radius-lg)] p-5"
            >
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <SettingsIcon className="h-3.5 w-3.5 text-muted" />
                    <h3 className="text-sm font-semibold text-primary font-mono">
                      {setting.key}
                    </h3>
                    <span
                      className={cn(
                        "text-[9px] px-1.5 py-0.5 rounded border font-mono font-bold uppercase tracking-wider",
                        typeClass,
                      )}
                    >
                      {setting.value_type}
                    </span>
                  </div>
                  {setting.description && (
                    <p className="text-xs text-muted mt-1.5">
                      {setting.description}
                    </p>
                  )}
                  <p className="text-[10px] text-muted font-mono mt-2">
                    Updated {new Date(setting.updated_at).toLocaleString()}
                    {setting.updated_by_username && (
                      <>
                        {" · by "}
                        <span className="text-accent-cyan">
                          {setting.updated_by_username}
                        </span>
                      </>
                    )}
                  </p>
                </div>

                {!isEditing && (
                  <button
                    onClick={() => startEdit(setting)}
                    className="flex items-center gap-1.5 px-2.5 h-7 rounded-[var(--radius-sm)] text-[10px] font-semibold text-accent-cyan border border-accent-cyan/20 hover:bg-accent-cyan/10 transition-all cursor-pointer"
                  >
                    <Pencil className="h-3 w-3" />
                    Edit
                  </button>
                )}
              </div>

              <div className="mt-3 pt-3 border-t border-border-subtle/30">
                {isEditing ? (
                  <div className="space-y-2">
                    {setting.value_type === "json" ? (
                      <textarea
                        value={draftValue}
                        onChange={(e) => setDraftValue(e.target.value)}
                        rows={Math.min(10, draftValue.split("\n").length + 1)}
                        className="w-full px-3 py-2 text-xs font-mono text-primary bg-elevated border border-accent-cyan/30 rounded-[var(--radius-sm)] outline-none focus:border-accent-cyan"
                        autoFocus
                      />
                    ) : (
                      <input
                        type="text"
                        value={draftValue}
                        onChange={(e) => setDraftValue(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSave(setting);
                          if (e.key === "Escape") cancelEdit();
                        }}
                        className="w-full px-3 h-8 text-xs font-mono text-primary bg-elevated border border-accent-cyan/30 rounded-[var(--radius-sm)] outline-none focus:border-accent-cyan"
                        autoFocus
                      />
                    )}
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleSave(setting)}
                        disabled={updateMut.isPending}
                        className="flex items-center gap-1.5 px-2.5 h-7 rounded-[var(--radius-sm)] text-[10px] font-semibold text-accent-green border border-accent-green/20 hover:bg-accent-green/10 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        <Save className="h-3 w-3" />
                        Save
                      </button>
                      <button
                        onClick={cancelEdit}
                        className="flex items-center gap-1.5 px-2.5 h-7 rounded-[var(--radius-sm)] text-[10px] font-semibold text-muted border border-border-subtle hover:text-secondary transition-all cursor-pointer"
                      >
                        <X className="h-3 w-3" />
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <pre className="text-xs font-mono text-accent-cyan bg-elevated/50 rounded-[var(--radius-sm)] px-3 py-2 overflow-x-auto whitespace-pre-wrap break-all">
                    {formatTypedValue(setting)}
                  </pre>
                )}
              </div>
            </motion.div>
          );
        })}

        {(settings ?? []).length === 0 && (
          <div className="py-12 text-center text-sm text-muted">
            {isLoading ? "Loading settings..." : "No settings configured"}
          </div>
        )}
      </motion.div>
    </div>
  );
}
