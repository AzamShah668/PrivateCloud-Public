import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { X, Monitor, Loader2, AlertTriangle, ExternalLink } from "lucide-react";
import Button from "@/components/ui/Button";
import { createDesktopSession } from "@/api/vms";

interface GuacamoleModalProps {
  open: boolean;
  onClose: () => void;
  jobId: number;
  vmName: string;
}

export default function GuacamoleModal({ open, onClose, jobId, vmName }: GuacamoleModalProps) {
  const [clientUrl, setClientUrl] = useState<string | null>(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) {
      setClientUrl(null);
      setIframeLoaded(false);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function run() {
      setLoading(true);
      setError(null);
      setClientUrl(null);
      setIframeLoaded(false);
      try {
        const session = await createDesktopSession(jobId);
        if (!cancelled) setClientUrl(session.client_url);
      } catch (e: unknown) {
        if (cancelled) return;
        let msg = "Could not start a remote desktop session.";
        if (e && typeof e === "object" && "response" in e) {
          const res = (e as { response?: { json?: () => Promise<{ detail?: string }> } }).response;
          if (res?.json) {
            try {
              const body = await res.json();
              if (body?.detail) msg = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
            } catch {
              /* ignore */
            }
          }
        } else if (e instanceof Error) msg = e.message;
        setError(msg);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void run();
    return () => {
      cancelled = true;
    };
  }, [open, jobId]);

  async function retry() {
    setLoading(true);
    setError(null);
    setClientUrl(null);
    setIframeLoaded(false);
    try {
      const session = await createDesktopSession(jobId);
      setClientUrl(session.client_url);
    } catch (e: unknown) {
      let msg = "Could not start a remote desktop session.";
      if (e instanceof Error) msg = e.message;
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AnimatePresence
      onExitComplete={() => {
        setClientUrl(null);
        setIframeLoaded(false);
        setError(null);
        setLoading(false);
      }}
    >
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            onClick={onClose}
          />

          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="relative z-10 w-full flex flex-col"
            style={{
              maxWidth: "1100px",
              height: "clamp(520px, 82vh, 800px)",
              background: "rgba(10, 22, 40, 0.98)",
              backdropFilter: "blur(24px)",
              border: "1px solid rgba(10,239,255,0.15)",
              borderRadius: "var(--radius-xl)",
              boxShadow:
                "0 8px 40px rgba(0,0,0,0.7), 0 0 60px rgba(10,239,255,0.05)",
            }}
          >
            <div
              className="absolute top-0 left-8 right-8 h-[1px]"
              style={{
                background:
                  "linear-gradient(90deg, transparent, rgba(10,239,255,0.25), transparent)",
              }}
            />

            <div className="flex items-center justify-between px-6 pt-5 pb-4 shrink-0">
              <div className="flex items-center gap-3">
                <div
                  className="flex items-center justify-center h-8 w-8 rounded-[var(--radius-md)]"
                  style={{ background: "rgba(10,239,255,0.08)", border: "1px solid rgba(10,239,255,0.15)" }}
                >
                  <Monitor className="h-4 w-4 text-accent-cyan" />
                </div>
                <div>
                  <h2
                    className="text-sm font-bold text-primary leading-none"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    Remote Desktop
                  </h2>
                  <p className="text-[10px] text-muted mt-0.5 font-mono">
                    {vmName} · Apache Guacamole (RDP)
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {clientUrl && (
                  <a
                    href={clientUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 h-8 px-3 text-xs font-medium rounded-[var(--radius-md)] text-secondary hover:text-accent-cyan hover:bg-accent-cyan/10 border border-border-subtle hover:border-accent-cyan/30 transition-all duration-200 cursor-pointer"
                    style={{ fontFamily: "var(--font-body)" }}
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    Open in Tab
                  </a>
                )}
                <button
                  type="button"
                  onClick={onClose}
                  className="p-1.5 rounded-[var(--radius-sm)] text-muted hover:text-primary hover:bg-elevated transition-all duration-200 cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            <div className="h-[1px] mx-6 bg-border-subtle shrink-0" />

            <div className="relative flex-1 overflow-hidden rounded-b-[var(--radius-xl)]" style={{ background: "#0a0f1a" }}>
              {loading && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3">
                  <Loader2 className="h-6 w-6 text-accent-cyan animate-spin" />
                  <p className="text-xs text-secondary">Connecting to Guacamole…</p>
                </div>
              )}

              {error && !loading && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 px-8 text-center">
                  <AlertTriangle className="h-7 w-7 text-accent-yellow" />
                  <div>
                    <p className="text-sm text-primary font-medium mb-1">Remote desktop unavailable</p>
                    <p className="text-xs text-secondary max-w-md">{error}</p>
                    <p className="text-[10px] text-muted mt-3 max-w-lg">
                      Ensure the Guacamole stack is running (<span className="font-mono">docker compose up</span>) and
                      set <span className="font-mono">GUACAMOLE_API_URL</span> /{" "}
                      <span className="font-mono">GUACAMOLE_PUBLIC_URL</span> for the backend. If the iframe stays blank,
                      use <strong>Open in Tab</strong> — some browsers block cross-origin embedding.
                    </p>
                  </div>
                  <Button variant="secondary" size="sm" onClick={() => void retry()}>
                    Retry
                  </Button>
                </div>
              )}

              {clientUrl && !error && (
                <iframe
                  key={clientUrl}
                  src={clientUrl}
                  title={`Remote desktop — ${vmName}`}
                  onLoad={() => setIframeLoaded(true)}
                  className="w-full h-full border-0"
                  style={{ opacity: iframeLoaded ? 1 : 0, transition: "opacity 0.35s ease" }}
                  allow="clipboard-read; clipboard-write; fullscreen"
                />
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
