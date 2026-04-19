import { motion } from "motion/react";
import {
  Plus,
  Play,
  Square,
  RotateCcw,
  Trash2,
  Maximize2,
  Clock,
} from "lucide-react";
import type { VMEnriched } from "@/api/vms";
import SpotlightCard from "@/components/ui/SpotlightCard";
import GlitchText from "@/components/ui/GlitchText";

interface RecentActivityProps {
  vms?: VMEnriched[];
}

interface ActivityEvent {
  id: string;
  action: string;
  icon: React.ReactNode;
  color: string;
  vmName: string;
  timestamp: Date;
}

function getTimeDiff(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  return `${diffDays}d ago`;
}

function deriveActivities(vms: VMEnriched[]): ActivityEvent[] {
  const events: ActivityEvent[] = [];

  for (const vm of vms) {
    // Created event
    events.push({
      id: `${vm.id}-created`,
      action: "Instance created",
      icon: <Plus className="h-3 w-3" />,
      color: "#10B981",
      vmName: vm.vm_name,
      timestamp: new Date(vm.created_at),
    });

    // If updated after creation, add an update event
    if (vm.updated_at !== vm.created_at) {
      const status = vm.live_status ?? vm.status;
      let actionText = "Instance updated";
      let icon = <RotateCcw className="h-3 w-3" />;
      let color = "#3B82F6";

      if (status === "running") {
        actionText = "Instance started";
        icon = <Play className="h-3 w-3" />;
        color = "#10B981";
      } else if (status === "stopped") {
        actionText = "Instance stopped";
        icon = <Square className="h-3 w-3" />;
        color = "#F59E0B";
      } else if (status === "failed") {
        actionText = "Deployment failed";
        icon = <Trash2 className="h-3 w-3" />;
        color = "#EF4444";
      } else if (vm.status === "deleted") {
        actionText = "Instance deleted";
        icon = <Trash2 className="h-3 w-3" />;
        color = "#6B7280";
      } else if (status === "done") {
        actionText = "Deployment completed";
        icon = <Maximize2 className="h-3 w-3" />;
        color = "#0AEFFF";
      }

      events.push({
        id: `${vm.id}-updated`,
        action: actionText,
        icon,
        color,
        vmName: vm.vm_name,
        timestamp: new Date(vm.updated_at),
      });
    }
  }

  // Sort by most recent first
  events.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  return events.slice(0, 8);
}

export default function RecentActivity({ vms }: RecentActivityProps) {
  const activities = vms ? deriveActivities(vms) : [];

  return (
    <SpotlightCard
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.25, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="p-6 relative overflow-hidden"
    >
      {/* Top accent line */}
      <div
        className="absolute top-0 left-6 right-6 h-[1px]"
        style={{
          background: "linear-gradient(90deg, transparent, rgba(20,184,166,0.15), transparent)",
        }}
      />

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <GlitchText
          text="Recent Activity"
          className="text-base font-bold tracking-wide text-primary"
        />
        <Clock className="h-3.5 w-3.5 text-muted" />
      </div>

      {activities.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <Clock className="h-8 w-8 text-muted/30 mb-3" />
          <p className="text-xs text-muted">No activity yet</p>
        </div>
      ) : (
        <div className="relative">
          {/* Timeline line */}
          <div className="absolute left-[11px] top-2 bottom-2 w-[1px] bg-border-subtle/50" />

          <div className="space-y-1">
            {activities.map((event, i) => (
              <motion.div
                key={event.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{
                  delay: 0.3 + i * 0.06,
                  duration: 0.35,
                  ease: [0.16, 1, 0.3, 1],
                }}
                className="relative flex items-start gap-3 px-3 py-2 -ml-3 rounded-xl border border-transparent hover:border-border-subtle/30 hover:bg-surface/50 hover:shadow-lg transition-all duration-300"
              >
                {/* Timeline dot */}
                <div
                  className="relative z-10 flex items-center justify-center h-[22px] w-[22px] rounded-full shrink-0"
                  style={{
                    background: `${event.color}15`,
                    border: `1px solid ${event.color}30`,
                  }}
                >
                  <span style={{ color: event.color }}>{event.icon}</span>
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 pt-0.5">
                  <p className="text-xs text-primary" style={{ fontFamily: "var(--font-body)" }}>
                    <span className="font-medium">{event.action}</span>
                    <span className="text-muted"> — </span>
                    <span className="text-secondary">{event.vmName}</span>
                  </p>
                  <p className="text-[10px] text-muted font-mono mt-0.5">
                    {getTimeDiff(event.timestamp)}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </SpotlightCard>
  );
}
