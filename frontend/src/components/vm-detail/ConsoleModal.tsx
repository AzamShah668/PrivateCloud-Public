import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { X, TerminalSquare, Loader2, AlertTriangle, ExternalLink } from "lucide-react";
import Button from "@/components/ui/Button";

interface ConsoleModalProps {
  open: boolean;
  onClose: () => void;
  vmIP: string;
  vmName: string;
}

export default function ConsoleModal({
  open,
  onClose,
  vmIP,
  vmName,
}: ConsoleModalProps) {
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const [iframeError, setIframeError] = useState(false);

  const consoleURL = `http://${vmIP}:7681`;

  function handleOpen() {
    setIframeLoaded(false);
    setIframeError(false);
  }

  function handleIframeLoad() {
    setIframeLoaded(true);
    setIframeError(false);
  }

  function handleIframeError() {
    setIframeError(true);
    setIframeLoaded(false);
  }

  return (
    <AnimatePresence onExitComplete={() => { setIframeLoaded(false); setIframeError(false); }}>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 12 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            onAnimationStart={handleOpen}
            className="relative z-10 w-full flex flex-col"
            style={{
              maxWidth: "960px",
              height: "clamp(480px, 75vh, 720px)",
              background: "rgba(10, 22, 40, 0.98)",
              backdropFilter: "blur(24px)",
              border: "1px solid rgba(10,239,255,0.15)",
              borderRadius: "var(--radius-xl)",
              boxShadow:
                "0 8px 40px rgba(0,0,0,0.7), 0 0 60px rgba(10,239,255,0.05)",
            }}
          >
            {/* Accent line */}
            <div
              className="absolute top-0 left-8 right-8 h-[1px]"
              style={{
                background:
                  "linear-gradient(90deg, transparent, rgba(10,239,255,0.25), transparent)",
              }}
            />

            {/* Header */}
            <div className="flex items-center justify-between px-6 pt-5 pb-4 shrink-0">
              <div className="flex items-center gap-3">
                <div
                  className="flex items-center justify-center h-8 w-8 rounded-[var(--radius-md)]"
                  style={{ background: "rgba(10,239,255,0.08)", border: "1px solid rgba(10,239,255,0.15)" }}
                >
                  <TerminalSquare className="h-4 w-4 text-accent-cyan" />
                </div>
                <div>
                  <h2
                    className="text-sm font-bold text-primary leading-none"
                    style={{ fontFamily: "var(--font-display)" }}
                  >
                    Web Console
                  </h2>
                  <p className="text-[10px] text-muted mt-0.5 font-mono">{vmName} · {vmIP}:7681</p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <a
                  href={consoleURL}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 h-8 px-3 text-xs font-medium rounded-[var(--radius-md)] text-secondary hover:text-accent-cyan hover:bg-accent-cyan/10 border border-border-subtle hover:border-accent-cyan/30 transition-all duration-200 cursor-pointer"
                  style={{ fontFamily: "var(--font-body)" }}
                >
                  <ExternalLink className="h-3 w-3" />
                  Open in Tab
                </a>
                <button
                  onClick={onClose}
                  className="p-1.5 rounded-[var(--radius-sm)] text-muted hover:text-primary hover:bg-elevated transition-all duration-200 cursor-pointer"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Divider */}
            <div className="h-[1px] mx-6 bg-border-subtle shrink-0" />

            {/* Terminal area */}
            <div className="relative flex-1 overflow-hidden rounded-b-[var(--radius-xl)]" style={{ background: "#0a0f1a" }}>

              {/* Loading overlay */}
              {!iframeLoaded && !iframeError && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3">
                  <Loader2 className="h-6 w-6 text-accent-cyan animate-spin" />
                  <p className="text-xs text-secondary">Connecting to terminal…</p>
                  <p className="text-[10px] text-muted font-mono">{consoleURL}</p>
                </div>
              )}

              {/* Error overlay */}
              {iframeError && (
                <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 px-8 text-center">
                  <AlertTriangle className="h-7 w-7 text-accent-yellow" />
                  <div>
                    <p className="text-sm text-primary font-medium mb-1">Unable to reach ttyd</p>
                    <p className="text-xs text-secondary">
                      Make sure the VM is running and ttyd is active on port 7681.<br />
                      It may still be booting — wait a few seconds and try again.
                    </p>
                  </div>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => { setIframeError(false); setIframeLoaded(false); }}
                  >
                    Retry
                  </Button>
                  <a
                    href={consoleURL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-accent-cyan hover:underline"
                  >
                    Open directly in browser →
                  </a>
                </div>
              )}

              {/* iframe */}
              {!iframeError && (
                <iframe
                  key={`${vmIP}-${open}`}
                  src={consoleURL}
                  title={`Console — ${vmName}`}
                  onLoad={handleIframeLoad}
                  onError={handleIframeError}
                  className="w-full h-full border-0"
                  style={{ opacity: iframeLoaded ? 1 : 0, transition: "opacity 0.3s ease" }}
                  allow="clipboard-read; clipboard-write"
                />
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
