import { useState, useEffect, useRef } from "react";
import { motion } from "motion/react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { MoreHorizontal } from "lucide-react";

interface DataPoint {
  time: string;
  value: number;
}

function generateData(count: number, base: number, variance: number): DataPoint[] {
  const data: DataPoint[] = [];
  for (let i = 0; i < count; i++) {
    data.push({
      time: `${i * 50}ms`,
      value: base + (Math.random() - 0.5) * variance,
    });
  }
  return data;
}

function ChartPanel({
  title,
  color,
  gradientId,
  baseValue,
  variance,
  delay,
  unit = "%",
}: {
  title: string;
  color: string;
  gradientId: string;
  baseValue: number;
  variance: number;
  delay: number;
  unit?: string;
}) {
  const [data, setData] = useState<DataPoint[]>(() =>
    generateData(30, baseValue, variance)
  );
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setData((prev) => {
        const newData = [...prev.slice(1)];
        const last = prev[prev.length - 1]?.value ?? baseValue;
        const next = Math.max(
          5,
          Math.min(98, last + (Math.random() - 0.48) * variance * 0.3)
        );
        const ms = parseInt(prev[prev.length - 1]?.time ?? "0") + 50;
        newData.push({ time: `${ms}ms`, value: next });
        return newData;
      });
    }, 1500);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [baseValue, variance]);

  const current = data[data.length - 1]?.value ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-2"
    >
      <div className="flex items-center justify-between">
        <span className="text-sm text-secondary font-medium">{title}</span>
        <span className="text-sm font-mono font-bold" style={{ color }}>
          {current.toFixed(1)}{unit}
        </span>
      </div>
      <div className="h-[120px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={color} stopOpacity={0.3} />
                <stop offset="50%" stopColor={color} stopOpacity={0.1} />
                <stop offset="100%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="time"
              tick={{ fontSize: 9, fill: "var(--color-muted)" }}
              axisLine={false}
              tickLine={false}
              interval={5}
            />
            <YAxis hide domain={[0, 100]} />
            <Tooltip
              contentStyle={{
                background: "var(--color-elevated)",
                border: "1px solid var(--color-border-subtle)",
                borderRadius: "var(--radius-sm)",
                fontSize: "11px",
                color: "var(--color-primary)",
                fontFamily: "var(--font-mono)",
              }}
              formatter={(val: number) => [`${val.toFixed(1)}${unit}`, title]}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={1.5}
              fill={`url(#${gradientId})`}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </motion.div>
  );
}

export default function AdminLiveCharts() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden h-full group"
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
        <div
          className="absolute top-0 -left-6 -right-6 h-[1px] opacity-40"
          style={{
            background: "linear-gradient(90deg, transparent, rgba(59,130,246,0.8), transparent)",
          }}
        />

        <div className="flex items-center justify-between mb-6">
          <h2
            className="text-base font-bold uppercase tracking-[0.15em] text-primary"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Cluster Resources
          </h2>
        <button className="p-1 rounded-[var(--radius-sm)] text-muted hover:text-primary hover:bg-elevated transition-colors cursor-pointer">
          <MoreHorizontal className="h-4 w-4" />
        </button>
        </div>

        <div className="space-y-6 pt-2">
          <ChartPanel
            title="CPU Utilization"
            color="#3B82F6"
            gradientId="admin-cpu"
            baseValue={38}
            variance={25}
            delay={0.3}
          />
          <ChartPanel
            title="Memory Utilization"
            color="#0AEFFF"
            gradientId="admin-mem"
            baseValue={55}
            variance={18}
            delay={0.4}
          />
          <ChartPanel
            title="Storage I/O"
            color="#F59E0B"
            gradientId="admin-io"
            baseValue={22}
            variance={35}
            delay={0.5}
            unit=" MB/s"
          />
        </div>
      </div>
    </motion.div>
  );
}
