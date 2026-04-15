import { Navigate, Outlet } from "react-router-dom";
import { useAuthStore } from "@/stores/auth-store";
import Spinner from "@/components/ui/Spinner";

export default function AdminRoute() {
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  // Not authenticated at all — redirect to login
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Authenticated but user profile hasn't loaded yet (useCurrentUser still hydrating)
  if (!user) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-deepest">
        <Spinner size="lg" />
      </div>
    );
  }

  // Authenticated, user loaded, but not admin — redirect to dashboard
  if (user.role !== "admin") {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
