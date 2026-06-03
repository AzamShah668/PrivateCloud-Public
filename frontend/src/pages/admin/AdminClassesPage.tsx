import { useState } from "react";
import { motion } from "motion/react";
import { GraduationCap, Plus, UserPlus, X, Users, Trash2 } from "lucide-react";
import GlitchText from "@/components/ui/GlitchText";
import Button from "@/components/ui/Button";
import { useAdminUsers } from "@/hooks/use-admin";
import {
  useClasses,
  useClass,
  useCreateClass,
  useEnrollStudents,
  useUnenrollStudent,
} from "@/hooks/use-templates";
import { cn } from "@/lib/cn";

export default function AdminClassesPage() {
  const { data: classes, isLoading } = useClasses();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showCreate, setShowCreate] = useState(false);

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
            text="Classes"
            className="text-2xl font-bold text-primary tracking-tight"
          />
          <p className="text-sm text-muted mt-1" style={{ fontFamily: "var(--font-body)" }}>
            Group students into reusable classes to distribute templates
          </p>
        </div>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus className="h-4 w-4" />
          New Class
        </Button>
      </motion.div>

      {isLoading ? (
        <p className="text-sm text-muted">Loading classes…</p>
      ) : (classes ?? []).length === 0 ? (
        <EmptyState onCreate={() => setShowCreate(true)} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {(classes ?? []).map((c) => (
            <button
              key={c.id}
              onClick={() => setSelectedId(c.id)}
              className="text-left rounded-[var(--radius-lg)] border border-border-subtle bg-elevated/40 p-5 hover:border-accent-amber/40 transition-all cursor-pointer group"
            >
              <div className="flex items-center gap-3 mb-2">
                <div className="h-9 w-9 rounded-[var(--radius-md)] flex items-center justify-center bg-accent-amber/10 border border-accent-amber/20">
                  <GraduationCap className="h-4 w-4 text-accent-amber" />
                </div>
                <span className="font-bold text-primary" style={{ fontFamily: "var(--font-display)" }}>
                  {c.name}
                </span>
              </div>
              {c.description && (
                <p className="text-xs text-muted mb-3 line-clamp-2">{c.description}</p>
              )}
              <div className="flex items-center gap-1.5 text-xs text-secondary">
                <Users className="h-3.5 w-3.5" />
                {c.student_count} student{c.student_count === 1 ? "" : "s"}
              </div>
            </button>
          ))}
        </div>
      )}

      {showCreate && <CreateClassModal onClose={() => setShowCreate(false)} />}
      {selectedId !== null && (
        <ClassDetailModal classId={selectedId} onClose={() => setSelectedId(null)} />
      )}
    </div>
  );
}

function EmptyState({ onCreate }: { onCreate: () => void }) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-dashed border-border-subtle p-12 text-center">
      <GraduationCap className="h-10 w-10 text-muted mx-auto mb-3" />
      <p className="text-secondary mb-4">No classes yet. Create one to start enrolling students.</p>
      <Button size="sm" onClick={onCreate}>
        <Plus className="h-4 w-4" />
        New Class
      </Button>
    </div>
  );
}

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

function CreateClassModal({ onClose }: { onClose: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const createClass = useCreateClass();

  const submit = async () => {
    await createClass.mutateAsync({ name, description: description || undefined });
    onClose();
  };

  return (
    <Modal onClose={onClose}>
      <ModalHeader title="New Class" onClose={onClose} />
      <div className="space-y-4">
        <Field label="Class name">
          <TextInput value={name} onChange={setName} placeholder="ML-Batch-2026" />
        </Field>
        <Field label="Description (optional)">
          <TextInput value={description} onChange={setDescription} placeholder="Spring semester ML lab" />
        </Field>
      </div>
      <div className="flex justify-end gap-2 mt-6">
        <Button variant="secondary" size="sm" onClick={onClose}>Cancel</Button>
        <Button size="sm" loading={createClass.isPending} disabled={name.trim().length < 3} onClick={submit}>
          Create
        </Button>
      </div>
    </Modal>
  );
}

function ClassDetailModal({ classId, onClose }: { classId: number; onClose: () => void }) {
  const { data: cls, isLoading } = useClass(classId);
  const { data: users } = useAdminUsers();
  const enroll = useEnrollStudents();
  const unenroll = useUnenrollStudent();
  const [picked, setPicked] = useState<number[]>([]);

  const enrolledIds = new Set((cls?.students ?? []).map((s) => s.id));
  const candidates = (users ?? []).filter(
    (u) => u.status === "active" && u.role !== "admin" && !enrolledIds.has(u.id),
  );

  const togglePick = (id: number) =>
    setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));

  const doEnroll = async () => {
    if (picked.length === 0) return;
    await enroll.mutateAsync({ classId, studentIds: picked });
    setPicked([]);
  };

  return (
    <Modal onClose={onClose}>
      <ModalHeader title={cls?.name ?? "Class"} onClose={onClose} />
      {isLoading ? (
        <p className="text-sm text-muted">Loading…</p>
      ) : (
        <div className="space-y-5">
          {/* Enrolled students */}
          <div>
            <SectionLabel>Enrolled ({cls?.students.length ?? 0})</SectionLabel>
            {(cls?.students ?? []).length === 0 ? (
              <p className="text-xs text-muted">No students enrolled yet.</p>
            ) : (
              <div className="space-y-1.5">
                {cls?.students.map((s) => (
                  <div key={s.id} className="flex items-center justify-between px-3 h-9 rounded-[var(--radius-md)] bg-elevated/50 border border-border-subtle">
                    <span className="text-sm text-primary">{s.username}</span>
                    <button
                      onClick={() => unenroll.mutate({ classId, studentId: s.id })}
                      className="text-muted hover:text-accent-red transition-colors cursor-pointer"
                      title="Unenroll"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Add students */}
          <div>
            <SectionLabel>Add students</SectionLabel>
            {candidates.length === 0 ? (
              <p className="text-xs text-muted">All active users are already enrolled.</p>
            ) : (
              <div className="space-y-1.5 max-h-52 overflow-y-auto">
                {candidates.map((u) => (
                  <button
                    key={u.id}
                    onClick={() => togglePick(u.id)}
                    className={cn(
                      "flex items-center justify-between w-full px-3 h-9 rounded-[var(--radius-md)] border transition-all cursor-pointer text-sm",
                      picked.includes(u.id)
                        ? "border-accent-amber/50 bg-accent-amber/10 text-accent-amber"
                        : "border-border-subtle bg-elevated/30 text-secondary hover:text-primary",
                    )}
                  >
                    <span>{u.username}</span>
                    {picked.includes(u.id) && <UserPlus className="h-3.5 w-3.5" />}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
      <div className="flex justify-end gap-2 mt-6">
        <Button variant="secondary" size="sm" onClick={onClose}>Close</Button>
        <Button size="sm" loading={enroll.isPending} disabled={picked.length === 0} onClick={doEnroll}>
          Enroll {picked.length > 0 ? `(${picked.length})` : ""}
        </Button>
      </div>
    </Modal>
  );
}

// --- small shared bits ------------------------------------------------------

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

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[10px] font-bold uppercase tracking-[0.12em] text-muted/60 mb-2" style={{ fontFamily: "var(--font-display)" }}>
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
