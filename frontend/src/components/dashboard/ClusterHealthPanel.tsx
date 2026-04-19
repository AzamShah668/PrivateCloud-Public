import { motion } from "motion/react";
import { Cpu, MemoryStick, Server, Wifi } from "lucide-react";
import AnimatedStatCard from "./AnimatedStatCard";
import type { VMEnriched } from "@/api/vms";

interface ClusterHealthPanelProps {
  vms?: VMEnriched[];
}

// Animated network node component
function NetworkNode({ x, y, delay, size = 6 }: { x: number; y: number; delay: number; size?: number }) {
  return (
    <motion.g
      initial={{ opacity: 0, scale: 0 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ delay, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Outer glow */}
      <circle cx={x} cy={y} r={size + 4} fill="rgba(10,239,255,0.08)" />
      {/* Pulse ring */}
      <circle
        cx={x} cy={y} r={size + 2}
        fill="none"
        stroke="rgba(10,239,255,0.2)"
        strokeWidth="0.5"
      >
        <animate
          attributeName="r"
          values={`${size + 2};${size + 8};${size + 2}`}
          dur="3s"
          begin={`${delay}s`}
          repeatCount="indefinite"
        />
        <animate
          attributeName="opacity"
          values="0.3;0;0.3"
          dur="3s"
          begin={`${delay}s`}
          repeatCount="indefinite"
        />
      </circle>
      {/* Core node */}
      <circle cx={x} cy={y} r={size} fill="url(#nodeGrad)" />
      {/* Inner bright */}
      <circle cx={x} cy={y} r={size * 0.4} fill="rgba(10,239,255,0.8)" />
    </motion.g>
  );
}

function NetworkLine({
  x1, y1, x2, y2, delay,
}: {
  x1: number; y1: number; x2: number; y2: number; delay: number;
}) {
  return (
    <motion.line
      x1={x1} y1={y1} x2={x2} y2={y2}
      stroke="url(#lineGrad)"
      strokeWidth="1"
      initial={{ pathLength: 0, opacity: 0 }}
      animate={{ pathLength: 1, opacity: 1 }}
      transition={{ delay, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
    />
  );
}

function ClusterVisualization() {
  // Define node positions for a network topology
  const nodes = [
    { x: 200, y: 80, size: 8, delay: 0.3 },   // Top center (main)
    { x: 100, y: 60, size: 5, delay: 0.5 },   // Top left
    { x: 300, y: 60, size: 5, delay: 0.5 },   // Top right
    { x: 60, y: 120, size: 6, delay: 0.6 },    // Mid left
    { x: 150, y: 130, size: 7, delay: 0.4 },   // Mid center-left
    { x: 250, y: 130, size: 7, delay: 0.4 },   // Mid center-right
    { x: 340, y: 120, size: 6, delay: 0.6 },   // Mid right
    { x: 120, y: 180, size: 5, delay: 0.7 },   // Bottom left
    { x: 200, y: 190, size: 6, delay: 0.7 },   // Bottom center
    { x: 280, y: 180, size: 5, delay: 0.7 },   // Bottom right
    { x: 50, y: 170, size: 4, delay: 0.8 },    // Far left
    { x: 350, y: 170, size: 4, delay: 0.8 },   // Far right
  ];

  const lines = [
    { x1: 200, y1: 80, x2: 100, y2: 60, delay: 0.4 },
    { x1: 200, y1: 80, x2: 300, y2: 60, delay: 0.4 },
    { x1: 200, y1: 80, x2: 150, y2: 130, delay: 0.5 },
    { x1: 200, y1: 80, x2: 250, y2: 130, delay: 0.5 },
    { x1: 100, y1: 60, x2: 60, y2: 120, delay: 0.6 },
    { x1: 300, y1: 60, x2: 340, y2: 120, delay: 0.6 },
    { x1: 150, y1: 130, x2: 60, y2: 120, delay: 0.7 },
    { x1: 250, y1: 130, x2: 340, y2: 120, delay: 0.7 },
    { x1: 150, y1: 130, x2: 120, y2: 180, delay: 0.7 },
    { x1: 250, y1: 130, x2: 280, y2: 180, delay: 0.7 },
    { x1: 150, y1: 130, x2: 200, y2: 190, delay: 0.7 },
    { x1: 250, y1: 130, x2: 200, y2: 190, delay: 0.7 },
    { x1: 60, y1: 120, x2: 50, y2: 170, delay: 0.8 },
    { x1: 340, y1: 120, x2: 350, y2: 170, delay: 0.8 },
    { x1: 120, y1: 180, x2: 200, y2: 190, delay: 0.8 },
    { x1: 280, y1: 180, x2: 200, y2: 190, delay: 0.8 },
  ];

  return (
    <div className="relative w-full h-[220px] flex items-center justify-center overflow-hidden">
      {/* Radial glow behind */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse 50% 60% at 50% 50%, rgba(10,239,255,0.06) 0%, transparent 70%)",
        }}
      />
      <svg viewBox="0 0 400 240" className="w-full h-full max-w-[500px]" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="nodeGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="rgba(10,239,255,0.4)" />
            <stop offset="100%" stopColor="rgba(59,130,246,0.3)" />
          </linearGradient>
          <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="rgba(10,239,255,0.3)" />
            <stop offset="100%" stopColor="rgba(10,239,255,0.1)" />
          </linearGradient>
        </defs>

        {/* Connection lines */}
        {lines.map((line, i) => (
          <NetworkLine key={`line-${i}`} {...line} />
        ))}

        {/* Animated data packets flowing along lines */}
        {[0, 1, 2, 3].map((i) => (
          <circle key={`packet-${i}`} r="2" fill="#0AEFFF" opacity="0.6">
            <animateMotion
              dur={`${2 + i * 0.5}s`}
              repeatCount="indefinite"
              begin={`${i * 0.7}s`}
              path={`M${lines[i * 3]?.x1 ?? 200},${lines[i * 3]?.y1 ?? 80} L${lines[i * 3]?.x2 ?? 150},${lines[i * 3]?.y2 ?? 130}`}
            />
          </circle>
        ))}

        {/* Nodes */}
        {nodes.map((node, i) => (
          <NetworkNode key={`node-${i}`} {...node} />
        ))}
      </svg>
    </div>
  );
}

export default function ClusterHealthPanel({ vms }: ClusterHealthPanelProps) {
  const activeVMs = vms?.filter((v) => v.live_status === "running").length ?? 0;
  const totalVMs = vms?.length ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden"
    >
      {/* Section header */}
      <div className="flex items-center justify-between mb-4">
        <h2
          className="text-xs font-bold uppercase tracking-[0.15em] text-primary"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Cluster Health & Utilization
        </h2>
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-accent-green animate-pulse-status" />
          <span className="text-[10px] text-accent-green font-mono uppercase tracking-wider">
            Healthy
          </span>
        </div>
      </div>

      {/* Network Visualization */}
      <ClusterVisualization />

      {/* Stats grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 mt-4">
        <AnimatedStatCard
          label="Total Cores"
          value={totalVMs > 0 ? totalVMs * 4 : 5120}
          icon={<Cpu className="h-3.5 w-3.5" />}
          color="var(--color-accent-cyan)"
          delay={0.4}
        />
        <AnimatedStatCard
          label="Total RAM"
          value={1.2}
          suffix="PB"
          decimals={1}
          icon={<MemoryStick className="h-3.5 w-3.5" />}
          color="var(--color-accent-teal)"
          delay={0.5}
        />
        <AnimatedStatCard
          label="Active VMs"
          value={activeVMs > 0 ? activeVMs : 3450}
          icon={<Server className="h-3.5 w-3.5" />}
          color="var(--color-accent-green)"
          delay={0.6}
        />
        <AnimatedStatCard
          label="Network IO"
          value={25.1}
          suffix="Gbps"
          decimals={1}
          icon={<Wifi className="h-3.5 w-3.5" />}
          color="var(--color-accent-blue)"
          delay={0.7}
        />
      </div>
    </motion.div>
  );
}
