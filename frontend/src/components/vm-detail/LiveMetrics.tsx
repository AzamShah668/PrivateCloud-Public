import { MemoryStick, ArrowDownToLine, ArrowUpFromLine, Clock } from "lucide-react";
import AnimatedNumber from "@/components/shared/AnimatedNumber";
import { formatBytes, formatUptime } from "@/lib/format";
import type { VMEnriched } from "@/api/vms";

interface LiveMetricsProps {
  vm: VMEnriched;
}

function GaugeRing({
  pct,
  color,
  label,
  children,
}: {
  pct: number;
  color: string;
  label: string;
  children: React.ReactNode;
}) {
  const r = 42;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative h-28 w-28">
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
          <circle cx="50" cy="50" r={r} fill="none" stroke="var(--color-elevated)" strokeWidth="5" />
          <circle
            cx="50"
            cy="50"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="5"
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            className="transition-all duration-700 ease-out"
            style={{
              filter: `drop-shadow(0 0 6px ${color})`,
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-bold font-mono text-primary">{children}</span>
        </div>
      </div>
      <span className="text-[9px] text-muted uppercase tracking-[0.1em] font-semibold">{label}</span>
    </div>
  );
}

export default function LiveMetrics({ vm }: LiveMetricsProps) {
  const cpuPct = vm.cpu_usage != null ? vm.cpu_usage * 100 : 0;
  const memPct =
    vm.mem_usage != null && vm.max_mem
      ? (vm.mem_usage / vm.max_mem) * 100
      : 0;

  return (
    <div className="space-y-6">
      {/* Gauges */}
      <div className="flex items-center justify-center gap-10">
        <GaugeRing pct={cpuPct} color="var(--color-accent-blue)" label="CPU">
          <AnimatedNumber value={cpuPct} decimals={1} suffix="%" />
        </GaugeRing>
        <GaugeRing pct={memPct} color="var(--color-accent-cyan)" label="Memory">
          <AnimatedNumber value={memPct} decimals={1} suffix="%" />
        </GaugeRing>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <StatCard
          icon={<MemoryStick className="h-3.5 w-3.5" />}
          label="RAM Used"
          value={vm.mem_usage != null ? formatBytes(vm.mem_usage) : "—"}
        />
        <StatCard
          icon={<MemoryStick className="h-3.5 w-3.5" />}
          label="RAM Total"
          value={vm.max_mem != null ? formatBytes(vm.max_mem) : "—"}
        />
        <StatCard
          icon={<ArrowDownToLine className="h-3.5 w-3.5" />}
          label="Net In"
          value={vm.netin != null ? formatBytes(vm.netin) : "—"}
        />
        <StatCard
          icon={<ArrowUpFromLine className="h-3.5 w-3.5" />}
          label="Net Out"
          value={vm.netout != null ? formatBytes(vm.netout) : "—"}
        />
      </div>

      {/* Uptime */}
      <div className="flex items-center gap-2 text-xs text-secondary">
        <Clock className="h-3.5 w-3.5 text-muted" />
        <span className="font-mono">Uptime: {formatUptime(vm.uptime)}</span>
      </div>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-[var(--radius-md)] bg-elevated/50 border border-border-subtle p-3">
      <span className="text-[9px] text-muted uppercase tracking-[0.1em] flex items-center gap-1 mb-1 font-semibold">
        {icon} {label}
      </span>
      <span className="text-sm font-mono font-semibold text-primary">{value}</span>
    </div>
  );
}
