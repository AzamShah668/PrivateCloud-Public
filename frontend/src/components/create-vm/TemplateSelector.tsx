import { motion } from "motion/react";
import { Boxes, Cpu, MemoryStick, Loader2, AlertTriangle } from "lucide-react";
import type { VMTemplate } from "@/api/templates";
import { cn } from "@/lib/cn";

interface TemplateSelectorProps {
  templates: VMTemplate[];
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}

function formatRam(mb: number): string {
  return mb >= 1024
    ? `${(mb / 1024).toFixed(mb % 1024 === 0 ? 0 : 1)} GB`
    : `${mb} MB`;
}

function TemplateCard({
  template,
  selected,
  onClick,
  index,
}: {
  template: VMTemplate;
  selected: boolean;
  onClick: () => void;
  index: number;
}) {
  const isPublished = template.status === "published" && template.template_vmid != null;
  const isBuilding = template.status === "building";
  const isFailed = template.status === "failed";
  const disabled = !isPublished;

  return (
    <motion.button
      type="button"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      className={cn(
        "relative flex flex-col gap-3 p-4 rounded-xl text-left transition-all duration-300",
        "bg-surface border backdrop-blur-md overflow-hidden group",
        disabled && "opacity-60 cursor-not-allowed",
        selected
          ? "border-accent-cyan/60 shadow-[0_0_30px_-5px_rgba(10,239,255,0.35)] bg-accent-cyan/[0.03]"
          : !disabled && "border-border-subtle/50 hover:border-accent-cyan/40 hover:bg-elevated/80",
        disabled && "border-border-subtle/40",
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div
            className={cn(
              "w-9 h-9 rounded-lg flex items-center justify-center shrink-0 border border-white/10",
              "bg-gradient-to-br from-cyan-500/80 to-blue-600/80",
            )}
          >
            <Boxes className="h-4 w-4 text-white" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-primary truncate group-hover:text-white">
              {template.name}
            </p>
            <p className="text-[11px] font-mono text-secondary truncate">{template.os_choice}</p>
          </div>
        </div>

        {isPublished && (
          <span className="text-[10px] font-mono uppercase tracking-wider text-accent-green/90 border border-accent-green/30 rounded px-1.5 py-0.5 shrink-0">
            Ready
          </span>
        )}
        {isBuilding && (
          <span className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider text-accent-amber border border-accent-amber/30 rounded px-1.5 py-0.5 shrink-0">
            <Loader2 className="h-3 w-3 animate-spin" /> Building
          </span>
        )}
        {isFailed && (
          <span className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider text-accent-red border border-accent-red/30 rounded px-1.5 py-0.5 shrink-0">
            <AlertTriangle className="h-3 w-3" /> Failed
          </span>
        )}
      </div>

      <div className="flex items-center gap-4 text-xs text-secondary font-mono">
        <span className="flex items-center gap-1">
          <Cpu className="h-3.5 w-3.5" /> {template.default_cpu} vCPU
        </span>
        <span className="flex items-center gap-1">
          <MemoryStick className="h-3.5 w-3.5" /> {formatRam(template.default_ram_mb)}
        </span>
      </div>

      {selected && (
        <motion.div
          layoutId="template-active-border"
          className="absolute inset-0 rounded-xl border-2 border-accent-cyan/80 pointer-events-none"
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
        />
      )}
    </motion.button>
  );
}

export default function TemplateSelector({
  templates,
  selectedId,
  onSelect,
}: TemplateSelectorProps) {
  // Hide archived; show the rest (published deployable, building/failed informational).
  const visible = templates.filter((t) => t.status !== "archived");

  if (visible.length === 0) return null;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-6">
        <label className="block text-sm font-medium text-accent-cyan uppercase tracking-widest opacity-80">
          Templates
        </label>
        {selectedId !== null && (
          <button
            type="button"
            onClick={() => onSelect(null)}
            className="text-[11px] font-mono text-secondary hover:text-accent-cyan transition-colors"
          >
            Clear selection
          </button>
        )}
      </div>
      <p className="text-xs text-secondary -mt-4 mb-5">
        Deploy a ready-made VM from a pre-configured template. Selecting one overrides the
        OS choice above.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {visible.map((t, i) => (
          <TemplateCard
            key={t.id}
            template={t}
            selected={selectedId === t.id}
            onClick={() => onSelect(t.id)}
            index={i}
          />
        ))}
      </div>
    </div>
  );
}
