import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion, AnimatePresence } from "motion/react";
import {
  Server,
  Cpu,
  ShieldCheck,
  Loader2,
  ArrowRight,
  ChevronDown,
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Eye,
  EyeOff,
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

// ── Provider presets ────────────────────────────────────────────────────────
interface LLMProvider {
  id: string;
  name: string;
  baseUrl: string;          // auto-filled when selected
  modelPlaceholder: string; // shown as placeholder in the model field
  modelDefault: string;     // auto-filled when selected
  hint: string;
  apiKeyHint: string;
}

const LLM_PROVIDERS: LLMProvider[] = [
  {
    id: "openai",
    name: "OpenAI",
    baseUrl: "",                      // OpenAI SDK default — leave blank
    modelPlaceholder: "gpt-4o-mini",
    modelDefault: "gpt-4o-mini",
    hint: "Direct OpenAI API — no base URL needed",
    apiKeyHint: "Your OpenAI API key (starts with sk-…). Get one at platform.openai.com/api-keys",
  },
  {
    id: "openrouter",
    name: "OpenRouter",
    baseUrl: "https://openrouter.ai/api/v1",
    modelPlaceholder: "openai/gpt-4o-mini",
    modelDefault: "openai/gpt-4o-mini",
    hint: "Access 200+ models via OpenRouter (OpenAI, Anthropic, Google, etc.)",
    apiKeyHint: "Your OpenRouter API key (starts with sk-or-…). Get one at openrouter.ai/keys",
  },
  {
    id: "custom",
    name: "Custom / Self-hosted",
    baseUrl: "",
    modelPlaceholder: "my-model-name",
    modelDefault: "",
    hint: "Any OpenAI-compatible API (vLLM, Ollama, LiteLLM, etc.)",
    apiKeyHint: "API key for your custom endpoint",
  },
];

// Safe default for TypeScript — guaranteed non-undefined.
const DEFAULT_PROVIDER: LLMProvider = LLM_PROVIDERS[0] as LLMProvider;

// Mirrors the wizard keys in db/config_registry.py.
const PROXMOX_FIELDS: Field[] = [
  {
    key: "proxmox.host",
    label: "Proxmox Host / IP",
    type: "text",
    placeholder: "192.168.1.57",
    required: true,
    hint: "The IP or hostname of your Proxmox VE server",
  },
  {
    key: "proxmox.node",
    label: "Node Name",
    type: "text",
    placeholder: "proxmox",
    required: true,
    hint: "The node name shown in Proxmox UI → Datacenter → your node",
  },
  {
    key: "proxmox.token_id",
    label: "API Token ID",
    type: "text",
    placeholder: "root@pam!privatecloud",
    hint: "Format: user@realm!tokenname — create at Datacenter → Permissions → API Tokens",
  },
  {
    key: "proxmox.token_secret",
    label: "API Token Secret",
    type: "password",
    placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    hint: "The UUID shown once when you created the token",
  },
  {
    key: "proxmox.verify_ssl",
    label: "Verify TLS certificate",
    type: "boolean",
    hint: "Turn OFF for self-signed certs (common in local labs)",
  },
];

const ADVANCED_FIELDS: Field[] = [
  {
    key: "vm.default_password",
    label: "Linux VM default password",
    type: "password",
    hint: "SSH password baked into your Linux golden image",
  },
  {
    key: "vm.windows_username",
    label: "Windows VM username",
    type: "text",
    hint: "Username for the Windows golden image",
  },
  {
    key: "vm.windows_password",
    label: "Windows VM password",
    type: "password",
    hint: "Password for the Windows golden image",
  },
  {
    key: "guacamole.public_url",
    label: "Guacamole public URL",
    type: "text",
    placeholder: "http://<host>:9080/guacamole",
    hint: "Browser-accessible Apache Guacamole URL for remote desktop",
  },
];

// LLM fields are rendered manually (with the provider selector), so we only
// define them here for the submit handler.
const LLM_KEYS = ["llm.api_key", "llm.base_url", "llm.model"];

const ALL_FIELD_KEYS = [
  ...PROXMOX_FIELDS.map((f) => f.key),
  ...LLM_KEYS,
  ...ADVANCED_FIELDS.map((f) => f.key),
];

export default function SetupWizardPage() {
  const navigate = useNavigate();
  const apply = useApplySetup();

  const [values, setValues] = useState<Record<string, string | boolean>>({
    "proxmox.verify_ssl": false,
    "proxmox.node": "proxmox",
  });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState<string>("openai");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  const currentProvider = LLM_PROVIDERS.find((p) => p.id === selectedProvider) ?? DEFAULT_PROVIDER;

  function setField(key: string, value: string | boolean) {
    setValues((prev) => ({ ...prev, [key]: value }));
    if (submitError) setSubmitError(null);
  }

  function handleProviderChange(providerId: string) {
    setSelectedProvider(providerId);
    const provider = LLM_PROVIDERS.find((p) => p.id === providerId);
    if (provider) {
      setValues((prev) => ({
        ...prev,
        "llm.base_url": provider.baseUrl,
        "llm.model": provider.modelDefault,
      }));
    }
  }

  async function handleSubmit() {
    setSubmitError(null);
    setSubmitSuccess(false);

    // Validate required Proxmox fields
    const missingProxmox = PROXMOX_FIELDS.filter(
      (f) => f.required && !String(values[f.key] ?? "").trim(),
    );
    if (missingProxmox.length > 0) {
      setSubmitError(
        `Missing required Proxmox fields: ${missingProxmox.map((m) => m.label).join(", ")}`,
      );
      toast.error(
        `Required: ${missingProxmox.map((m) => m.label).join(", ")}`,
      );
      return;
    }

    // Build settings payload
    const settings: Record<string, unknown> = {};
    for (const key of ALL_FIELD_KEYS) {
      const v = values[key];
      if (key === "proxmox.verify_ssl") {
        settings[key] = Boolean(v);
      } else if (typeof v === "string" && v.trim() !== "") {
        settings[key] = v.trim();
      }
    }

    try {
      const res = await apply.mutateAsync({
        settings,
        testConnection: true,
      });

      if (res.proxmox_ok === false) {
        const errMsg = res.error ?? "Unknown connection error";
        setSubmitError(`Proxmox connection test failed: ${errMsg}`);
        toast.error(`Proxmox test failed — see error below`, {
          duration: 6000,
        });
        return;
      }

      if (res.completed) {
        setSubmitSuccess(true);
        toast.success("Setup complete — welcome to PrivateCloud! 🎉");
        setTimeout(() => navigate("/", { replace: true }), 1200);
      } else {
        setSubmitError(
          "Settings saved, but some required fields are still missing. Please fill them in above.",
        );
      }
    } catch {
      setSubmitError(
        "Could not reach the backend. Is the server running? Check your browser console for details.",
      );
      toast.error("Failed to apply setup — check the server.");
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
        {/* ── Header ──────────────────────────────────────────────────── */}
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center h-12 w-12 rounded-[var(--radius-lg)] bg-accent-cyan/10 border border-accent-cyan/20 mb-4">
            <ShieldCheck className="h-6 w-6 text-accent-cyan" />
          </div>
          <GlitchText
            text="First-run Setup"
            className="text-3xl font-bold tracking-tight"
          />
          <p
            className="text-sm text-muted mt-2 max-w-md mx-auto"
            style={{ fontFamily: "var(--font-body)" }}
          >
            Connect your Proxmox hypervisor and (optionally) an AI provider.
            Everything is stored securely in the database — secrets are encrypted
            at rest.
          </p>
        </div>

        {/* ── Success banner ──────────────────────────────────────────── */}
        <AnimatePresence>
          {submitSuccess && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-4 flex items-center gap-2 px-4 py-3 rounded-[var(--radius-md)] bg-green-500/10 border border-green-500/30 text-green-400 text-xs font-medium"
            >
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              Setup complete! Redirecting to the dashboard…
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Error banner ────────────────────────────────────────────── */}
        <AnimatePresence>
          {submitError && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-4 flex items-start gap-2 px-4 py-3 rounded-[var(--radius-md)] bg-red-500/10 border border-red-500/30 text-red-400 text-xs font-medium"
            >
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span className="break-words whitespace-pre-wrap">
                {submitError}
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Proxmox Connector ───────────────────────────────────────── */}
        <Section
          icon={<Server className="h-4 w-4" />}
          title="Proxmox Connector"
          subtitle="Required"
        >
          {PROXMOX_FIELDS.map((f) => (
            <FieldRow
              key={f.key}
              field={f}
              value={values[f.key]}
              onChange={setField}
            />
          ))}
        </Section>

        {/* ── AI Provider ─────────────────────────────────────────────── */}
        <Section
          icon={<Cpu className="h-4 w-4" />}
          title="AI Provider"
          subtitle="Optional — for ChatOps + RAG"
        >
          {/* Provider selector */}
          <div className="mb-4">
            <label className="flex items-center gap-1.5 text-xs font-medium text-secondary mb-2">
              Provider
              <Tooltip text="Choose your LLM provider. The base URL and model will be auto-filled." />
            </label>
            <div className="grid grid-cols-3 gap-2">
              {LLM_PROVIDERS.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleProviderChange(p.id)}
                  className={cn(
                    "px-3 py-2.5 rounded-[var(--radius-sm)] text-xs font-medium transition-all cursor-pointer border",
                    selectedProvider === p.id
                      ? "bg-accent-cyan/15 border-accent-cyan text-accent-cyan shadow-[0_0_12px_rgba(0,255,255,0.08)]"
                      : "bg-elevated border-border-subtle text-muted hover:text-primary hover:border-border-subtle/80",
                  )}
                >
                  {p.name}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-muted mt-1.5">{currentProvider.hint}</p>
          </div>

          {/* API Key */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-medium text-secondary mb-1">
              API Key
            </label>
            <PasswordInput
              value={(values["llm.api_key"] as string) ?? ""}
              placeholder={
                selectedProvider === "openai"
                  ? "sk-…"
                  : selectedProvider === "openrouter"
                    ? "sk-or-v1-…"
                    : "your-api-key"
              }
              onChange={(v) => setField("llm.api_key", v)}
            />
            <p className="text-[10px] text-muted mt-1">
              {currentProvider.apiKeyHint}
            </p>
          </div>

          {/* Base URL — only show for OpenRouter or Custom */}
          {selectedProvider !== "openai" && (
            <div>
              <label className="flex items-center gap-1.5 text-xs font-medium text-secondary mb-1">
                Base URL
                {selectedProvider === "openrouter" && (
                  <span className="text-[10px] text-accent-cyan font-normal">
                    (auto-filled)
                  </span>
                )}
              </label>
              <input
                type="text"
                value={(values["llm.base_url"] as string) ?? ""}
                placeholder={
                  selectedProvider === "custom"
                    ? "https://your-server.com/v1"
                    : currentProvider.baseUrl
                }
                onChange={(e) => setField("llm.base_url", e.target.value)}
                className="w-full px-3 h-9 text-xs font-mono text-primary bg-elevated border border-border-subtle rounded-[var(--radius-sm)] outline-none focus:border-accent-cyan transition-colors"
              />
              {selectedProvider === "openrouter" && (
                <p className="text-[10px] text-muted mt-1">
                  Pre-filled for OpenRouter. Don't change this unless you know
                  what you're doing.
                </p>
              )}
              {selectedProvider === "custom" && (
                <p className="text-[10px] text-muted mt-1">
                  Must be an OpenAI-compatible endpoint (e.g.
                  http://localhost:11434/v1 for Ollama)
                </p>
              )}
            </div>
          )}

          {selectedProvider === "openai" && (
            <p className="text-[10px] text-muted px-1 py-1.5 bg-accent-cyan/5 rounded-[var(--radius-sm)] border border-accent-cyan/10">
              💡 No base URL needed — the system uses the official OpenAI endpoint
              automatically.
            </p>
          )}

          {/* Model */}
          <div>
            <label className="flex items-center gap-1.5 text-xs font-medium text-secondary mb-1">
              Model
            </label>
            <input
              type="text"
              value={(values["llm.model"] as string) ?? ""}
              placeholder={currentProvider.modelPlaceholder}
              onChange={(e) => setField("llm.model", e.target.value)}
              className="w-full px-3 h-9 text-xs font-mono text-primary bg-elevated border border-border-subtle rounded-[var(--radius-sm)] outline-none focus:border-accent-cyan transition-colors"
            />
            <p className="text-[10px] text-muted mt-1">
              {selectedProvider === "openai"
                ? "e.g. gpt-4o-mini, gpt-4o, gpt-4-turbo"
                : selectedProvider === "openrouter"
                  ? "e.g. openai/gpt-4o-mini, anthropic/claude-3.5-sonnet, google/gemini-2.5-flash"
                  : "The model identifier for your custom endpoint"}
            </p>
          </div>
        </Section>

        {/* ── Advanced (optional) ─────────────────────────────────────── */}
        <button
          onClick={() => setShowAdvanced((v) => !v)}
          className="flex items-center gap-2 text-xs font-medium text-muted hover:text-accent-cyan transition-colors mb-3 cursor-pointer"
        >
          <ChevronDown
            className={cn(
              "h-4 w-4 transition-transform",
              showAdvanced && "rotate-180",
            )}
          />
          Advanced — VM credentials & remote desktop (optional)
        </button>
        <AnimatePresence>
          {showAdvanced && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
            >
              <Section
                icon={<Server className="h-4 w-4" />}
                title="VM & Remote Access"
                subtitle="Optional"
              >
                {ADVANCED_FIELDS.map((f) => (
                  <FieldRow
                    key={f.key}
                    field={f}
                    value={values[f.key]}
                    onChange={setField}
                  />
                ))}
              </Section>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Submit ──────────────────────────────────────────────────── */}
        <button
          onClick={handleSubmit}
          disabled={apply.isPending || submitSuccess}
          className="w-full mt-4 flex items-center justify-center gap-2 h-11 rounded-[var(--radius-md)] bg-accent-cyan text-deepest font-semibold text-sm hover:bg-accent-cyan/90 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {apply.isPending ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              Testing connection & saving…
            </>
          ) : submitSuccess ? (
            <>
              <CheckCircle2 className="h-4 w-4" />
              Setup complete!
            </>
          ) : (
            <>
              Test connection & finish setup
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
        <p className="text-[11px] text-muted text-center mt-3">
          You can change any of these later in{" "}
          <span className="text-secondary">Admin → Settings</span>.
        </p>
      </motion.div>
    </div>
  );
}

// ─── Reusable components ──────────────────────────────────────────────────────

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

function Tooltip({ text }: { text: string }) {
  return (
    <span className="group relative inline-flex">
      <HelpCircle className="h-3 w-3 text-muted cursor-help" />
      <span className="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 px-2 py-1 rounded bg-elevated border border-border-subtle text-[10px] text-secondary whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-50 shadow-lg">
        {text}
      </span>
    </span>
  );
}

function PasswordInput({
  value,
  placeholder,
  onChange,
}: {
  value: string;
  placeholder: string;
  onChange: (v: string) => void;
}) {
  const [show, setShow] = useState(false);
  return (
    <div className="relative">
      <input
        type={show ? "text" : "password"}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
        className="w-full px-3 pr-9 h-9 text-xs font-mono text-primary bg-elevated border border-border-subtle rounded-[var(--radius-sm)] outline-none focus:border-accent-cyan transition-colors"
      />
      <button
        type="button"
        tabIndex={-1}
        onClick={() => setShow((v) => !v)}
        className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-primary transition-colors cursor-pointer"
      >
        {show ? (
          <EyeOff className="h-3.5 w-3.5" />
        ) : (
          <Eye className="h-3.5 w-3.5" />
        )}
      </button>
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
          {field.hint && (
            <p className="text-[10px] text-muted mt-0.5">{field.hint}</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => onChange(field.key, !on)}
          className={cn(
            "relative h-5 w-9 rounded-full transition-colors cursor-pointer shrink-0",
            on
              ? "bg-accent-cyan"
              : "bg-elevated border border-border-subtle",
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

  if (field.type === "password") {
    return (
      <div>
        <label className="flex items-center gap-1.5 text-xs font-medium text-secondary mb-1">
          {field.label}
          {field.required && <span className="text-accent-magenta">*</span>}
        </label>
        <PasswordInput
          value={(value as string) ?? ""}
          placeholder={field.placeholder ?? ""}
          onChange={(v) => onChange(field.key, v)}
        />
        {field.hint && (
          <p className="text-[10px] text-muted mt-1">{field.hint}</p>
        )}
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
      {field.hint && (
        <p className="text-[10px] text-muted mt-1">{field.hint}</p>
      )}
    </div>
  );
}
