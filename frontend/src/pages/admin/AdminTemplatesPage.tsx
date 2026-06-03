import { useState } from "react";
import { motion } from "motion/react";
import {
  Copy,
  Plus,
  X,
  Send,
  Archive,
  Cpu,
  MemoryStick,
  Layers,
  HardDriveDownload,
} from "lucide-react";
import GlitchText from "@/components/ui/GlitchText";
import Button from "@/components/ui/Button";
import { useAdminVMs } from "@/hooks/use-admin";
import {
  useTemplates,
  useCreateTemplate,
  useUpdateTemplate,
  useDistributeTemplate,
  useClasses,
  useBatchProgress,
} from "@/hooks/use-templates";
import type { CloneMode, VMTemplate } from "@/api/templates";
import { cn } from "@/lib/cn";

const CLONE_STATUS_STYLES: Record<string, string> = {
  done: "bg-accent-green/10 text-accent-green border-accent-green/20",
  cloning: "bg-accent-blue/10 text-accent-blue border-accent-blue/20",
  queued: "bg-accent-amber/10 text-accent-amber border-accent-amber/20",
  failed: "bg-accent-red/10 text-accent-red border-accent-red/20",
};

export default function AdminTemplatesPage() {
  const { data: templates, isLoading } = useTemplates();
  const [showPublish, setShowPublish] = useState(false);
  const [distributeFor, setDistributeFor] = useState<VMTemplate | null>(null);
  const [activeBatch, setActiveBatch] = useState<number | null>(null);
  const updateTemplate = useUpdateTemplate();

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
            text="Templates"
            className="text-2xl font-bold text-primary tracking-tight"
          />
          <p className="text-sm text-muted mt-1" style={{ fontFamily: "var(--font-body)" }}>
            Publish a pre-configured VM, then clone it to a whole class at once
          </p>
        </div>
        <Button size="sm" onClick={() => setShowPublish(true)}>
          <Plus className="h-4 w-4" />
          Publish Template
        </Button>
      </motion.div>

      {isLoading ? (
        <p className="text-sm text-muted">Loading templates…</p>
      ) : (templates ?? []).length === 0 ? (
        <div className="rounded-[var(--radius-lg)] border border-dashed border-border-subtle p-12 text-center">
          <Copy className="h-10 w-10 text-muted mx-auto mb-3" />
          <p className="text-secondary mb-4">
            No templates yet. Build a VM, install your software, then publish it here.
          </p>
          <Button size="sm" onClick={() => setShowPublish(true)}>
            <Plus className="h-4 w-4" />
            Publish Template
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(templates ?? []).map((t) => (
            <div
              key={t.id}
              className="rounded-[var(--radius-lg)] border border-border-subtle bg-elevated/40 p-5 flex flex-col"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-[var(--radius-md)] flex items-center justify-center bg-accent-amber/10 border border-accent-amber/20">
                    <Copy className="h-4 w-4 text-accent-amber" />
                  </div>
                  <div>
                    <p className="font-bold text-primary" style={{ fontFamily: "var(--font-display)" }}>
                      {t.name}
                    </p>
                    <p className="text-[11px] text-muted font-mono">
                      {t.os_choice} · vmid {t.source_vmid}
                    </p>
                  </div>
                </div>
                <ModeBadge mode={t.clone_mode} />
              </div>

              {t.description && <p className="text-xs text-muted mb-3 line-clamp-2">{t.description}</p>}

              <div className="flex items-center gap-3 text-[11px] text-secondary mb-4 mt-auto pt-2">
                <span className="flex items-center gap-1"><Cpu className="h-3 w-3" />{t.default_cpu} vCPU</span>
                <span className="flex items-center gap-1"><MemoryStick className="h-3 w-3" />{t.default_ram_mb} MB</span>
                <span className={cn("ml-auto uppercase tracking-wide text-[9px] px-1.5 py-0.5 rounded border",
                  t.status === "published" ? "text-accent-green border-accent-green/30"
                  : t.status === "archived" ? "text-muted border-border-subtle"
                  : "text-accent-amber border-accent-amber/30")}>
                  {t.status}
                </span>
              </div>

              <div className="flex gap-2">
                <Button
                  size="sm"
                  className="flex-1"
                  disabled={t.status === "archived"}
                  onClick={() => setDistributeFor(t)}
                >
                  <Send className="h-3.5 w-3.5" />
                  Distribute
                </Button>
                {t.status !== "archived" && (
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => updateTemplate.mutate({ id: t.id, body: { status: "archived" } })}
                    title="Archive"
                  >
                    <Archive className="h-3.5 w-3.5" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {showPublish && <PublishModal onClose={() => setShowPublish(false)} />}
      {distributeFor && (
        <DistributeModal
          template={distributeFor}
          onClose={() => setDistributeFor(null)}
          onDistributed={(batchId) => {
            setDistributeFor(null);
            setActiveBatch(batchId);
          }}
        />
      )}
      {activeBatch !== null && (
        <BatchProgressModal batchId={activeBatch} onClose={() => setActiveBatch(null)} />
      )}
    </div>
  );
}

function ModeBadge({ mode }: { mode: CloneMode }) {
  return (
    <span
      className={cn(
        "flex items-center gap-1 text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded border",
        mode === "linked"
          ? "text-accent-cyan border-accent-cyan/30"
          : "text-accent-blue border-accent-blue/30",
      )}
    >
      <Layers className="h-2.5 w-2.5" />
      {mode}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Publish modal — turn an existing "done" VM into a template
// ---------------------------------------------------------------------------

function PublishModal({ onClose }: { onClose: () => void }) {
  const { data: vms } = useAdminVMs();
  const createTemplate = useCreateTemplate();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [vmJobId, setVmJobId] = useState<number | null>(null);
  const [cloneMode, setCloneMode] = useState<CloneMode>("full");
  const [cpu, setCpu] = useState(2);
  const [ram, setRam] = useState(2048);

  const eligible = (vms ?? []).filter((v) => v.status === "done");

  const submit = async () => {
    if (!vmJobId) return;
    await createTemplate.mutateAsync({
      name,
      vm_job_id: vmJobId,
      description: description || undefined,
      clone_mode: cloneMode,
      default_cpu: cpu,
      default_ram_mb: ram,
    });
    onClose();
  };

  const busy = createTemplate.isPending;
  const guardedClose = () => {
    if (!busy) onClose();
  };

  return (
    <Modal onClose={guardedClose}>
      <ModalHeader title="Publish Template" onClose={guardedClose} />
      <div className="space-y-4">
        <Field label="Template name">
          <TextInput value={name} onChange={setName} placeholder="ML Lab — PyTorch ready" />
        </Field>
        <Field label="Description (optional)">
          <TextInput value={description} onChange={setDescription} placeholder="Ubuntu 22.04 with CUDA + PyTorch preinstalled" />
        </Field>

        <Field label="Source VM (must be a finished 'done' VM)">
          {eligible.length === 0 ? (
            <p className="text-xs text-accent-amber">No finished VMs available to publish.</p>
          ) : (
            <div className="space-y-1.5 max-h-44 overflow-y-auto">
              {eligible.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setVmJobId(v.id)}
                  className={cn(
                    "flex items-center justify-between w-full px-3 h-10 rounded-[var(--radius-md)] border transition-all cursor-pointer text-sm",
                    vmJobId === v.id
                      ? "border-accent-amber/50 bg-accent-amber/10 text-accent-amber"
                      : "border-border-subtle bg-elevated/30 text-secondary hover:text-primary",
                  )}
                >
                  <span>{v.vm_name} <span className="text-muted font-mono text-xs">({v.os_choice})</span></span>
                  <span className="text-muted font-mono text-xs">vmid {v.vmid}</span>
                </button>
              ))}
            </div>
          )}
        </Field>

        <Field label="Clone mode">
          <div className="grid grid-cols-2 gap-2">
            <ModeOption
              active={cloneMode === "full"}
              onClick={() => setCloneMode("full")}
              title="Full clone"
              desc="Independent disk. Robust, more storage."
            />
            <ModeOption
              active={cloneMode === "linked"}
              onClick={() => setCloneMode("linked")}
              title="Linked clone"
              desc="Near-instant, tiny disk. Freezes source."
            />
          </div>
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="Default vCPU">
            <NumberInput value={cpu} onChange={setCpu} min={1} max={16} />
          </Field>
          <Field label="Default RAM (MB)">
            <NumberInput value={ram} onChange={setRam} min={512} max={65536} step={512} />
          </Field>
        </div>
      </div>

      <div className="flex justify-end gap-2 mt-6">
        <Button variant="secondary" size="sm" disabled={busy} onClick={guardedClose}>Cancel</Button>
        <Button
          size="sm"
          loading={busy}
          disabled={name.trim().length < 3 || !vmJobId}
          onClick={submit}
        >
          Publish
        </Button>
      </div>
    </Modal>
  );
}

function ModeOption({
  active,
  onClick,
  title,
  desc,
}: {
  active: boolean;
  onClick: () => void;
  title: string;
  desc: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "text-left px-3 py-2.5 rounded-[var(--radius-md)] border transition-all cursor-pointer",
        active
          ? "border-accent-amber/50 bg-accent-amber/10"
          : "border-border-subtle bg-elevated/30 hover:border-secondary/30",
      )}
    >
      <p className={cn("text-sm font-medium", active ? "text-accent-amber" : "text-primary")}>{title}</p>
      <p className="text-[10px] text-muted mt-0.5 leading-snug">{desc}</p>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Distribute modal — clone the template to a class
// ---------------------------------------------------------------------------

function DistributeModal({
  template,
  onClose,
  onDistributed,
}: {
  template: VMTemplate;
  onClose: () => void;
  onDistributed: (batchId: number) => void;
}) {
  const { data: classes } = useClasses();
  const distribute = useDistributeTemplate();
  const [classId, setClassId] = useState<number | null>(null);
  const [cpu, setCpu] = useState(template.default_cpu);
  const [ram, setRam] = useState(template.default_ram_mb);

  const submit = async () => {
    if (!classId) return;
    const batch = await distribute.mutateAsync({
      id: template.id,
      body: { class_id: classId, cpu_cores: cpu, ram_mb: ram, clone_mode: template.clone_mode },
    });
    onDistributed(batch.id);
  };

  const busy = distribute.isPending;
  const guardedClose = () => {
    if (!busy) onClose();
  };

  return (
    <Modal onClose={guardedClose}>
      <ModalHeader title={`Distribute "${template.name}"`} onClose={guardedClose} />
      <p className="text-xs text-muted mb-4">
        One {template.clone_mode} clone will be created for every active student in the
        selected class. Clones bypass the daily quota.
      </p>
      <div className="space-y-4">
        <Field label="Class">
          {(classes ?? []).length === 0 ? (
            <p className="text-xs text-accent-amber">No classes yet — create one first.</p>
          ) : (
            <div className="space-y-1.5 max-h-44 overflow-y-auto">
              {(classes ?? []).map((c) => (
                <button
                  key={c.id}
                  onClick={() => setClassId(c.id)}
                  className={cn(
                    "flex items-center justify-between w-full px-3 h-10 rounded-[var(--radius-md)] border transition-all cursor-pointer text-sm",
                    classId === c.id
                      ? "border-accent-amber/50 bg-accent-amber/10 text-accent-amber"
                      : "border-border-subtle bg-elevated/30 text-secondary hover:text-primary",
                  )}
                >
                  <span>{c.name}</span>
                  <span className="text-muted text-xs">{c.student_count} students</span>
                </button>
              ))}
            </div>
          )}
        </Field>

        <div className="grid grid-cols-2 gap-3">
          <Field label="vCPU per clone">
            <NumberInput value={cpu} onChange={setCpu} min={1} max={16} />
          </Field>
          <Field label="RAM per clone (MB)">
            <NumberInput value={ram} onChange={setRam} min={512} max={65536} step={512} />
          </Field>
        </div>
      </div>

      <div className="flex justify-end gap-2 mt-6">
        <Button variant="secondary" size="sm" disabled={busy} onClick={guardedClose}>Cancel</Button>
        <Button
          size="sm"
          loading={busy}
          disabled={!classId}
          onClick={submit}
        >
          <HardDriveDownload className="h-3.5 w-3.5" />
          Clone to class
        </Button>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Batch progress modal — live per-student clone status
// ---------------------------------------------------------------------------

function BatchProgressModal({ batchId, onClose }: { batchId: number; onClose: () => void }) {
  const { data: batch } = useBatchProgress(batchId);
  const done = (batch?.clones ?? []).filter((c) => c.status === "done").length;
  const failed = (batch?.clones ?? []).filter((c) => c.status === "failed").length;

  return (
    <Modal onClose={onClose}>
      <ModalHeader title="Distribution progress" onClose={onClose} />
      {!batch ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center gap-4 text-xs">
            <span className="text-accent-green">{done} done</span>
            {failed > 0 && <span className="text-accent-red">{failed} failed</span>}
            <span className="text-muted ml-auto uppercase tracking-wide">{batch.status}</span>
          </div>

          {/* Progress bar */}
          <div className="h-2 rounded-full bg-elevated overflow-hidden">
            <div
              className="h-full bg-accent-green transition-all duration-500"
              style={{ width: `${batch.total ? (done / batch.total) * 100 : 0}%` }}
            />
          </div>

          <div className="space-y-1.5 max-h-72 overflow-y-auto">
            {batch.clones.map((c) => (
              <div key={c.id} className="flex items-center justify-between px-3 h-10 rounded-[var(--radius-md)] bg-elevated/40 border border-border-subtle">
                <div className="flex flex-col">
                  <span className="text-sm text-primary">{c.username}</span>
                  {c.vm_ip && <span className="text-[10px] text-muted font-mono">{c.vm_ip}</span>}
                  {c.error_message && <span className="text-[10px] text-accent-red truncate max-w-[220px]">{c.error_message}</span>}
                </div>
                <span className={cn("text-[9px] uppercase tracking-wide px-1.5 py-0.5 rounded border", CLONE_STATUS_STYLES[c.status])}>
                  {c.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
      <div className="flex justify-end mt-6">
        <Button variant="secondary" size="sm" onClick={onClose}>Close</Button>
      </div>
    </Modal>
  );
}

// ---------------------------------------------------------------------------
// Shared modal primitives
// ---------------------------------------------------------------------------

function Modal({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm" onClick={onClose}>
      <motion.div
        initial={{ opacity: 0, scale: 0.96, y: 10 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
        className="w-full max-w-lg rounded-[var(--radius-lg)] border border-border-subtle bg-surface p-6 max-h-[85vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {children}
      </motion.div>
    </div>
  );
}

function ModalHeader({ title, onClose }: { title: string; onClose: () => void }) {
  return (
    <div className="flex items-center justify-between mb-5">
      <h2 className="text-lg font-bold text-primary" style={{ fontFamily: "var(--font-display)" }}>
        {title}
      </h2>
      <button onClick={onClose} className="text-muted hover:text-primary transition-colors cursor-pointer">
        <X className="h-5 w-5" />
      </button>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs text-muted mb-1.5" style={{ fontFamily: "var(--font-body)" }}>
        {label}
      </label>
      {children}
    </div>
  );
}

function TextInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full h-10 px-3 rounded-[var(--radius-md)] bg-elevated/50 border border-border-subtle text-sm text-primary placeholder:text-muted outline-none focus:border-accent-amber/40 transition-colors"
      style={{ fontFamily: "var(--font-body)" }}
    />
  );
}

function NumberInput({
  value,
  onChange,
  min,
  max,
  step = 1,
}: {
  value: number;
  onChange: (v: number) => void;
  min: number;
  max: number;
  step?: number;
}) {
  return (
    <input
      type="number"
      value={value}
      min={min}
      max={max}
      step={step}
      onChange={(e) => onChange(Number(e.target.value))}
      className="w-full h-10 px-3 rounded-[var(--radius-md)] bg-elevated/50 border border-border-subtle text-sm text-primary outline-none focus:border-accent-amber/40 transition-colors font-mono"
    />
  );
}
