import { useAuthStore } from "@/stores/auth-store";

interface QuotaIndicatorProps {
  usedToday: number;
}

export default function QuotaIndicator({ usedToday }: QuotaIndicatorProps) {
  const user = useAuthStore((s) => s.user);
  const quota = user?.daily_quota ?? 3;
  const pct = Math.min((usedToday / quota) * 100, 100);
  const isMaxed = usedToday >= quota;

  return (
    <div className="flex items-center gap-3">
      <span className="text-[10px] text-muted uppercase tracking-wider font-mono">
        {usedToday} / {quota} VMs today
      </span>
      <div className="w-24 h-1.5 rounded-full bg-elevated overflow-hidden border border-border-subtle/50">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{
            width: `${pct}%`,
            background: isMaxed
              ? "var(--color-accent-red)"
              : "linear-gradient(90deg, var(--color-accent-cyan), var(--color-accent-blue))",
            boxShadow: isMaxed
              ? "0 0 8px rgba(239,68,68,0.3)"
              : "0 0 8px rgba(10,239,255,0.2)",
          }}
        />
      </div>
    </div>
  );
}
