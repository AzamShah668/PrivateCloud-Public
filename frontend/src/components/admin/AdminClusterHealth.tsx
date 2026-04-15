import { motion } from "motion/react";
import { useState, useEffect } from "react";

interface ClusterHealthProps {
  totalVMs: number;
  activeVMs: number;
  totalUsers: number;
}

const NODES = [
  { id: "core", x: 250, y: 150, r: 28, label: "Core", type: "primary" as const },
  { id: "n1", x: 100, y: 70, r: 18, label: "Node 1", type: "compute" as const },
  { id: "n2", x: 400, y: 70, r: 18, label: "Node 2", type: "compute" as const },
  { id: "n3", x: 70, y: 220, r: 16, label: "Storage", type: "storage" as const },
  { id: "n4", x: 430, y: 220, r: 16, label: "Backup", type: "storage" as const },
  { id: "n5", x: 180, y: 270, r: 14, label: "Net GW", type: "network" as const },
  { id: "n6", x: 320, y: 270, r: 14, label: "DNS", type: "network" as const },
];

const CONNECTIONS = [
  ["core", "n1"], ["core", "n2"], ["core", "n3"], ["core", "n4"],
  ["core", "n5"], ["core", "n6"], ["n1", "n3"], ["n2", "n4"],
  ["n5", "n6"],
];

const NODE_COLORS = {
  primary: { fill: "#0AEFFF", stroke: "#0AEFFF", glow: "rgba(10,239,255,0.3)" },
  compute: { fill: "#3B82F6", stroke: "#3B82F6", glow: "rgba(59,130,246,0.25)" },
  storage: { fill: "#F59E0B", stroke: "#F59E0B", glow: "rgba(245,158,11,0.25)" },
  network: { fill: "#14B8A6", stroke: "#14B8A6", glow: "rgba(20,184,166,0.25)" },
};

function DataPacket({ x1, y1, x2, y2, delay }: { x1: number; y1: number; x2: number; y2: number; delay: number }) {
  return (
    <motion.circle
      r="2.5"
      fill="#0AEFFF"
      initial={{ cx: x1, cy: y1, opacity: 0 }}
      animate={{
        cx: [x1, x2],
        cy: [y1, y2],
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration: 2.5,
        delay,
        repeat: Infinity,
        repeatDelay: 3 + Math.random() * 4,
        ease: "easeInOut",
      }}
    />
  );
}

export default function AdminClusterHealth(_props: ClusterHealthProps) {
  const [pulsePhase, setPulsePhase] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => setPulsePhase((p) => p + 1), 2000);
    return () => clearInterval(interval);
  }, []);

  const nodeMap = Object.fromEntries(NODES.map((n) => [n.id, n]));

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden group"
    >
      {/* ── Box Video Background ─────────────────────── */}
      <video
        autoPlay
        loop
        muted
        playsInline
        className="absolute inset-0 w-full h-full object-cover opacity-30 pointer-events-none z-0 mix-blend-screen transition-opacity duration-700 group-hover:opacity-50"
        src="/admin-box-bg.mp4"
      />
      <div className="absolute inset-0 bg-deepest/60 z-0 pointer-events-none" />

      {/* Main Content Layer */}
      <div className="relative z-10">
        {/* Glow accent */}
        <div
          className="absolute top-0 -left-6 -right-6 h-[1px] opacity-40"
          style={{
            background: "linear-gradient(90deg, transparent, rgba(10,239,255,0.8), transparent)",
          }}
        />

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2
            className="text-base font-bold uppercase tracking-[0.15em] text-primary"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Cluster Health
          </h2>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-[var(--radius-sm)] border border-accent-green/20 bg-accent-green/5">
          <span className="relative flex h-2 w-2">
            <span className="absolute inset-0 rounded-full bg-accent-green animate-pulse-status" />
            <span className="relative h-2 w-2 rounded-full bg-accent-green" />
          </span>
          <span className="text-[10px] font-mono font-semibold text-accent-green uppercase">
            All Systems Operational
          </span>
        </div>
        </div>

        {/* SVG Network Topology */}
        <div className="relative mt-4">
          <svg viewBox="0 0 500 310" className="w-full h-auto" style={{ maxHeight: 380 }}>
          {/* Connection lines */}
          {CONNECTIONS.map(([from, to], i) => {
            const a = nodeMap[from as string];
            const b = nodeMap[to as string];
            if (!a || !b) return null;
            return (
              <g key={`conn-${i}`}>
                <line
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke="rgba(10,239,255,0.12)"
                  strokeWidth="1"
                  strokeDasharray="4 3"
                />
                {i < 4 && (
                  <DataPacket
                    x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                    delay={i * 1.2}
                  />
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {NODES.map((node) => {
            const colors = NODE_COLORS[node.type];
            return (
              <g key={node.id}>
                {/* Outer glow */}
                <circle
                  cx={node.x} cy={node.y} r={node.r + 8}
                  fill={colors.glow}
                  opacity={0.15 + (pulsePhase % 2 === 0 ? 0.1 : 0)}
                  style={{ transition: "opacity 1s ease" }}
                />
                {/* Node circle */}
                <circle
                  cx={node.x} cy={node.y} r={node.r}
                  fill="rgba(15,29,50,0.8)"
                  stroke={colors.stroke}
                  strokeWidth="1.5"
                  opacity="0.9"
                />
                {/* Inner dot */}
                <circle
                  cx={node.x} cy={node.y} r={node.r * 0.35}
                  fill={colors.fill}
                  opacity="0.6"
                />
                {/* Label */}
                <text
                  x={node.x}
                  y={node.y + node.r + 14}
                  textAnchor="middle"
                  fill="var(--color-secondary)"
                  fontSize="12"
                  fontWeight="600"
                  fontFamily="var(--font-mono)"
                >
                  {node.label}
                </text>
              </g>
            );
          })}

          {/* Radar sweep on core */}
          <circle
            cx={250} cy={150} r={60}
            fill="none"
            stroke="rgba(10,239,255,0.06)"
            strokeWidth="1"
            strokeDasharray="4 4"
          />
          <circle
            cx={250} cy={150} r={100}
            fill="none"
            stroke="rgba(10,239,255,0.03)"
            strokeWidth="0.5"
            strokeDasharray="3 5"
          />
        </svg>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-6 mt-6 px-2 pb-2">
          {(
            [
              ["Compute", NODE_COLORS.compute.fill],
              ["Storage", NODE_COLORS.storage.fill],
              ["Network", NODE_COLORS.network.fill],
            ] as const
          ).map(([label, color]) => (
            <div key={label} className="flex items-center gap-2">
              <span
                className="h-3 w-3 rounded-full"
                style={{ background: color }}
              />
              <span className="text-xs text-muted font-mono">{label}</span>
            </div>
          ))}
        </div>
      </div>
    </motion.div>
  );
}
