import { Link } from "react-router-dom";
import { PlusCircle, AlertTriangle } from "lucide-react";
import { motion } from "motion/react";
import MyInstances from "@/components/dashboard/MyInstances";
import ResourceQuota from "@/components/dashboard/ResourceQuota";
import RecentActivity from "@/components/dashboard/RecentActivity";
import QuickDeploy from "@/components/dashboard/QuickDeploy";
import QuotaIndicator from "@/components/dashboard/QuotaIndicator";
import Button from "@/components/ui/Button";
import GlitchText from "@/components/ui/GlitchText";
import { useVMs } from "@/hooks/use-vms";
import AIChatOps from "@/components/dashboard/AIChatOps";

export default function DashboardPage() {
  const { data: vms, isError } = useVMs();

  const todayCount =
    vms?.filter((vm) => {
      const created = new Date(vm.created_at);
      const now = new Date();
      return (
        created.getFullYear() === now.getFullYear() &&
        created.getMonth() === now.getMonth() &&
        created.getDate() === now.getDate()
      );
    }).length ?? 0;

  return (
    <div className="flex flex-col h-full">
      {/* Page header bar */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="flex items-center justify-between px-6 py-4 border-b border-border-subtle/50"
      >
        <div>
          <GlitchText
            text="Dashboard"
            className="text-2xl font-bold text-primary mb-1"
          />
          <p className="text-sm text-muted mt-0.5" style={{ fontFamily: "var(--font-body)" }}>
            Your cloud infrastructure at a glance
          </p>
        </div>
        <div className="flex items-center gap-4">
          <QuotaIndicator usedToday={todayCount} />
          <Link to="/vms/create">
            <Button>
              <PlusCircle className="h-4 w-4" />
              Deploy Instance
            </Button>
          </Link>
        </div>
      </motion.div>

      {/* Dashboard Grid */}
      <main className="flex-1 overflow-y-auto p-6">
        {isError && (
          <div className="flex items-center gap-2 mb-4 p-3 rounded-[var(--radius-md)] bg-accent-red/5 border border-accent-red/20 text-xs text-accent-red">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            Failed to load VMs. Data shown may be stale.
          </div>
        )}
        <div className="grid grid-cols-1 xl:grid-cols-12 gap-5">
          {/* Row 1: My Instances (large) + Resource Quota */}
          <div className="xl:col-span-7">
            <MyInstances vms={vms} />
          </div>

          <div className="xl:col-span-5">
            <ResourceQuota vms={vms} />
          </div>

          {/* Row 2: Recent Activity + Quick Deploy */}
          <div className="xl:col-span-7">
            <RecentActivity vms={vms} />
          </div>
          <div className="xl:col-span-5">
            <AIChatOps />
          </div>

          <div className="xl:col-span-5">
            <QuickDeploy />
          </div>
        </div>
      </main>
    </div>
  );
}
