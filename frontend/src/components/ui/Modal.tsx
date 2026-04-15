import { type ReactNode } from "react";
import { motion, AnimatePresence } from "motion/react";
import { X } from "lucide-react";
import { cn } from "@/lib/cn";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  className?: string;
}

export default function Modal({
  open,
  onClose,
  title,
  children,
  className,
}: ModalProps) {
  return (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className={cn(
              "relative z-10 w-full max-w-md mx-4",
              "rounded-[var(--radius-xl)]",
              className,
            )}
            style={{
              background: "rgba(10, 22, 40, 0.95)",
              backdropFilter: "blur(24px)",
              border: "1px solid rgba(10,239,255,0.1)",
              boxShadow: "0 8px 32px rgba(0,0,0,0.6), 0 0 40px rgba(10,239,255,0.03)",
            }}
          >
            {/* Accent line */}
            <div
              className="absolute top-0 left-6 right-6 h-[1px]"
              style={{
                background: "linear-gradient(90deg, transparent, rgba(10,239,255,0.15), transparent)",
              }}
            />

            {/* Header */}
            <div className="flex items-center justify-between px-6 pt-6 pb-4">
              <h2
                className="text-lg font-bold text-primary"
                style={{ fontFamily: "var(--font-display)" }}
              >
                {title}
              </h2>
              <button
                onClick={onClose}
                className="p-1.5 rounded-[var(--radius-sm)] text-muted hover:text-primary hover:bg-elevated transition-all duration-200 cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Content */}
            <div className="px-6 pb-6">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
}
