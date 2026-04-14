import { type HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
}

export default function Card({
  className,
  hoverable = false,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)] bg-surface",
        "border border-border-subtle",
        "shadow-[0_1px_3px_rgba(0,0,0,0.4),0_0_0_1px_var(--color-border-subtle)]",
        hoverable && [
          "transition-all duration-200",
          "hover:scale-[1.02] hover:border-border-focus/40",
          "hover:shadow-[0_8px_32px_rgba(0,0,0,0.5),0_0_0_1px_var(--color-border-focus)]",
          "cursor-pointer",
        ],
        className,
      )}
      {...props}
    >
      {children}
    </div>
  );
}
