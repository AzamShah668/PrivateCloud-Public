import { Outlet } from "react-router-dom";
import { motion } from "motion/react";
import { Search, Wifi, Shield, Menu } from "lucide-react";
import AdminSidebar from "./AdminSidebar";
import BackgroundEffects from "@/components/layout/BackgroundEffects";
import { useAuthStore } from "@/stores/auth-store";
import { useState, useEffect } from "react";

function AdminTopBar({ toggleSidebar }: { toggleSidebar: () => void }) {
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
      {/* Left: Admin badge + Welcome */}
      <div className="flex items-center gap-4">
        <button
          onClick={toggleSidebar}
          className="p-1.5 rounded-[var(--radius-sm)] text-muted hover:text-primary hover:bg-elevated/80 hover:shadow-[0_0_15px_rgba(245,158,11,0.2)] transition-all duration-300"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-[var(--radius-sm)] border border-accent-amber/20 bg-accent-amber/5">
          <Shield className="h-3.5 w-3.5 text-accent-amber" />
          <span
            className="text-[10px] font-bold tracking-[0.1em] text-accent-amber uppercase"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Admin Panel
          </span>
        </div>
        <span className="text-border-subtle">|</span>
        <span
          className="text-sm text-secondary"
          style={{ fontFamily: "var(--font-body)" }}
        >
          Welcome,{" "}
          <span className="text-primary font-semibold">
            {user?.username ?? "Admin"}
          </span>
        </span>
      </div>

      {/* Center: Search */}
      <div className="flex items-center gap-2 px-3 h-8 rounded-[var(--radius-md)] border border-border-subtle bg-elevated/50 min-w-[260px] transition-all duration-200 focus-within:border-accent-cyan/30 focus-within:bg-elevated focus-within:shadow-[0_0_12px_rgba(10,239,255,0.08)]">
        <Search className="h-3.5 w-3.5 text-muted" />
        <input
          type="text"
          placeholder="Search users, VMs, logs..."
          className="bg-transparent text-xs text-primary placeholder:text-muted outline-none flex-1 font-mono"
        />
      </div>

      {/* Right: System status + Time */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 px-3 py-1 rounded-[var(--radius-sm)] border border-border-subtle bg-elevated/30">
          <span
            className="text-[10px] text-secondary uppercase tracking-wider"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Cluster:
          </span>
          <span className="text-xs font-mono font-semibold text-accent-green flex items-center gap-1.5">
            Healthy
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

export default function AdminShell() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  return (
    <div className="flex h-dvh bg-deepest overflow-hidden relative">
      <BackgroundEffects />

      {/* Sidebar Wrapper */}
      <motion.div
        initial={false}
        animate={{ 
          width: isSidebarOpen ? 260 : 0, 
          x: isSidebarOpen ? 0 : -260 
        }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="relative z-50 h-full shrink-0 shadow-2xl border-r border-border-subtle bg-surface/80"
      >
        {/* Force inner width to always be 260px so content doesn't squash during animation */}
        <div className="w-[260px] h-full">
          <AdminSidebar />
        </div>
      </motion.div>

      <div className="flex-1 flex flex-col overflow-hidden relative z-10 w-full">
        <div className="absolute inset-0 grid-bg pointer-events-none opacity-30" />
        <AdminTopBar toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)} />
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
