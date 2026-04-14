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
      <span className="text-xs text-secondary">
        {usedToday} / {quota} VMs today
      </span>
      <div className="w-24 h-1.5 rounded-full bg-elevated overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{
            width: `${pct}%`,
            background: isMaxed
              ? "var(--color-accent-red)"
              : "var(--color-accent-blue)",
          }}
        />
      </div>
    </div>
  );
}
