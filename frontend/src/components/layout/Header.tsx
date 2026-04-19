import { type ReactNode } from "react";
import GlitchText from "@/components/ui/GlitchText";

interface HeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export default function Header({ title, subtitle, actions }: HeaderProps) {
  return (
    <header className="flex items-center justify-between px-6 h-14 border-b border-border-subtle/50 bg-surface/30 backdrop-blur-sm relative overflow-hidden">
      {/* Subtle accent line at top */}
      <div
        className="absolute top-0 left-0 right-0 h-[1px]"
        style={{
          background: "linear-gradient(90deg, transparent, rgba(217, 70, 239, 0.4), rgba(10,239,255,0.4), transparent)",
        }}
      />
      <div>
        <h1
          className="text-2xl font-bold tracking-wide"
          style={{ fontFamily: "var(--font-display)" }}
        >
          <GlitchText text={title} />
        </h1>
        {subtitle && <p className="text-sm text-muted mt-1">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </header>
  );
}
