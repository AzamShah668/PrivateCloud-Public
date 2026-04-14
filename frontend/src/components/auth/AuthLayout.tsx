import { type ReactNode } from "react";
import { motion } from "motion/react";
import TerrainBackground from "./TerrainBackground";
import TypewriterText from "./TypewriterText";

interface AuthLayoutProps {
  children: ReactNode;
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
            background: "rgba(15, 17, 23, 0.85)",
            backdropFilter: "blur(20px) saturate(1.2)",
            boxShadow:
              "0 0 0 1px rgba(35,39,54,0.6), 0 20px 60px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.03)",
          }}
        >
          {/* Logo / Wordmark */}
          <div className="text-center mb-8">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.7, duration: 0.3 }}
              className="inline-flex items-center gap-2 mb-2"
            >
              {/* Cloud icon mark */}
              <svg
                width="28"
                height="28"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--color-accent-blue)"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9Z" />
              </svg>
            </motion.div>

            <TypewriterText
              text="PrivateCloud"
              delay={0.7}
              className="block text-2xl font-bold tracking-[0.08em] text-primary"
              style={{ fontFamily: "var(--font-display)" }}
            />
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1.6, duration: 0.4 }}
              className="text-xs text-secondary mt-1.5 tracking-wider uppercase"
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
