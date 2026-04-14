import { cn } from "@/lib/cn";
import { STATUS_COLORS } from "@/lib/constants";

interface BadgeProps {
  status: string;
  className?: string;
}

export default function Badge({ status, className }: BadgeProps) {
  const color = STATUS_COLORS[status] ?? STATUS_COLORS["unknown"]!;
  const isRunning = status === "running";

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-0.5",
        "rounded-full text-xs font-medium tracking-wide uppercase",
        "border",
        className,
      )}
      style={{
        color,
        borderColor: `color-mix(in srgb, ${color} 30%, transparent)`,
        background: `color-mix(in srgb, ${color} 8%, transparent)`,
      }}
    >
      {/* Animated pulse dot for running status */}
      <span className="relative flex h-2 w-2">
        {isRunning && (
          <span
            className="absolute inset-0 rounded-full animate-pulse-status"
            style={{ background: color }}
          />
        )}
        <span
          className="relative h-2 w-2 rounded-full"
          style={{ background: color }}
        />
      </span>
      {status}
    </span>
  );
}
