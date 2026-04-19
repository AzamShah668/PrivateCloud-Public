import { useEffect, useRef } from "react";
import { Cpu, MemoryStick, HardDrive } from "lucide-react";
import { motion, animate } from "motion/react";

interface ResourceSlidersProps {
  cpuCores: number;
  ramMb: number;
  storageGb: number;
  onCpuChange: (v: number) => void;
  onRamChange: (v: number) => void;
  onStorageChange: (v: number) => void;
}

function AnimatedCounter({ value, format }: { value: number, format: (val: number) => string }) {
  const nodeRef = useRef<HTMLSpanElement>(null);
  
  useEffect(() => {
    const node = nodeRef.current;
    if (!node) return;
    
    // We get the current value from the node text if possible to animate from it
    // But for simplicity, we can just animate directly to the new value on change
    const controls = animate(value, value, {
      duration: 0,
      onUpdate(v) {
        if (nodeRef.current) {
          nodeRef.current.textContent = format(v);
        }
      }
    });
    
    // When value prop changes, animate to it
    const newControls = animate(parseInt(node.dataset.val || "0") || value, value, {
      duration: 0.4,
      ease: "easeOut",
      onUpdate(v) {
        if (nodeRef.current) {
          nodeRef.current.textContent = format(v);
        }
      }
    });
    
    node.dataset.val = value.toString();
    
    return () => {
      controls.stop();
      newControls.stop();
    };
  }, [value, format]);
  
  return <span ref={nodeRef} className="tabular-nums">{format(value)}</span>;
}

function SliderRow({
  icon,
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  const pct = ((value - min) / (max - min)) * 100;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-secondary flex items-center gap-2">
          <div className="p-2 rounded-lg bg-accent-blue/10 border border-accent-blue/20 text-accent-blue shadow-[0_0_10px_rgba(10,239,255,0.2)]">
            {icon}
          </div>
          {label}
        </span>
        <span className="text-lg font-mono font-bold text-transparent bg-clip-text bg-gradient-to-r from-accent-cyan to-accent-blue drop-shadow-[0_0_8px_rgba(10,239,255,0.8)]">
          <AnimatedCounter value={value} format={(v) => {
            const val = Math.round(v);
            if (label === "RAM") return val >= 1024 ? `${(val / 1024).toFixed(val % 1024 === 0 ? 0 : 1)} GB` : `${val} MB`;
            if (label === "Storage") return `${val} GB`;
            return `${val} vCPU${val > 1 ? "s" : ""}`;
          }} />
        </span>
      </div>
      <div className="relative h-6 flex items-center">
        <div className="absolute inset-x-0 h-2 rounded-full bg-surface border border-border-subtle/50 shadow-inner" />
        <motion.div
          className="absolute left-0 h-2 rounded-full bg-gradient-to-r from-accent-blue/80 to-accent-cyan shadow-[0_0_15px_rgba(10,239,255,0.5)]"
          style={{ width: `${pct}%` }}
          layout
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="relative w-full h-6 appearance-none bg-transparent cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:bg-white
            [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-accent-cyan
            [&::-webkit-slider-thumb]:shadow-[0_0_10px_var(--color-accent-cyan)]
            [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:duration-150
            [&::-webkit-slider-thumb]:hover:scale-125
            [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4
            [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0
            [&::-moz-range-thumb]:bg-accent-blue"
        />
      </div>
      <div className="flex justify-between text-xs text-muted">
        <span>{min}{label.includes("RAM") ? " MB" : label.includes("CPU") ? "" : " GB"}</span>
        <span>{max}{label.includes("RAM") ? " MB" : label.includes("CPU") ? "" : " GB"}</span>
      </div>
    </div>
  );
}

export default function ResourceSliders({
  cpuCores,
  ramMb,
  storageGb,
  onCpuChange,
  onRamChange,
  onStorageChange,
}: ResourceSlidersProps) {
  return (
    <div className="space-y-8 p-6 rounded-2xl border border-border-subtle/30 bg-surface/30 backdrop-blur-md">
      <label className="block text-sm font-medium text-accent-cyan uppercase tracking-widest mb-2 opacity-80">
        Compute Resources
      </label>
      <SliderRow
        icon={<Cpu className="h-4 w-4" />}
        label="CPU Cores"
        value={cpuCores}
        min={1}
        max={16}
        step={1}
        onChange={onCpuChange}
      />
      <SliderRow
        icon={<MemoryStick className="h-4 w-4" />}
        label="RAM"
        value={ramMb}
        min={512}
        max={65536}
        step={512}
        onChange={onRamChange}
      />
      <SliderRow
        icon={<HardDrive className="h-4 w-4" />}
        label="Storage"
        value={storageGb}
        min={10}
        max={500}
        step={10}
        onChange={onStorageChange}
      />
    </div>
  );
}
