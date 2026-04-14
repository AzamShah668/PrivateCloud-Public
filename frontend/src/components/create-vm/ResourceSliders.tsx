import { Cpu, MemoryStick, HardDrive } from "lucide-react";

interface ResourceSlidersProps {
  cpuCores: number;
  ramMb: number;
  storageGb: number;
  onCpuChange: (v: number) => void;
  onRamChange: (v: number) => void;
  onStorageChange: (v: number) => void;
}

function SliderRow({
  icon,
  label,
  value,
  displayValue,
  min,
  max,
  step,
  onChange,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  displayValue: string;
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
          {icon}
          {label}
        </span>
        <span className="text-sm font-mono font-semibold text-accent-blue tabular-nums">
          {displayValue}
        </span>
      </div>
      <div className="relative h-8 flex items-center">
        <div className="absolute inset-x-0 h-1.5 rounded-full bg-elevated" />
        <div
          className="absolute left-0 h-1.5 rounded-full bg-accent-blue transition-all duration-150"
          style={{ width: `${pct}%` }}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="relative w-full h-8 appearance-none bg-transparent cursor-pointer
            [&::-webkit-slider-thumb]:appearance-none
            [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4
            [&::-webkit-slider-thumb]:rounded-full
            [&::-webkit-slider-thumb]:bg-accent-blue
            [&::-webkit-slider-thumb]:border-2 [&::-webkit-slider-thumb]:border-surface
            [&::-webkit-slider-thumb]:shadow-[0_0_8px_var(--color-accent-blue)]
            [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:duration-150
            [&::-webkit-slider-thumb]:hover:scale-125
            [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4
            [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:border-0
            [&::-moz-range-thumb]:bg-accent-blue"
        />
      </div>
      <div className="flex justify-between text-[10px] text-muted">
        <span>{min}{label.includes("RAM") ? " MB" : label.includes("CPU") ? "" : " GB"}</span>
        <span>{max}{label.includes("RAM") ? " MB" : label.includes("CPU") ? "" : " GB"}</span>
      </div>
    </div>
  );
}

function formatRam(mb: number): string {
  return mb >= 1024 ? `${(mb / 1024).toFixed(mb % 1024 === 0 ? 0 : 1)} GB` : `${mb} MB`;
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
    <div className="space-y-6">
      <label className="block text-sm font-medium text-secondary">
        Resources
      </label>
      <SliderRow
        icon={<Cpu className="h-4 w-4" />}
        label="CPU Cores"
        value={cpuCores}
        displayValue={`${cpuCores} vCPU${cpuCores > 1 ? "s" : ""}`}
        min={1}
        max={16}
        step={1}
        onChange={onCpuChange}
      />
      <SliderRow
        icon={<MemoryStick className="h-4 w-4" />}
        label="RAM"
        value={ramMb}
        displayValue={formatRam(ramMb)}
        min={512}
        max={65536}
        step={512}
        onChange={onRamChange}
      />
      <SliderRow
        icon={<HardDrive className="h-4 w-4" />}
        label="Storage"
        value={storageGb}
        displayValue={`${storageGb} GB`}
        min={10}
        max={500}
        step={10}
        onChange={onStorageChange}
      />
    </div>
  );
}
