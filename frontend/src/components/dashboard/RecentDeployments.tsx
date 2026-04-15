import { motion } from "motion/react";
import { MoreHorizontal, AlertTriangle, CheckCircle } from "lucide-react";
import Badge from "@/components/ui/Badge";
import type { VMEnriched } from "@/api/vms";

interface RecentDeploymentsProps {
  vms?: VMEnriched[];
}

// Mock data for when no VMs exist
const mockDeployments = [
  { id: "0010070-01", status: "running", type: "RUNNING", owner: "Admin", os: "ubuntu-24.04" },
  { id: "0010070-11", status: "failed", type: "TERMINATED", owner: "Adam", os: "debian-12" },
  { id: "0010070-02", status: "paused", type: "ALERTS", owner: "Admin", os: "centos-9" },
];

export default function RecentDeployments({ vms }: RecentDeploymentsProps) {
  const hasRealData = vms && vms.length > 0;

  // Build rows from real data or fall back to mock
  const rows = hasRealData
    ? vms.slice(0, 6).map((vm) => ({
        id: `${vm.vmid}`,
        name: vm.vm_name,
        status: vm.live_status ?? vm.status,
        type: vm.live_status === "running" ? "RUNNING" : vm.status === "failed" ? "TERMINATED" : vm.status.toUpperCase(),
        owner: "Admin",
        os: vm.os_choice,
      }))
    : mockDeployments.map((d) => ({
        id: d.id,
        name: `instance-${d.id}`,
        status: d.status,
        type: d.type,
        owner: d.owner,
        os: d.os,
      }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2
          className="text-xs font-bold uppercase tracking-[0.15em] text-primary"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Recent Deployments
        </h2>
        <button className="p-1 rounded-[var(--radius-sm)] text-muted hover:text-primary hover:bg-elevated transition-colors cursor-pointer">
          <MoreHorizontal className="h-4 w-4" />
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-[10px] text-muted uppercase tracking-[0.1em] border-b border-border-subtle">
              <th className="pb-2.5 pr-4 font-semibold">Instance ID</th>
              <th className="pb-2.5 pr-4 font-semibold">Status</th>
              <th className="pb-2.5 pr-4 font-semibold">Type</th>
              <th className="pb-2.5 pr-4 font-semibold">Owner</th>
              <th className="pb-2.5 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <motion.tr
                key={row.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  delay: 0.4 + i * 0.08,
                  duration: 0.35,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="border-b border-border-subtle/50 hover:bg-elevated/30 transition-colors"
              >
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    {row.status === "running" ? (
                      <CheckCircle className="h-3 w-3 text-accent-green" />
                    ) : row.status === "failed" ? (
                      <AlertTriangle className="h-3 w-3 text-accent-red" />
                    ) : (
                      <AlertTriangle className="h-3 w-3 text-accent-amber" />
                    )}
                    <span className="font-mono text-primary">{row.id}</span>
                  </div>
                </td>
                <td className="py-3 pr-4">
                  <Badge status={row.status} />
                </td>
                <td className="py-3 pr-4">
                  <span className="text-secondary font-medium">{row.type}</span>
                </td>
                <td className="py-3 pr-4">
                  <span className="text-secondary">{row.owner}</span>
                </td>
                <td className="py-3">
                  <button className="p-1 rounded text-muted hover:text-primary hover:bg-elevated transition-colors cursor-pointer">
                    <MoreHorizontal className="h-3.5 w-3.5" />
                  </button>
                </td>
              </motion.tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
