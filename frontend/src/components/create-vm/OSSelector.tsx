import { motion } from "motion/react";

import { OS_OPTIONS, type OSValue } from "@/lib/constants";
import { cn } from "@/lib/cn";

const osEmojis: Record<string, string> = {
  ubuntu: "🟠",
  debian: "🔴",
  centos: "🟣",
  windows: "🔵",
};

interface OSSelectorProps {
  value: OSValue;
  onChange: (value: OSValue) => void;
}

export default function OSSelector({ value, onChange }: OSSelectorProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-secondary mb-3">
        Operating System
      </label>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {OS_OPTIONS.map((os, i) => {
          const selected = value === os.value;
          return (
            <motion.button
              key={os.value}
              type="button"
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              onClick={() => onChange(os.value as OSValue)}
              className={cn(
                "relative flex flex-col items-center gap-2 p-4 rounded-[var(--radius-md)] border transition-all duration-200 cursor-pointer",
                selected
                  ? "border-accent-blue bg-accent-blue/5 shadow-[0_0_16px_-4px_var(--color-accent-blue)]"
                  : "border-border-subtle bg-elevated hover:border-secondary/30 hover:bg-elevated/80",
              )}
            >
              <span className="text-2xl">{osEmojis[os.icon] ?? "💻"}</span>
              <span className="text-xs font-medium text-primary text-center leading-tight">
                {os.label}
              </span>
              {selected && (
                <motion.div
                  layoutId="os-ring"
                  className="absolute inset-0 rounded-[var(--radius-md)] border-2 border-accent-blue pointer-events-none"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
