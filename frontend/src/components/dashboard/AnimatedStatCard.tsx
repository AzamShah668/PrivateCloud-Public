import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";

interface AnimatedStatCardProps {
  label: string;
  value: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
  icon?: React.ReactNode;
  color?: string;
  delay?: number;
}

export default function AnimatedStatCard({
  label,
  value,
  suffix = "",
  prefix = "",
  decimals = 0,
  icon,
  color = "var(--color-accent-cyan)",
  delay = 0,
}: AnimatedStatCardProps) {
  const [display, setDisplay] = useState(0);
  const raf = useRef<number>(0);
  const started = useRef(false);

  useEffect(() => {
    const timeout = setTimeout(() => {
      if (started.current) return;
      started.current = true;

      const duration = 1200;
      const start = performance.now();

      function tick(now: number) {
        const t = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - t, 4); // ease-out quartic
        setDisplay(value * eased);
        if (t < 1) raf.current = requestAnimationFrame(tick);
      }

      raf.current = requestAnimationFrame(tick);
    }, delay * 1000);

    return () => {
      clearTimeout(timeout);
      cancelAnimationFrame(raf.current);
    };
  }, [value, delay]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: delay, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="relative group"
    >
      <div
        className="glass-panel glass-panel-hover rounded-[var(--radius-md)] p-4 transition-all duration-300"
      >
        {/* Glow accent line */}
        <div
          className="absolute top-0 left-4 right-4 h-[1px] opacity-50"
          style={{
            background: `linear-gradient(90deg, transparent, ${color}, transparent)`,
          }}
        />

        <div className="flex items-center gap-2 mb-2">
          {icon && <span style={{ color }} className="opacity-60">{icon}</span>}
          <span className="text-[10px] text-muted uppercase tracking-[0.1em] font-semibold">
            {label}
          </span>
        </div>

        <div className="flex items-baseline gap-1">
          <span
            className="text-2xl font-bold font-mono tabular-nums"
            style={{ color }}
          >
            {prefix}
            {display.toFixed(decimals).replace(/\B(?=(\d{3})+(?!\d))/g, ",")}
          </span>
          {suffix && (
            <span className="text-sm font-semibold text-secondary">
              {suffix}
            </span>
          )}
        </div>
      </div>
    </motion.div>
  );
}
