import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/auth-store";
import { useCurrentUser } from "@/hooks/use-auth";
import { useSetupStatus } from "@/hooks/use-setup";
import Spinner from "@/components/ui/Spinner";

export default function ProtectedRoute() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const location = useLocation();
  const { isLoading } = useCurrentUser();

  const isAdmin = user?.role === "admin";
  // Only admins can complete (and therefore need) first-run setup.
  const { data: setup, isLoading: setupLoading } = useSetupStatus(
    isAuthenticated && isAdmin,
  );

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (isLoading || (isAdmin && setupLoading)) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-deepest">
        <Spinner size="lg" />
      </div>
    );
  }

  const onSetupPage = location.pathname === "/setup";

  // First run: an admin must finish setup before using the rest of the app.
  if (isAdmin && setup && !setup.completed && !onSetupPage) {
    return <Navigate to="/setup" replace />;
  }

  // Keep the wizard out of reach once setup is done (or for non-admins).
  if (onSetupPage && (!isAdmin || setup?.completed)) {
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
