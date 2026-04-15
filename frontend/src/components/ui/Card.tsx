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
        "rounded-[var(--radius-lg)]",
        "glass-panel",
        hoverable && [
          "transition-all duration-300",
          "hover:scale-[1.02]",
          "glass-panel-hover",
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
