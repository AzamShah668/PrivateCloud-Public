import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Server,
  Terminal,
  Bell,
  LogOut,
  ChevronRight,
  Shield,
} from "lucide-react";
import { motion } from "motion/react";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/cn";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/vms/create", icon: Server, label: "My Instances" },
  { to: "/chatops", icon: Terminal, label: "Agent ChatOps" },
];

function ACLogo() {
  return (
    <div className="relative flex items-center justify-center h-10 w-10 rounded-[var(--radius-md)]">
      {/* Glow background */}
      <div 
        className="absolute inset-0 rounded-[var(--radius-md)] opacity-40"
        style={{
          background: "linear-gradient(135deg, rgba(10,239,255,0.3), rgba(59,130,246,0.2))",
          filter: "blur(4px)",
        }}
      />
      <svg
        width="32"
        height="32"
        viewBox="0 0 40 40"
        fill="none"
        className="relative z-10"
      >
        {/* Outer ring */}
        <circle cx="20" cy="20" r="18" stroke="url(#logo-grad)" strokeWidth="1.5" opacity="0.6" />
        {/* A letter */}
        <path
          d="M14 28L20 12L26 28M16 23H24"
          stroke="url(#logo-grad)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* C arc */}
        <path
          d="M28 16C26 13 23 12 20 12C15 12 12 16 12 20C12 24 15 28 20 28C23 28 26 27 28 24"
          stroke="url(#logo-grad)"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.5"
        />
        <defs>
          <linearGradient id="logo-grad" x1="0" y1="0" x2="40" y2="40">
            <stop stopColor="#0AEFFF" />
            <stop offset="1" stopColor="#3B82F6" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

interface SidebarProps {
  isOpen: boolean;
}

export default function Sidebar({ isOpen }: SidebarProps) {
  const { user, logout } = useAuthStore();

  return (
    <motion.aside 
      initial={false}
      animate={{ width: isOpen ? 260 : 72 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="h-dvh flex flex-col bg-surface/80 backdrop-blur-md border-r border-border-subtle shrink-0 relative overflow-hidden"
    >
      {/* Subtle grid background */}
      <div className="absolute inset-0 grid-bg-dense pointer-events-none opacity-40" />

      {/* Logo */}
      <div className="relative z-10 flex items-center gap-3 px-5 h-[72px] border-b border-border-subtle overflow-hidden">
        <ACLogo />
        {isOpen && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col">
            <span
              className="text-xs font-bold tracking-[0.12em] text-accent-cyan uppercase whitespace-nowrap"
              style={{ fontFamily: "var(--font-display)" }}
            >
              azna-cloud
            </span>
            <span className="text-[10px] text-muted tracking-wider whitespace-nowrap" style={{ fontFamily: "var(--font-body)" }}>
              Private Cloud
            </span>
          </motion.div>
        )}
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex-1 px-3 py-5 flex flex-col gap-0.5 overflow-y-auto">
        {navItems.map(({ to, icon: Icon, label }, i) => (
          <motion.div
            key={to}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              delay: 0.1 + i * 0.04,
              duration: 0.35,
              ease: [0.16, 1, 0.3, 1],
            }}
          >
            <NavLink
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                cn(
                  "relative flex items-center gap-3 px-3 h-10 rounded-[var(--radius-md)]",
                  "text-sm font-medium transition-all duration-300",
                  isActive
                    ? "text-accent-cyan"
                    : "text-secondary hover:text-primary hover:bg-elevated/50 nav-glow",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="sidebar-active"
                      className="absolute inset-0 rounded-[var(--radius-md)]"
                      style={{
                        background: "linear-gradient(135deg, rgba(10,239,255,0.08), rgba(59,130,246,0.04))",
                        border: "1px solid rgba(10,239,255,0.15)",
                        boxShadow: "0 0 20px rgba(10,239,255,0.05), inset 0 0 20px rgba(10,239,255,0.03)",
                      }}
                      transition={{ type: "spring", stiffness: 350, damping: 30 }}
                    />
                  )}
                  <Icon className="h-4 w-4 relative z-10 shrink-0" />
                  {isOpen && (
                    <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="relative z-10 flex-1 whitespace-nowrap" style={{ fontFamily: "var(--font-body)" }}>{label}</motion.span>
                  )}
                  {isActive && isOpen && (
                    <ChevronRight className="h-3 w-3 relative z-10 text-accent-cyan/50 shrink-0" />
                  )}
                </>
              )}
            </NavLink>
          </motion.div>
        ))}

        {/* Separator */}
        <div className="h-px bg-border-subtle/30 my-3 mx-3" />

        {/* Notifications nav item */}
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className={cn("flex items-center px-3 h-10 rounded-[var(--radius-md)] text-sm text-muted/50 cursor-not-allowed select-none", isOpen ? "gap-3" : "justify-center")}>
            <Bell className="h-4 w-4 shrink-0" />
            {isOpen && (
              <>
                <span className="flex-1 whitespace-nowrap" style={{ fontFamily: "var(--font-body)" }}>Notifications</span>
                <span className="text-[9px] uppercase tracking-wider px-1.5 py-0.5 rounded bg-elevated/50 text-muted/40 border border-border-subtle/30 shrink-0">
                  Soon
                </span>
              </>
            )}
          </div>
        </motion.div>

        {/* Admin Portal link — only for admins */}
        {user?.role === "admin" && (
          <>
            <div className="h-px bg-border-subtle/30 my-3 mx-3" />
            <motion.div
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            >
              <NavLink
                to="/admin"
                className={cn("relative flex items-center px-3 h-10 rounded-[var(--radius-md)] text-sm font-medium text-accent-amber hover:bg-accent-amber/5 transition-all duration-300 nav-glow overflow-hidden", isOpen ? "gap-3" : "justify-center")}
              >
                <Shield className="h-4 w-4 shrink-0" />
                {isOpen && (
                  <>
                    <span className="whitespace-nowrap" style={{ fontFamily: "var(--font-body)" }}>Admin Portal</span>
                    <ChevronRight className="h-3 w-3 ml-auto text-accent-amber/50 shrink-0" />
                  </>
                )}
              </NavLink>
            </motion.div>
          </>
        )}
      </nav>

      {/* User section */}
      <div className="relative z-10 px-3 py-4 border-t border-border-subtle">
        <div className={cn("flex items-center mb-3", isOpen ? "gap-3 px-3" : "justify-center px-0")}>
          <div className="relative shrink-0">
            <div className="h-9 w-9 rounded-full flex items-center justify-center text-xs font-bold text-accent-cyan uppercase"
              style={{
                background: "linear-gradient(135deg, rgba(10,239,255,0.15), rgba(59,130,246,0.1))",
                border: "1px solid rgba(10,239,255,0.2)",
                fontFamily: "var(--font-display)",
              }}
            >
              {user?.username?.charAt(0) ?? "?"}
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full bg-accent-green border-2 border-surface" />
          </div>
          {isOpen && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex-1 min-w-0">
              <p className="text-sm font-medium text-primary truncate" style={{ fontFamily: "var(--font-body)" }}>
                {user?.username ?? "Loading..."}
              </p>
              <p className="text-[10px] text-muted uppercase tracking-wider" style={{ fontFamily: "var(--font-display)" }}>
                {user?.role ?? "user"}
              </p>
            </motion.div>
          )}
        </div>
        <button
          onClick={logout}
          className={cn("flex items-center h-9 w-full rounded-[var(--radius-md)] text-sm text-secondary hover:text-accent-red hover:bg-accent-red/5 transition-all duration-200 cursor-pointer group nav-glow", isOpen ? "gap-3 px-3" : "justify-center")}
          style={{ fontFamily: "var(--font-body)" }}
          title={!isOpen ? "Sign out" : undefined}
        >
          <LogOut className="h-4 w-4 shrink-0 transition-transform group-hover:-translate-x-0.5" />
          {isOpen && <span className="whitespace-nowrap">Sign out</span>}
        </button>
      </div>
    </motion.aside>
  );
}
