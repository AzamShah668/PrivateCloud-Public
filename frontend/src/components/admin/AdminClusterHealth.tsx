import { motion } from "motion/react";
import { useState, useEffect } from "react";
import GlitchText from "@/components/ui/GlitchText";

const CSS_ANIMATIONS = `
@keyframes radar-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
@keyframes radar-spin-reverse {
  from { transform: rotate(0deg); }
  to { transform: rotate(-360deg); }
}
@keyframes dash-flow {
  from { stroke-dashoffset: 100; }
  to { stroke-dashoffset: 0; }
}
`;

interface ClusterHealthProps {
  totalVMs: number;
  activeVMs: number;
  totalUsers: number;
}

const NODES = [
  { id: "core", x: 250, y: 150, r: 28, label: "Core Router", metric: "99.99% UP", type: "primary" as const },
  { id: "n1", x: 90, y: 60, r: 18, label: "Compute Alpha", metric: "CPU 42%", type: "compute" as const },
  { id: "n2", x: 410, y: 60, r: 18, label: "Compute Beta", metric: "CPU 68%", type: "compute" as const },
  { id: "n3", x: 60, y: 220, r: 16, label: "SAN Storage", metric: "45/100 TB", type: "storage" as const },
  { id: "n4", x: 440, y: 220, r: 16, label: "Tape Backup", metric: "Active", type: "storage" as const },
  { id: "n5", x: 170, y: 270, r: 14, label: "Net GW-1", metric: "1.2 Gbps", type: "network" as const },
  { id: "n6", x: 330, y: 270, r: 14, label: "DNS Root", metric: "12ms ping", type: "network" as const },
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

function DataPacket({ x1, y1, x2, y2, delay, color }: { x1: number; y1: number; x2: number; y2: number; delay: number; color: string }) {
  return (
    <motion.circle
      r="3"
      cx="0" cy="0"
      fill={color}
      initial={{ x: x1, y: y1, opacity: 0 }}
      animate={{
        x: [x1, x2],
        y: [y1, y2],
        opacity: [0, 1, 1, 0],
      }}
      transition={{
        duration: 1.8 + Math.random() * 1.5,
        delay,
        repeat: Infinity,
        repeatDelay: 1 + Math.random() * 3,
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
      {/* ── Box CSS Grid Background ─────────────────────── */}
      <div 
        className="absolute inset-0 pointer-events-none z-0 opacity-30 transition-opacity duration-700 group-hover:opacity-50" 
        style={{
          backgroundImage: `linear-gradient(rgba(10,239,255,0.1) 1px, transparent 1px), linear-gradient(90deg, rgba(10,239,255,0.1) 1px, transparent 1px)`,
          backgroundSize: '24px 24px',
          backgroundPosition: 'center center'
        }} 
      />
      {/* Radial vignette to fade edges */}
      <div className="absolute inset-0 pointer-events-none z-0" style={{ background: 'radial-gradient(circle at center, transparent 30%, var(--color-deepest) 90%)' }} />
      <div className="absolute inset-0 bg-deepest/70 z-0 pointer-events-none" />
      <style>{CSS_ANIMATIONS}</style>

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
          <GlitchText
            text="Cluster Health"
            className="text-base font-bold uppercase tracking-[0.15em] text-primary"
          />
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
          <svg viewBox="0 0 500 340" className="w-full h-auto" style={{ maxHeight: 380 }}>
          {/* Connection lines */}
          {CONNECTIONS.map(([from, to], i) => {
            const a = nodeMap[from as string];
            const b = nodeMap[to as string];
            if (!a || !b) return null;
            return (
              <g key={`conn-${i}`}>
                <line
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  stroke="rgba(10,239,255,0.2)"
                  strokeWidth="1.5"
                  strokeDasharray="6 4"
                  style={{ animation: 'dash-flow 5s linear infinite' }}
                />
                {/* Multiple data packets for more activity */}
                <DataPacket
                  x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                  delay={i * 0.5}
                  color={NODE_COLORS[b.type].fill}
                />
                {(i % 2 === 0) && (
                  <DataPacket
                    x1={b.x} y1={b.y} x2={a.x} y2={a.y}
                    delay={i * 0.7 + 1.2}
                    color={NODE_COLORS[a.type].fill}
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
                  y={node.y + node.r + 16}
                  textAnchor="middle"
                  fill="var(--color-secondary)"
                  fontSize="12"
                  fontWeight="600"
                  fontFamily="var(--font-display)"
                  className="tracking-wider"
                >
                  {node.label}
                </text>
                {/* Metric */}
                <text
                  x={node.x}
                  y={node.y + node.r + 28}
                  textAnchor="middle"
                  fill={colors.fill}
                  fontSize="9"
                  fontWeight="bold"
                  fontFamily="var(--font-mono)"
                  className="opacity-80"
                >
                  [{node.metric}]
                </text>
              </g>
            );
          })}

          {/* Radar sweep on core */}
          <circle
            cx={250} cy={150} r={45}
            fill="none"
            stroke="#0AEFFF"
            strokeWidth="0.5"
            strokeDasharray="4 4"
            opacity="0.3"
            style={{ transformOrigin: "250px 150px", animation: "radar-spin 15s linear infinite" }}
          />
          <circle
            cx={250} cy={150} r={75}
            fill="none"
            stroke="#F59E0B"
            strokeWidth="0.5"
            strokeDasharray="10 10"
            opacity="0.2"
            style={{ transformOrigin: "250px 150px", animation: "radar-spin-reverse 25s linear infinite" }}
          />
          <circle
            cx={250} cy={150} r={105}
            fill="none"
            stroke="rgba(10,239,255,0.05)"
            strokeWidth="1"
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
