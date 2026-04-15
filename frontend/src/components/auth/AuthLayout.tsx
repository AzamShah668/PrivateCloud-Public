import { type ReactNode } from "react";
import { motion } from "motion/react";
import TerrainBackground from "./TerrainBackground";


interface AuthLayoutProps {
  children: ReactNode;
}

function ACLogoMark() {
  return (
    <svg
      width="40"
      height="40"
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
      {/* Video particle background */}
      <TerrainBackground />

      {/* Glass card */}
      <motion.div
        initial={{ opacity: 0, y: 32, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.7, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-20 w-full max-w-[420px] mx-4"
      >
        <div
          className="rounded-[var(--radius-xl)] p-8"
          style={{
            background: "rgba(6, 14, 30, 0.78)",
            backdropFilter: "blur(28px) saturate(1.4)",
            WebkitBackdropFilter: "blur(28px) saturate(1.4)",
            boxShadow: [
              "0 0 0 1px rgba(10,239,255,0.07)",
              "0 24px 80px rgba(0,0,0,0.6)",
              "0 0 60px rgba(10,239,255,0.04)",
              "inset 0 1px 0 rgba(255,255,255,0.04)",
            ].join(", "),
          }}
        >
          {/* Subtle top-edge highlight — mimics light from the particles */}
          <div
            className="absolute inset-x-6 top-0 h-px pointer-events-none rounded-full"
            style={{
              background:
                "linear-gradient(90deg, transparent 0%, rgba(10,239,255,0.25) 30%, rgba(59,130,246,0.2) 70%, transparent 100%)",
            }}
          />

          {/* Logo / Wordmark */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.6, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="inline-flex items-center justify-center mb-4"
            >
              <ACLogoMark />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.7, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            >
              <h1
                className="text-[2rem] font-extrabold tracking-[0.06em] leading-none"
                style={{
                  fontFamily: "var(--font-display)",
                  background: "linear-gradient(135deg, #0AEFFF 0%, #3B82F6 50%, #8B5CF6 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                  filter: "drop-shadow(0 0 20px rgba(10,239,255,0.3)) drop-shadow(0 0 6px rgba(59,130,246,0.2))",
                }}
              >
                azna<span style={{
                  background: "linear-gradient(135deg, #3B82F6 0%, #0AEFFF 100%)",
                  WebkitBackgroundClip: "text",
                  WebkitTextFillColor: "transparent",
                  backgroundClip: "text",
                }}>-cloud</span>
              </h1>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, scaleX: 0 }}
              animate={{ opacity: 1, scaleX: 1 }}
              transition={{ delay: 1.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
              className="mx-auto mt-3 mb-2 h-px w-24"
              style={{
                background: "linear-gradient(90deg, transparent, #0AEFFF, #3B82F6, transparent)",
                opacity: 0.4,
              }}
            />

            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              transition={{ delay: 1.3, duration: 0.5 }}
              className="text-[9px] mt-2 tracking-[0.3em] uppercase"
              style={{
                fontFamily: "var(--font-mono)",
                color: "#7A8BA8",
              }}
            >
              Private Cloud Infrastructure
            </motion.p>
          </div>

          {children}
        </div>
      </motion.div>
    </div>
  );
}
