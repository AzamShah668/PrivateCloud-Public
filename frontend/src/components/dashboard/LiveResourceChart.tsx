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

function generateInitialData(count: number, baseValue: number, variance: number): DataPoint[] {
  const data: DataPoint[] = [];
  for (let i = 0; i < count; i++) {
    const ms = i * 50;
    data.push({
      time: `${ms}ms`,
      value: baseValue + (Math.random() - 0.5) * variance,
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
}: {
  title: string;
  color: string;
  gradientId: string;
  baseValue: number;
  variance: number;
  delay: number;
}) {
  const [data, setData] = useState<DataPoint[]>(() =>
    generateInitialData(30, baseValue, variance)
  );
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setData((prev) => {
        const newData = [...prev.slice(1)];
        const lastVal = prev[prev.length - 1]?.value ?? baseValue;
        const newVal = Math.max(
          10,
          Math.min(95, lastVal + (Math.random() - 0.48) * variance * 0.3)
        );
        const ms = parseInt(prev[prev.length - 1]?.time ?? "0") + 50;
        newData.push({ time: `${ms}ms`, value: newVal });
        return newData;
      });
    }, 1500);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [baseValue, variance]);

  const currentValue = data[data.length - 1]?.value ?? 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="space-y-2"
    >
      <div className="flex items-center justify-between">
        <span className="text-xs text-secondary font-medium">{title}</span>
        <span className="text-xs font-mono font-semibold" style={{ color }}>
          {currentValue.toFixed(1)}%
        </span>
      </div>
      <div className="h-[100px]">
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
              formatter={(val: number) => [`${val.toFixed(1)}%`, title]}
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

export default function LiveResourceChart() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2
          className="text-xs font-bold uppercase tracking-[0.15em] text-primary"
          style={{ fontFamily: "var(--font-display)" }}
        >
          Live Resource Metrics
        </h2>
        <button className="p-1 rounded-[var(--radius-sm)] text-muted hover:text-primary hover:bg-elevated transition-colors cursor-pointer">
          <MoreHorizontal className="h-4 w-4" />
        </button>
      </div>

      {/* Charts */}
      <div className="space-y-5">
        <ChartPanel
          title="CPU utilization"
          color="#3B82F6"
          gradientId="cpuGrad"
          baseValue={45}
          variance={30}
          delay={0.3}
        />
        <ChartPanel
          title="Memory utilization"
          color="#0AEFFF"
          gradientId="memGrad"
          baseValue={62}
          variance={20}
          delay={0.4}
        />
      </div>
    </motion.div>
  );
}
