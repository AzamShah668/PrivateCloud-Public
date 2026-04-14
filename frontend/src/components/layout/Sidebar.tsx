import { NavLink } from "react-router-dom";
import { LayoutDashboard, PlusCircle, LogOut, Cloud } from "lucide-react";
import { useAuthStore } from "@/stores/auth-store";
import { cn } from "@/lib/cn";

const navItems = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/vms/create", icon: PlusCircle, label: "Create VM" },
];

export default function Sidebar() {
  const { user, logout } = useAuthStore();

  return (
    <aside className="w-[240px] h-dvh flex flex-col bg-surface border-r border-border-subtle shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-16 border-b border-border-subtle">
        <Cloud className="h-5 w-5 text-accent-blue" />
        <span
          className="text-sm font-bold tracking-[0.06em] text-primary"
          style={{ fontFamily: "var(--font-display)" }}
        >
          PrivateCloud
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 flex flex-col gap-1">
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 px-3 h-10 rounded-[var(--radius-md)]",
                "text-sm font-medium transition-all duration-200",
                isActive
                  ? "bg-accent-blue/10 text-accent-blue border-l-2 border-accent-blue shadow-[inset_0_0_12px_var(--color-accent-blue-glow)]"
                  : "text-secondary hover:text-primary hover:bg-elevated",
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div className="px-3 py-4 border-t border-border-subtle">
        <div className="flex items-center gap-3 px-3 mb-3">
          <div className="h-8 w-8 rounded-full bg-accent-blue/20 flex items-center justify-center text-xs font-bold text-accent-blue uppercase">
            {user?.username?.charAt(0) ?? "?"}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-primary truncate">
              {user?.username ?? "Loading..."}
            </p>
            <p className="text-xs text-muted">{user?.role ?? ""}</p>
          </div>
        </div>
        <button
          onClick={logout}
          className="flex items-center gap-3 px-3 h-9 w-full rounded-[var(--radius-md)] text-sm text-secondary hover:text-accent-red hover:bg-accent-red/5 transition-colors cursor-pointer"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
