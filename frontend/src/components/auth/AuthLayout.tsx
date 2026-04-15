import { type ReactNode } from "react";
import { motion } from "motion/react";
import TerrainBackground from "./TerrainBackground";
import TypewriterText from "./TypewriterText";

interface AuthLayoutProps {
  children: ReactNode;
}

function ACLogoMark() {
  return (
    <svg
      width="36"
      height="36"
      viewBox="0 0 40 40"
      fill="none"
    >
      <circle cx="20" cy="20" r="18" stroke="url(#auth-logo-grad)" strokeWidth="1.5" opacity="0.6" />
      <path
        d="M14 28L20 12L26 28M16 23H24"
        stroke="url(#auth-logo-grad)"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M28 16C26 13 23 12 20 12C15 12 12 16 12 20C12 24 15 28 20 28C23 28 26 27 28 24"
        stroke="url(#auth-logo-grad)"
        strokeWidth="1.5"
        strokeLinecap="round"
        opacity="0.5"
      />
      <defs>
        <linearGradient id="auth-logo-grad" x1="0" y1="0" x2="40" y2="40">
          <stop stopColor="#0AEFFF" />
          <stop offset="1" stopColor="#3B82F6" />
        </linearGradient>
      </defs>
    </svg>
  );
}

export default function AuthLayout({ children }: AuthLayoutProps) {
  return (
    <div className="relative min-h-dvh flex items-center justify-center overflow-hidden">
      {/* Animated wireframe terrain */}
      <TerrainBackground />

      {/* Glass card */}
      <motion.div
        initial={{ opacity: 0, y: 40 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-20 w-full max-w-[420px] mx-4"
      >
        <div
          className="rounded-[var(--radius-xl)] p-8"
          style={{
            background: "rgba(10, 22, 40, 0.85)",
            backdropFilter: "blur(24px) saturate(1.3)",
            boxShadow:
              "0 0 0 1px rgba(10,239,255,0.08), 0 20px 60px rgba(0,0,0,0.6), 0 0 40px rgba(10,239,255,0.03), inset 0 1px 0 rgba(255,255,255,0.03)",
          }}
        >
          {/* Logo / Wordmark */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.7, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="inline-flex items-center justify-center mb-3"
            >
              <ACLogoMark />
            </motion.div>

            <TypewriterText
              text="AETHER_CLOUD"
              delay={0.7}
              className="block text-2xl font-bold tracking-[0.12em] text-accent-cyan"
              style={{ fontFamily: "var(--font-display)" }}
            />
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.6, duration: 0.4 }}
              className="text-[10px] text-muted mt-2 tracking-[0.2em] uppercase"
            >
              Cloud Infrastructure Control
            </motion.p>
          </div>

          {children}
        </div>
      </motion.div>
    </div>
  );
}
