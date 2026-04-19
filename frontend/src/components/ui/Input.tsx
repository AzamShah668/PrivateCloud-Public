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
            className="text-[10px] font-semibold text-muted tracking-[0.1em] uppercase"
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
            "text-sm text-primary placeholder:text-primary/50",
            "outline-none transition-all duration-300",
            "focus:border-accent-cyan/50 focus:shadow-[0_0_0_3px_rgba(10,239,255,0.08),0_0_15px_rgba(10,239,255,0.05)]",
            "font-mono",
            error && "border-accent-red focus:border-accent-red focus:shadow-[0_0_0_3px_rgba(239,68,68,0.12)]",
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
