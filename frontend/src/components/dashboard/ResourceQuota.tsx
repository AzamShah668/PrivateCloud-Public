import { useEffect, useRef, useState } from "react";
import { motion } from "motion/react";
import type { VMEnriched } from "@/api/vms";
import SpotlightCard from "@/components/ui/SpotlightCard";
import GlitchText from "@/components/ui/GlitchText";

interface ResourceQuotaProps {
  vms?: VMEnriched[];
}

// Animated progress ring SVG component
function ProgressRing({
  value,
  max,
  label,
  unit,
  color,
  delay,
}: {
  value: number;
  max: number;
  label: string;
  unit: string;
  color: string;
  delay: number;
}) {
  const [animatedValue, setAnimatedValue] = useState(0);
  const raf = useRef<number>(0);

  const radius = 38;
  const circumference = 2 * Math.PI * radius;
  const percentage = max > 0 ? Math.min(animatedValue / max, 1) : 0;
  const offset = circumference - percentage * circumference;

  useEffect(() => {
    const timeout = setTimeout(() => {
      const duration = 1200;
      const start = performance.now();

      function tick(now: number) {
        const t = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - t, 4);
        setAnimatedValue(value * eased);
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
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="flex flex-col items-center gap-2"
    >
      <div className="relative">
        <svg width="92" height="92" viewBox="0 0 92 92">
          {/* Background ring */}
          <circle
            cx="46"
            cy="46"
            r={radius}
            fill="none"
            stroke="rgba(26,42,68,0.5)"
            strokeWidth="4"
          />
          {/* Progress ring */}
          <circle
            cx="46"
            cy="46"
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            transform="rotate(-90 46 46)"
            style={{
              transition: "stroke-dashoffset 0.1s ease",
              filter: `drop-shadow(0 0 6px ${color}40)`,
            }}
          />
          {/* Glow dot at the end */}
          {percentage > 0.05 && (
            <circle
              cx={46 + radius * Math.cos((-90 + percentage * 360) * (Math.PI / 180))}
              cy={46 + radius * Math.sin((-90 + percentage * 360) * (Math.PI / 180))}
              r="3"
              fill={color}
              style={{ filter: `drop-shadow(0 0 4px ${color})` }}
            />
          )}
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="text-lg font-bold font-mono tabular-nums"
            style={{ color, fontFamily: "var(--font-display)" }}
          >
            {Math.round(animatedValue)}
          </span>
          <span className="text-[9px] text-muted uppercase tracking-wider">
            / {max} {unit}
          </span>
        </div>
      </div>
      <span
        className="text-[10px] text-secondary uppercase tracking-[0.1em] font-semibold text-center"
        style={{ fontFamily: "var(--font-display)" }}
      >
        {label}
      </span>
    </motion.div>
  );
}

export default function ResourceQuota({ vms }: ResourceQuotaProps) {
  const instances = (vms ?? []).filter((v) => v.status !== "deleted");
  const runningVMs = instances.filter((v) => v.live_status === "running").length;
  const totalVMs = instances.length;

  // Calculate resource usage from actual VMs
  const usedCores = instances.reduce((sum, vm) => {
    const cores = (vm.request_payload?.cpu_cores as number) ?? 1;
    return sum + cores;
  }, 0);
  const usedRamGB = instances.reduce((sum, vm) => {
    const ramMB = (vm.request_payload?.ram_mb as number) ?? 1024;
    return sum + ramMB / 1024;
  }, 0);
  const usedStorageGB = instances.reduce((sum, vm) => {
    const storageGB = (vm.request_payload?.storage_gb as number) ?? 32;
    return sum + storageGB;
  }, 0);

  // Quotas (would come from an API in production)
  const maxVMs = 10;
  const maxCores = 32;
  const maxRamGB = 64;
  const maxStorageGB = 500;

  return (
    <SpotlightCard
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="p-6 relative overflow-hidden h-full"
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-6 right-6 h-[1px]"
        style={{
          background: "linear-gradient(90deg, transparent, rgba(59,130,246,0.15), transparent)",
        }}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <GlitchText
          text="Resource Quota"
          className="text-base font-bold tracking-wide text-primary"
        />
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-accent-green/10 border border-accent-green/20">
          <span className="h-1.5 w-1.5 rounded-full bg-accent-green animate-pulse-status shadow-[0_0_8px_#10B981]" />
          <span className="text-[10px] text-accent-green font-mono uppercase tracking-wider">
            {runningVMs} active
          </span>
        </div>
      </div>

      {/* Progress rings grid */}
      <div className="grid grid-cols-2 gap-4 mt-4">
        <ProgressRing
          value={totalVMs}
          max={maxVMs}
          label="Instances"
          unit=""
          color="#0AEFFF"
          delay={0.2}
        />
        <ProgressRing
          value={usedCores}
          max={maxCores}
          label="CPU Cores"
          unit=""
          color="#3B82F6"
          delay={0.3}
        />
        <ProgressRing
          value={Math.round(usedRamGB)}
          max={maxRamGB}
          label="RAM (GB)"
          unit="GB"
          color="#14B8A6"
          delay={0.4}
        />
        <ProgressRing
          value={Math.round(usedStorageGB)}
          max={maxStorageGB}
          label="Storage (GB)"
          unit="GB"
          color="#8B5CF6"
          delay={0.5}
        />
      </div>
    </SpotlightCard>
  );
}
