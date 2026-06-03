import { Routes, Route, Navigate } from "react-router-dom";
import { AnimatePresence } from "motion/react";
import { useLocation } from "react-router-dom";
import { useAuthStore } from "@/stores/auth-store";

// Pages (lazy-loaded later, direct imports for now)
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import DashboardPage from "@/pages/DashboardPage";
import CreateVMPage from "@/pages/CreateVMPage";
import VMDetailPage from "@/pages/VMDetailPage";
import ChatOpsPage from "@/pages/ChatOpsPage";
import NotFoundPage from "@/pages/NotFoundPage";

// Admin pages
import AdminDashboardPage from "@/pages/admin/AdminDashboardPage";
import AdminVMsPage from "@/pages/admin/AdminVMsPage";
import AdminUsersPage from "@/pages/admin/AdminUsersPage";
import AdminAuditLogsPage from "@/pages/admin/AdminAuditLogsPage";
import AdminSettingsPage from "@/pages/admin/AdminSettingsPage";
import AdminKnowledgePage from "@/pages/admin/AdminKnowledgePage";
import AdminTemplatesPage from "@/pages/admin/AdminTemplatesPage";
import AdminClassesPage from "@/pages/admin/AdminClassesPage";

// Layout
import AppShell from "@/components/layout/AppShell";
import AdminShell from "@/components/admin/AdminShell";
import ProtectedRoute from "@/components/shared/ProtectedRoute";
import AdminRoute from "@/components/shared/AdminRoute";

export default function App() {
  const location = useLocation();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={location.pathname}>
        {/* Public routes */}
        <Route
          path="/login"
          element={
            isAuthenticated ? <Navigate to="/" replace /> : <LoginPage />
          }
        />
        <Route
          path="/register"
          element={
            isAuthenticated ? <Navigate to="/" replace /> : <RegisterPage />
          }
        />

        {/* Protected routes — wrapped in AppShell */}
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="/vms/create" element={<CreateVMPage />} />
            <Route path="/chatops" element={<ChatOpsPage />} />
            <Route path="/vms/:jobId" element={<VMDetailPage />} />
          </Route>

          {/* Admin routes — wrapped in AdminShell + AdminRoute guard */}
          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminShell />}>
              <Route index element={<AdminDashboardPage />} />
              <Route path="vms" element={<AdminVMsPage />} />
              <Route path="templates" element={<AdminTemplatesPage />} />
              <Route path="classes" element={<AdminClassesPage />} />
              <Route path="users" element={<AdminUsersPage />} />
              <Route path="audit-logs" element={<AdminAuditLogsPage />} />
              <Route path="knowledge" element={<AdminKnowledgePage />} />
              <Route path="settings" element={<AdminSettingsPage />} />
            </Route>
          </Route>
        </Route>

        {/* 404 */}
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AnimatePresence>
  );
}
