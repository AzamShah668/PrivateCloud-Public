import { motion } from "motion/react";
import {
  Users,
  Server,
  Activity,
  AlertTriangle,
  Zap,
} from "lucide-react";
import { useAdminStats, useAdminVMs, useAdminAuditLogs } from "@/hooks/use-admin";
import AnimatedStatCard from "@/components/dashboard/AnimatedStatCard";
import AdminClusterHealth from "@/components/admin/AdminClusterHealth";
import AdminLiveCharts from "@/components/admin/AdminLiveCharts";
import AdminRecentActivity from "@/components/admin/AdminRecentActivity";
import GlitchText from "@/components/ui/GlitchText";

export default function AdminDashboardPage() {
  const { data: stats } = useAdminStats();
  const { data: vms } = useAdminVMs();
  const { data: logs } = useAdminAuditLogs();

  return (
    <div className="p-6 space-y-6">
      {/* Page header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <GlitchText
          text="Command Center"
          className="text-2xl font-bold text-primary tracking-tight"
        />
        <p
          className="text-sm text-muted mt-1"
          style={{ fontFamily: "var(--font-body)" }}
        >
          Infrastructure overview and system health monitoring
        </p>
      </motion.div>

      {/* Stat cards row */}
      <div className="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-5 gap-4">
        <AnimatedStatCard
          label="Total Users"
          value={stats?.total_users ?? 0}
          icon={<Users className="h-4 w-4" />}
          color="var(--color-accent-cyan)"
          delay={0.1}
        />
        <AnimatedStatCard
          label="Active VMs"
          value={stats?.active_vms ?? 0}
          icon={<Server className="h-4 w-4" />}
          color="var(--color-accent-green)"
          delay={0.15}
        />
        <AnimatedStatCard
          label="Failed Jobs"
          value={stats?.failed_vms ?? 0}
          icon={<AlertTriangle className="h-4 w-4" />}
          color="var(--color-accent-red)"
          delay={0.2}
        />
        <AnimatedStatCard
          label="Today's Deploys"
          value={stats?.vms_created_today ?? 0}
          icon={<Zap className="h-4 w-4" />}
          color="var(--color-accent-blue)"
          delay={0.25}
        />
        <AnimatedStatCard
          label="Audit Events"
          value={stats?.total_audit_entries ?? 0}
          icon={<Activity className="h-4 w-4" />}
          color="var(--color-accent-amber)"
          delay={0.3}
        />
      </div>

      {/* Main grid: Cluster Health + Live Charts */}
      <div className="grid grid-cols-12 gap-6">
        {/* Cluster Health — left 7 cols */}
        <div className="col-span-12 xl:col-span-7">
          <AdminClusterHealth
            totalVMs={stats?.total_vms ?? 0}
            activeVMs={stats?.active_vms ?? 0}
            totalUsers={stats?.total_users ?? 0}
          />
        </div>

        {/* Live Charts — right 5 cols */}
        <div className="col-span-12 xl:col-span-5">
          <AdminLiveCharts />
        </div>
      </div>

      {/* Recent Activity */}
      <AdminRecentActivity logs={logs ?? []} vms={vms ?? []} />
    </div>
  );
}
