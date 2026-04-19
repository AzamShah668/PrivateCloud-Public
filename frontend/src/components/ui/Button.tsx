import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";
import { Loader2 } from "lucide-react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
}

const variantStyles: Record<Variant, string> = {
  primary: [
    "text-white",
    "hover:brightness-110",
    "relative overflow-hidden",
    "btn-glow",
  ].join(" "),
  secondary: [
    "bg-elevated text-primary border border-border-subtle",
    "hover:bg-input hover:border-secondary/30",
    "btn-glow-soft",
  ].join(" "),
  ghost: [
    "bg-transparent text-secondary",
    "hover:bg-elevated hover:text-primary",
    "nav-glow",
  ].join(" "),
  danger: [
    "bg-transparent text-accent-red border border-accent-red/30",
    "hover:bg-accent-red/10 hover:border-accent-red/60",
  ].join(" "),
};

const sizeStyles: Record<Size, string> = {
  sm: "h-8 px-3 text-xs gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-12 px-6 text-base gap-2.5",
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading, children, disabled, ...props }, ref) => (
    <button
      ref={ref}
      disabled={disabled || loading}
      className={cn(
        "inline-flex items-center justify-center font-medium",
        "rounded-[var(--radius-md)] transition-all duration-200",
        "active:scale-[0.97] disabled:opacity-50 disabled:pointer-events-none",
        "cursor-pointer select-none",
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      style={
        variant === "primary"
          ? {
              background: "linear-gradient(135deg, #0AEFFF, #3B82F6)",
              boxShadow: "0 0 20px rgba(10,239,255,0.15), 0 0 40px rgba(10,239,255,0.05)",
              fontFamily: "var(--font-display)",
              letterSpacing: "0.02em",
              fontWeight: 600,
            }
          : {
              fontFamily: "var(--font-body)",
            }
      }
      {...props}
    >
      {loading && <Loader2 className="h-4 w-4 animate-spin" />}
      {/* Scan light effect on primary buttons */}
      {variant === "primary" && (
        <span className="absolute inset-0 pointer-events-none overflow-hidden">
          <span className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-white/15 to-transparent animate-scan-light" />
        </span>
      )}
      {children}
    </button>
  ),
);

Button.displayName = "Button";
export default Button;
