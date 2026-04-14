import { forwardRef, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, id, ...props }, ref) => {
    const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");

    return (
      <div className="flex flex-col gap-1.5">
        {label && (
          <label
            htmlFor={inputId}
            className="text-xs font-medium text-secondary tracking-wide uppercase"
            style={{ fontFamily: "var(--font-display)" }}
          >
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cn(
            "h-11 w-full rounded-[var(--radius-md)] px-4",
            "bg-input border border-border-subtle",
            "text-sm text-primary placeholder:text-muted",
            "outline-none transition-all duration-200",
            "focus:border-border-focus focus:shadow-[0_0_0_3px_var(--color-accent-blue-glow)]",
            error && "border-accent-red focus:border-accent-red focus:shadow-[0_0_0_3px_rgba(239,68,68,0.15)]",
            className,
          )}
          {...props}
        />
        {error && (
          <p className="text-xs text-accent-red animate-fade-in-up">
            {error}
          </p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
export default Input;
