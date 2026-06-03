import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import { toast } from "sonner";
import {
  RefreshCw,
  Upload,
  Trash2,
  FileText,
  Database,
  AlertTriangle,
  Loader2,
} from "lucide-react";
import {
  useKnowledgeStatus,
  useUploadKnowledgePdf,
  useDeleteKnowledgeSource,
} from "@/hooks/use-knowledge";
import GlitchText from "@/components/ui/GlitchText";

export default function AdminKnowledgePage() {
  const { data: status, isLoading, refetch } = useKnowledgeStatus();
  const uploadMut = useUploadKnowledgePdf();
  const deleteMut = useDeleteKnowledgeSource();

  const fileInputRef = useRef<HTMLInputElement>(null);
  const [dragActive, setDragActive] = useState(false);
  // Drag events fire on every child element; a counter avoids flicker so the
  // highlight only clears when the cursor truly leaves the dropzone.
  const dragDepth = useRef(0);

  // Stop the browser's default "open the dropped file in a new tab" behavior
  // when a file is dropped anywhere on the page (e.g. a near-miss of the zone).
  useEffect(() => {
    const prevent = (e: DragEvent) => e.preventDefault();
    window.addEventListener("dragover", prevent);
    window.addEventListener("drop", prevent);
    return () => {
      window.removeEventListener("dragover", prevent);
      window.removeEventListener("drop", prevent);
    };
  }, []);

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      toast.error(`"${file.name}" is not a PDF. Only .pdf files can be indexed.`);
      return;
    }
    uploadMut.mutate(file);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const sources = status?.sources ?? [];
  const available = status?.available ?? false;

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
            text="Knowledge Base"
            className="text-2xl font-bold text-primary tracking-tight"
          />
          <p
            className="text-sm text-muted mt-1"
            style={{ fontFamily: "var(--font-body)" }}
          >
            Upload documents the ChatOps agent retrieves from when answering questions
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 h-8 rounded-[var(--radius-md)] text-xs font-medium text-secondary border border-border-subtle hover:border-accent-amber/30 hover:text-accent-amber transition-all cursor-pointer"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </button>
      </motion.div>

      {/* Availability / stats banner */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="glass-panel rounded-[var(--radius-lg)] p-5 flex items-center gap-4"
      >
        <div className="h-11 w-11 rounded-[var(--radius-md)] flex items-center justify-center bg-accent-amber/10 border border-accent-amber/20">
          <Database className="h-5 w-5 text-accent-amber" />
        </div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-primary">
            {available ? "Vector store online" : "Vector store unavailable"}
          </p>
          <p className="text-xs text-muted mt-0.5">
            {available
              ? `${status?.doc_count ?? 0} chunks indexed across ${sources.length} document(s)`
              : status?.error ?? "The embedding model may still be downloading. Try again shortly."}
          </p>
        </div>
      </motion.div>

      {/* Upload dropzone */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <div
          onDragEnter={(e) => {
            e.preventDefault();
            dragDepth.current += 1;
            setDragActive(true);
          }}
          onDragOver={(e) => {
            // Must preventDefault on dragover for the drop event to fire at all.
            e.preventDefault();
            e.dataTransfer.dropEffect = "copy";
            if (!dragActive) setDragActive(true);
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            dragDepth.current = Math.max(0, dragDepth.current - 1);
            if (dragDepth.current === 0) setDragActive(false);
          }}
          onDrop={(e) => {
            e.preventDefault();
            dragDepth.current = 0;
            setDragActive(false);
            handleFiles(e.dataTransfer.files);
          }}
          onClick={() => fileInputRef.current?.click()}
          className={[
            "glass-panel rounded-[var(--radius-lg)] p-8 flex flex-col items-center justify-center text-center cursor-pointer transition-all border-2 border-dashed",
            dragActive
              ? "border-accent-amber/60 bg-accent-amber/5"
              : "border-border-subtle hover:border-accent-amber/30",
          ].join(" ")}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          {/* pointer-events-none so drag events always target the dropzone
              container, never these children (prevents flicker / missed drops) */}
          <div className="flex flex-col items-center pointer-events-none">
            {uploadMut.isPending ? (
              <Loader2 className="h-7 w-7 text-accent-amber animate-spin" />
            ) : (
              <Upload className="h-7 w-7 text-accent-amber" />
            )}
            <p className="text-sm font-medium text-primary mt-3">
              {uploadMut.isPending
                ? "Indexing document… (first upload also downloads the embedding model)"
                : dragActive
                ? "Release to upload"
                : "Drop a PDF here, or click to browse"}
            </p>
            <p className="text-xs text-muted mt-1">
              PDF only · max 20 MB · text is extracted, chunked, embedded, and stored
            </p>
          </div>
        </div>
      </motion.div>

      {/* Indexed sources */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="space-y-3"
      >
        <h2 className="text-xs font-bold uppercase tracking-[0.15em] text-muted/60">
          Indexed Documents
        </h2>

        {sources.map((src, i) => (
          <motion.div
            key={src.source}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              delay: 0.2 + i * 0.04,
              duration: 0.35,
              ease: [0.16, 1, 0.3, 1],
            }}
            className="glass-panel rounded-[var(--radius-lg)] p-4 flex items-center gap-4"
          >
            <FileText className="h-4 w-4 text-accent-cyan shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-primary truncate font-mono">
                {src.source}
              </p>
              <p className="text-[11px] text-muted mt-0.5">
                {src.chunks} chunk{src.chunks === 1 ? "" : "s"} indexed
              </p>
            </div>
            <button
              onClick={() => {
                if (
                  window.confirm(
                    `Remove "${src.source}" from the knowledge base? The agent will no longer use it.`,
                  )
                ) {
                  deleteMut.mutate(src.source);
                }
              }}
              disabled={deleteMut.isPending}
              className="flex items-center gap-1.5 px-2.5 h-7 rounded-[var(--radius-sm)] text-[10px] font-semibold text-accent-red border border-accent-red/20 hover:bg-accent-red/10 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Trash2 className="h-3 w-3" />
              Remove
            </button>
          </motion.div>
        ))}

        {sources.length === 0 && (
          <div className="py-12 text-center text-sm text-muted flex flex-col items-center gap-2">
            {isLoading ? (
              <>
                <Loader2 className="h-5 w-5 animate-spin" />
                Loading knowledge base…
              </>
            ) : (
              <>
                <AlertTriangle className="h-5 w-5 text-muted/50" />
                No documents indexed yet. Upload a PDF to give the agent knowledge to draw on.
              </>
            )}
          </div>
        )}
      </motion.div>
    </div>
  );
}
