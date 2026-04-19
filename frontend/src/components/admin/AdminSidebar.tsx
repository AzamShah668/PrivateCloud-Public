import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Server,
  Users,
  ScrollText,
  Settings,
  LogOut,
  ChevronRight,
  ArrowLeft,
  Shield,
} from "lucide-react";
import { motion } from "motion/react";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/cn";
import GlitchText from "@/components/ui/GlitchText";

const navItems = [
  { to: "/admin", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/admin/vms", icon: Server, label: "Virtual Machines" },
  { to: "/admin/users", icon: Users, label: "User Management" },
  { to: "/admin/audit-logs", icon: ScrollText, label: "Audit Logs" },
];

const bottomItems = [
  { to: "/admin/settings", icon: Settings, label: "Admin Settings" },
];

function AdminLogo() {
  return (
    <div className="relative flex items-center justify-center h-10 w-10 rounded-[var(--radius-md)]">
      <div
        className="absolute inset-0 rounded-[var(--radius-md)] opacity-40"
        style={{
          background:
            "linear-gradient(135deg, rgba(245,158,11,0.3), rgba(239,68,68,0.15))",
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
        <circle
          cx="20"
          cy="20"
          r="18"
          stroke="url(#admin-logo-grad)"
          strokeWidth="1.5"
          opacity="0.6"
        />
        <path
          d="M14 28L20 12L26 28M16 23H24"
          stroke="url(#admin-logo-grad)"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        <path
          d="M28 16C26 13 23 12 20 12C15 12 12 16 12 20C12 24 15 28 20 28C23 28 26 27 28 24"
          stroke="url(#admin-logo-grad)"
          strokeWidth="1.5"
          strokeLinecap="round"
          opacity="0.5"
        />
        <defs>
          <linearGradient
            id="admin-logo-grad"
            x1="0"
            y1="0"
            x2="40"
            y2="40"
          >
            <stop stopColor="#F59E0B" />
            <stop offset="1" stopColor="#EF4444" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}

export default function AdminSidebar({ onClose }: { onClose?: () => void }) {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  return (
    <aside className="w-[260px] h-dvh flex flex-col bg-surface/80 backdrop-blur-md border-r border-border-subtle shrink-0 relative overflow-hidden">
      <div className="absolute inset-0 grid-bg-dense pointer-events-none opacity-40" />

      {/* Logo */}
      <div className="relative z-10 flex items-center gap-3 px-5 h-[72px] border-b border-border-subtle">
        <AdminLogo />
        <div className="flex flex-col">
          <span
            className="text-xs font-bold tracking-[0.12em] text-accent-amber uppercase"
            style={{ fontFamily: "var(--font-display)" }}
          >
            azna-cloud
          </span>
          <span
            className="text-[10px] text-muted tracking-wider"
            style={{ fontFamily: "var(--font-body)" }}
          >
            Admin Console
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex-1 px-3 py-5 flex flex-col gap-0.5 overflow-y-auto">
        {/* Back to user dashboard */}
        <motion.div
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.05, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        >
          <button
            onClick={() => navigate("/")}
            className="flex items-center gap-3 px-3 h-9 w-full rounded-[var(--radius-md)] text-xs text-muted hover:text-accent-cyan hover:bg-elevated/50 transition-all duration-200 cursor-pointer group"
            style={{ fontFamily: "var(--font-body)" }}
          >
            <ArrowLeft className="h-3.5 w-3.5 transition-transform group-hover:-translate-x-0.5" />
            Back to Dashboard
          </button>
        </motion.div>

        <div className="h-px bg-border-subtle/30 my-2 mx-3" />

        {/* Section label */}
        <div className="px-3 py-1.5">
          <span
            className="text-[9px] font-bold uppercase tracking-[0.15em] text-muted/50"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Management
          </span>
        </div>

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
              end={to === "/admin"}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  "relative flex items-center gap-3 px-3 h-10 rounded-[var(--radius-md)]",
                  "text-sm font-medium transition-all duration-300 group",
                  isActive
                    ? "text-accent-amber"
                    : "text-secondary hover:text-primary hover:bg-elevated/50 nav-glow"
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="admin-sidebar-active"
                      className="absolute inset-0 rounded-[var(--radius-md)]"
                      style={{
                        background:
                          "linear-gradient(135deg, rgba(245,158,11,0.08), rgba(239,68,68,0.04))",
                        border: "1px solid rgba(245,158,11,0.15)",
                        boxShadow:
                          "0 0 20px rgba(245,158,11,0.05), inset 0 0 20px rgba(245,158,11,0.03)",
                      }}
                      transition={{
                        type: "spring",
                        stiffness: 350,
                        damping: 30,
                      }}
                    />
                  )}
                  <Icon className="h-4 w-4 relative z-10" />
                  {isActive ? (
                    <div className="relative z-10 flex-1 overflow-hidden" style={{ fontFamily: "var(--font-display)" }}>
                      <GlitchText text={label} className="font-bold tracking-wide" />
                    </div>
                  ) : (
                    <span
                      className="relative z-10 flex-1 group-hover:translate-x-1 transition-transform duration-300"
                      style={{ fontFamily: "var(--font-body)" }}
                    >
                      {label}
                    </span>
                  )}
                  {isActive && (
                    <ChevronRight className="h-3 w-3 relative z-10 text-accent-amber/50" />
                  )}
                </>
              )}
            </NavLink>
          </motion.div>
        ))}

        <div className="h-px bg-border-subtle/30 my-3 mx-3" />

        {/* Section label */}
        <div className="px-3 py-1.5">
          <span
            className="text-[9px] font-bold uppercase tracking-[0.15em] text-muted/50"
            style={{ fontFamily: "var(--font-display)" }}
          >
            System
          </span>
        </div>

        {bottomItems.map(({ to, icon: Icon, label }, i) => (
          <motion.div
            key={to}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              delay: 0.25 + i * 0.04,
              duration: 0.35,
              ease: [0.16, 1, 0.3, 1],
            }}
          >
            <NavLink
              to={to}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  "relative flex items-center gap-3 px-3 h-10 rounded-[var(--radius-md)]",
                  "text-sm font-medium transition-all duration-300 group",
                  isActive
                    ? "text-accent-amber"
                    : "text-secondary hover:text-primary hover:bg-elevated/50 nav-glow"
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <motion.div
                      layoutId="admin-sidebar-active"
                      className="absolute inset-0 rounded-[var(--radius-md)]"
                      style={{
                        background:
                          "linear-gradient(135deg, rgba(245,158,11,0.08), rgba(239,68,68,0.04))",
                        border: "1px solid rgba(245,158,11,0.15)",
                        boxShadow:
                          "0 0 20px rgba(245,158,11,0.05), inset 0 0 20px rgba(245,158,11,0.03)",
                      }}
                      transition={{
                        type: "spring",
                        stiffness: 350,
                        damping: 30,
                      }}
                    />
                  )}
                  <Icon className="h-4 w-4 relative z-10" />
                  {isActive ? (
                    <div className="relative z-10 flex-1 overflow-hidden" style={{ fontFamily: "var(--font-display)" }}>
                      <GlitchText text={label} className="font-bold tracking-wide" />
                    </div>
                  ) : (
                    <span
                      className="relative z-10 flex-1 group-hover:translate-x-1 transition-transform duration-300"
                      style={{ fontFamily: "var(--font-body)" }}
                    >
                      {label}
                    </span>
                  )}
                  {isActive && (
                    <ChevronRight className="h-3 w-3 relative z-10 text-accent-amber/50" />
                  )}
                </>
              )}
            </NavLink>
          </motion.div>
        ))}
      </nav>

      {/* User section */}
      <div className="relative z-10 px-3 py-4 border-t border-border-subtle">
        <div className="flex items-center gap-3 px-3 mb-3">
          <div className="relative">
            <div
              className="h-9 w-9 rounded-full flex items-center justify-center text-xs font-bold text-accent-amber uppercase"
              style={{
                background:
                  "linear-gradient(135deg, rgba(245,158,11,0.15), rgba(239,68,68,0.1))",
                border: "1px solid rgba(245,158,11,0.2)",
                fontFamily: "var(--font-display)",
              }}
            >
              {user?.username?.charAt(0) ?? "?"}
            </div>
            <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full bg-accent-green border-2 border-surface" />
          </div>
          <div className="flex-1 min-w-0">
            <p
              className="text-sm font-medium text-primary truncate"
              style={{ fontFamily: "var(--font-body)" }}
            >
              {user?.username ?? "Loading..."}
            </p>
            <div className="flex items-center gap-1.5">
              <Shield className="h-2.5 w-2.5 text-accent-amber" />
              <p
                className="text-[10px] text-accent-amber uppercase tracking-wider"
                style={{ fontFamily: "var(--font-display)" }}
              >
                Administrator
              </p>
            </div>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 h-9 w-full rounded-[var(--radius-md)] text-sm text-secondary hover:text-accent-red hover:bg-accent-red/5 transition-all duration-200 cursor-pointer group nav-glow"
          style={{ fontFamily: "var(--font-body)" }}
        >
          <LogOut className="h-4 w-4 transition-transform group-hover:-translate-x-0.5" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
