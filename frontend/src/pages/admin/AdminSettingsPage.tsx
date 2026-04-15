import { motion } from "motion/react";
import { Construction } from "lucide-react";

export default function AdminSettingsPage() {
  return (
    <div className="p-6 flex items-center justify-center min-h-[60vh]">
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="glass-panel rounded-[var(--radius-lg)] p-10 text-center max-w-md"
      >
        <div
          className="mx-auto h-16 w-16 rounded-full flex items-center justify-center mb-5"
          style={{
            background:
              "linear-gradient(135deg, rgba(245,158,11,0.1), rgba(239,68,68,0.05))",
            border: "1px solid rgba(245,158,11,0.15)",
          }}
        >
          <Construction className="h-7 w-7 text-accent-amber" />
        </div>
        <h2
          className="text-lg font-bold text-primary mb-2"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Settings Coming Soon
        </h2>
        <p
          className="text-sm text-muted leading-relaxed"
          style={{ fontFamily: "var(--font-body)" }}
        >
          System configuration, notification preferences, and cluster settings
          will be available in the next sprint.
        </p>
      </motion.div>
    </div>
  );
}
