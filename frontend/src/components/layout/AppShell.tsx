import { Outlet } from "react-router-dom";
import { motion } from "motion/react";
import { Wifi, Menu } from "lucide-react";
import Sidebar from "./Sidebar";
import BackgroundEffects from "./BackgroundEffects";
import Background3D from "./Background3D";
import { useAuthStore } from "@/stores/auth-store";
import { useState, useEffect } from "react";

function TopBar({ onToggleSidebar }: { onToggleSidebar: () => void }) {
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
      className="flex items-center justify-between px-6 h-14 border-b border-border-subtle bg-surface/40 backdrop-blur-md shrink-0 z-20"
    >
      {/* Left: Hamburger + Welcome */}
      <div className="flex items-center gap-4">
        <button
          onClick={onToggleSidebar}
          className="p-1.5 -ml-2 rounded-[var(--radius-sm)] text-muted hover:text-primary hover:bg-elevated transition-colors cursor-pointer"
        >
          <Menu className="h-5 w-5" />
        </button>
        <span className="text-base text-secondary" style={{ fontFamily: "var(--font-body)" }}>
          Welcome back,{" "}
          <span className="text-primary font-semibold text-glow-magenta transition-colors">
            {user?.username ?? "User"}
          </span>
        </span>
      </div>

      {/* Right: Status + Time */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 rounded-[var(--radius-sm)] border border-border-subtle bg-elevated/30 glow-border-hover transition-colors">
          <span className="text-xs text-secondary uppercase tracking-wider" style={{ fontFamily: "var(--font-display)" }}>
            Status:
          </span>
          <span className="text-xs font-mono font-semibold text-accent-cyan flex items-center gap-1.5 text-glow-cyan">
            Online
            <span className="relative flex h-2 w-2">
              <span className="absolute inset-0 rounded-full bg-accent-cyan animate-pulse-status" />
              <span className="relative h-2 w-2 rounded-full bg-accent-cyan" />
            </span>
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted font-mono">
          <Wifi className="h-3 w-3 text-accent-cyan" />
          <span>{time.toLocaleTimeString("en-US", { hour12: false })}</span>
        </div>
      </div>
    </motion.header>
  );
}

export default function AppShell() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <div className="flex h-dvh bg-deepest overflow-hidden">
      {/* Background effects layer */}
      <BackgroundEffects />
      <Background3D />

      <Sidebar isOpen={isSidebarOpen} />
      <div className="flex-1 flex flex-col overflow-hidden relative">
        {/* Subtle grid background */}
        <div className="absolute inset-0 grid-bg pointer-events-none opacity-30" />
        
        <TopBar onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} />
        
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
