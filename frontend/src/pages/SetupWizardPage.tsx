import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "motion/react";
import {
  Server,
  Cpu,
  ShieldCheck,
  Loader2,
  ArrowRight,
  ChevronDown,
} from "lucide-react";
import { toast } from "sonner";
import { useApplySetup } from "@/hooks/use-setup";
import GlitchText from "@/components/ui/GlitchText";
import { cn } from "@/lib/cn";

type FieldType = "text" | "password" | "boolean";

interface Field {
  key: string;
  label: string;
  type: FieldType;
  placeholder?: string;
  required?: boolean;
  hint?: string;
}

// Mirrors the wizard keys in db/config_registry.py.
const PROXMOX_FIELDS: Field[] = [
  { key: "proxmox.host", label: "Proxmox Host / IP", type: "text", placeholder: "192.168.1.57", required: true },
  { key: "proxmox.node", label: "Node Name", type: "text", placeholder: "proxmox", required: true },
  { key: "proxmox.token_id", label: "API Token ID", type: "text", placeholder: "root@pam!privatecloud", hint: "Preferred auth — Proxmox → Datacenter → Permissions → API Tokens" },
  { key: "proxmox.token_secret", label: "API Token Secret", type: "password", placeholder: "xxxxxxxx-xxxx-xxxx" },
  { key: "proxmox.verify_ssl", label: "Verify TLS certificate", type: "boolean", hint: "Leave off for self-signed lab certificates" },
];

const LLM_FIELDS: Field[] = [
  { key: "llm.api_key", label: "API Key", type: "password", placeholder: "sk-or-v1-…", hint: "OpenRouter / OpenAI key for AI ChatOps + the RAG assistant" },
  { key: "llm.base_url", label: "Base URL", type: "text", placeholder: "https://openrouter.ai/api/v1" },
  { key: "llm.model", label: "Model", type: "text", placeholder: "openai/gpt-4o-mini" },
];

const ADVANCED_FIELDS: Field[] = [
  { key: "vm.default_password", label: "Linux VM default password", type: "password" },
  { key: "vm.windows_username", label: "Windows VM username", type: "text" },
  { key: "vm.windows_password", label: "Windows VM password", type: "password" },
  { key: "guacamole.public_url", label: "Guacamole public URL", type: "text", placeholder: "http://<host>:9080/guacamole" },
];

const ALL_FIELDS = [...PROXMOX_FIELDS, ...LLM_FIELDS, ...ADVANCED_FIELDS];

export default function SetupWizardPage() {
  const navigate = useNavigate();
  const apply = useApplySetup();

  const [values, setValues] = useState<Record<string, string | boolean>>({
    "proxmox.verify_ssl": false,
    "proxmox.node": "proxmox",
    "llm.base_url": "https://openrouter.ai/api/v1",
    "llm.model": "openai/gpt-4o-mini",
  });
  const [showAdvanced, setShowAdvanced] = useState(false);

  function setField(key: string, value: string | boolean) {
    setValues((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit() {
    const missing = [...PROXMOX_FIELDS, ...LLM_FIELDS].filter(
      (f) => f.required && !String(values[f.key] ?? "").trim(),
    );
    if (missing.length > 0) {
      toast.error(`Required: ${missing.map((m) => m.label).join(", ")}`);
      return;
    }

    const settings: Record<string, unknown> = {};
    for (const f of ALL_FIELDS) {
      const v = values[f.key];
      if (f.type === "boolean") {
        if (v !== undefined) settings[f.key] = Boolean(v);
      } else if (typeof v === "string" && v.trim() !== "") {
        settings[f.key] = v.trim();
      }
    }

    try {
      const res = await apply.mutateAsync({ settings, testConnection: true });
      if (res.proxmox_ok === false) {
        toast.error(`Saved, but Proxmox test failed: ${res.error ?? "unknown error"}`);
      }
      if (res.completed) {
        toast.success("Setup complete — welcome to PrivateCloud!");
        navigate("/", { replace: true });
      } else {
        toast.error("Saved, but required connector fields are still missing.");
      }
    } catch {
      toast.error("Failed to apply setup. Check the values and try again.");
    }
  }

  return (
    <div className="min-h-dvh bg-deepest text-primary py-10 px-4">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        className="max-w-2xl mx-auto"
      >
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-[var(--radius-lg)] bg-accent-cyan/10 border border-accent-cyan/20 mb-4">
            <ShieldCheck className="h-6 w-6 text-accent-cyan" />
          </div>
          <GlitchText
            text="First-run Setup"
            className="text-3xl font-bold tracking-tight"
          />
          <p className="text-sm text-muted mt-2" style={{ fontFamily: "var(--font-body)" }}>
            Connect your hypervisor and AI provider. These are stored securely in
            the database (secrets encrypted) — no .env editing required.
          </p>
        </div>

        {/* Proxmox connector */}
        <Section icon={<Server className="h-4 w-4" />} title="Proxmox Connector" subtitle="Required">
          {PROXMOX_FIELDS.map((f) => (
            <FieldRow key={f.key} field={f} value={values[f.key]} onChange={setField} />
          ))}
        </Section>

        {/* LLM provider */}
        <Section icon={<Cpu className="h-4 w-4" />} title="AI Provider" subtitle="For ChatOps + RAG">
          {LLM_FIELDS.map((f) => (
            <FieldRow key={f.key} field={f} value={values[f.key]} onChange={setField} />
          ))}
        </Section>

        {/* Advanced (optional) */}
        <button
          onClick={() => setShowAdvanced((v) => !v)}
          className="flex items-center gap-2 text-xs font-medium text-muted hover:text-accent-cyan transition-colors mb-3 cursor-pointer"
        >
          <ChevronDown
            className={cn("h-4 w-4 transition-transform", showAdvanced && "rotate-180")}
          />
          Advanced — VM credentials & remote desktop (optional)
        </button>
        {showAdvanced && (
          <Section icon={<Server className="h-4 w-4" />} title="VM & Remote Access" subtitle="Optional">
            {ADVANCED_FIELDS.map((f) => (
              <FieldRow key={f.key} field={f} value={values[f.key]} onChange={setField} />
            ))}
          </Section>
        )}

        {/* Submit */}
        <button
          onClick={handleSubmit}
          disabled={apply.isPending}
          className="w-full mt-4 flex items-center justify-center gap-2 h-11 rounded-[var(--radius-md)] bg-accent-cyan text-deepest font-semibold text-sm hover:bg-accent-cyan/90 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {apply.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Testing connection & saving…
            </>
          ) : (
            <>
              Test connection & finish setup
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
        <p className="text-[11px] text-muted text-center mt-3">
          You can change any of these later in Admin → Settings.
        </p>
      </motion.div>
    </div>
  );
}

function Section({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="glass-panel rounded-[var(--radius-lg)] p-5 mb-4">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-accent-cyan">{icon}</span>
        <h2 className="text-sm font-semibold text-primary">{title}</h2>
        {subtitle && (
          <span className="text-[10px] uppercase tracking-wider text-muted ml-auto">
            {subtitle}
          </span>
        )}
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function FieldRow({
  field,
  value,
  onChange,
}: {
  field: Field;
  value: string | boolean | undefined;
  onChange: (key: string, value: string | boolean) => void;
}) {
  if (field.type === "boolean") {
    const on = Boolean(value);
    return (
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-secondary">{field.label}</p>
          {field.hint && <p className="text-[10px] text-muted mt-0.5">{field.hint}</p>}
        </div>
        <button
          type="button"
          onClick={() => onChange(field.key, !on)}
          className={cn(
            "relative h-5 w-9 rounded-full transition-colors cursor-pointer shrink-0",
            on ? "bg-accent-cyan" : "bg-elevated border border-border-subtle",
          )}
        >
          <span
            className={cn(
              "absolute top-0.5 h-4 w-4 rounded-full bg-deepest transition-transform",
              on ? "translate-x-4" : "translate-x-0.5",
            )}
          />
        </button>
      </div>
    );
  }

  return (
    <div>
      <label className="flex items-center gap-1.5 text-xs font-medium text-secondary mb-1">
        {field.label}
        {field.required && <span className="text-accent-magenta">*</span>}
      </label>
      <input
        type={field.type}
        value={(value as string) ?? ""}
        placeholder={field.placeholder}
        onChange={(e) => onChange(field.key, e.target.value)}
        className="w-full px-3 h-9 text-xs font-mono text-primary bg-elevated border border-border-subtle rounded-[var(--radius-sm)] outline-none focus:border-accent-cyan transition-colors"
      />
      {field.hint && <p className="text-[10px] text-muted mt-1">{field.hint}</p>}
    </div>
  );
}
