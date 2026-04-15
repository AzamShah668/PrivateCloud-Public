import { Outlet } from "react-router-dom";
import { motion } from "motion/react";
import { Search, Wifi } from "lucide-react";
import Sidebar from "./Sidebar";
import BackgroundEffects from "./BackgroundEffects";
import { useAuthStore } from "@/stores/auth-store";
import { useState, useEffect } from "react";

function TopBar() {
  const user = useAuthStore((s) => s.user);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="flex items-center justify-between px-6 h-14 border-b border-border-subtle bg-surface/40 backdrop-blur-md shrink-0"
    >
      {/* Left: Welcome + Region */}
      <div className="flex items-center gap-4">
        <span className="text-base text-secondary" style={{ fontFamily: "var(--font-body)" }}>
          Welcome back,{" "}
          <span className="text-primary font-semibold">
            {user?.username ?? "User"}
          </span>
        </span>
        <span className="text-border-subtle">|</span>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted uppercase tracking-wider" style={{ fontFamily: "var(--font-display)" }}>
            Active Region:
          </span>
          <span className="text-xs font-mono font-semibold text-accent-cyan px-2 py-0.5 rounded-[var(--radius-sm)] border border-accent-cyan/20 bg-accent-cyan/5">
            US-EAST-01
          </span>
        </div>
      </div>

      {/* Center: Search */}
      <div className="flex items-center gap-2 px-3 h-8 rounded-[var(--radius-md)] border border-border-subtle bg-elevated/50 min-w-[240px] transition-all duration-200 focus-within:border-accent-cyan/30 focus-within:bg-elevated focus-within:shadow-[0_0_12px_rgba(10,239,255,0.08)]">
        <Search className="h-3.5 w-3.5 text-muted" />
        <input
          type="text"
          placeholder="Search instances..."
          className="bg-transparent text-xs text-primary placeholder:text-muted outline-none flex-1 font-mono"
        />
      </div>

      {/* Right: Status + Time */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 rounded-[var(--radius-sm)] border border-border-subtle bg-elevated/30">
          <span className="text-xs text-secondary uppercase tracking-wider" style={{ fontFamily: "var(--font-display)" }}>
            Status:
          </span>
          <span className="text-xs font-mono font-semibold text-accent-green flex items-center gap-1.5">
            Online
            <span className="relative flex h-2 w-2">
              <span className="absolute inset-0 rounded-full bg-accent-green animate-pulse-status" />
              <span className="relative h-2 w-2 rounded-full bg-accent-green" />
            </span>
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted font-mono">
          <Wifi className="h-3 w-3 text-accent-green" />
          <span>{time.toLocaleTimeString("en-US", { hour12: false })}</span>
        </div>
      </div>
    </motion.header>
  );
}

export default function AppShell() {
  return (
    <div className="flex h-dvh bg-deepest overflow-hidden">
      {/* Background effects layer */}
      <BackgroundEffects />

      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Subtle grid background */}
        <div className="absolute inset-0 grid-bg pointer-events-none opacity-30" />
        
        <TopBar />
        
        <main className="flex-1 flex flex-col overflow-y-auto relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="flex-1"
          >
            <Outlet />
          </motion.div>
        </main>
      </div>
    </div>
  );
}
