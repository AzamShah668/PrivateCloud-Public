import { cn } from "@/lib/cn";

interface SkeletonProps {
  className?: string;
}

export default function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-md)]",
        "animate-shimmer bg-gradient-to-r from-elevated via-input to-elevated",
        "border border-border-subtle/30",
        className,
      )}
    />
  );
}
