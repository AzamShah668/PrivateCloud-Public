import { useState, useRef } from "react";
import { motion, useMotionTemplate, useMotionValue, useSpring, useTransform } from "motion/react";
import { OS_OPTIONS, type OSValue } from "@/lib/constants";
import { cn } from "@/lib/cn";

const osGradients: Record<string, string> = {
  ubuntu: "from-orange-500 to-orange-600",
  debian: "from-red-500 to-rose-700",
  centos: "from-purple-500 to-indigo-600",
  windows: "from-blue-400 to-blue-600",
};

interface OSSelectorProps {
  value: OSValue;
  onChange: (value: OSValue) => void;
}

function OSCard({
  os,
  selected,
  onClick,
  index,
}: {
  os: (typeof OS_OPTIONS)[number];
  selected: boolean;
  onClick: () => void;
  index: number;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  const [isHovered, setIsHovered] = useState(false);
  
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);

  const x = useMotionValue(0);
  const y = useMotionValue(0);
  const springX = useSpring(x, { stiffness: 400, damping: 30 });
  const springY = useSpring(y, { stiffness: 400, damping: 30 });
  const rotateX = useTransform(springY, [-0.5, 0.5], ["10deg", "-10deg"]);
  const rotateY = useTransform(springX, [-0.5, 0.5], ["-10deg", "10deg"]);

  function handleMouseMove({ currentTarget, clientX, clientY }: React.MouseEvent) {
    const { left, top, width, height } = currentTarget.getBoundingClientRect();
    mouseX.set(clientX - left);
    mouseY.set(clientY - top);
    x.set((clientX - left) / width - 0.5);
    y.set((clientY - top) / height - 0.5);
  }

  function handleMouseLeave() {
    setIsHovered(false);
    x.set(0);
    y.set(0);
  }

  const gradient = osGradients[os.icon] ?? "from-slate-500 to-slate-700";

  return (
    <motion.button
      ref={ref}
      type="button"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      onMouseMove={handleMouseMove}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={handleMouseLeave}
      onClick={onClick}
      style={{
        rotateX: isHovered ? rotateX : 0,
        rotateY: isHovered ? rotateY : 0,
        transformStyle: "preserve-3d",
      }}
      className={cn(
        "relative flex flex-col items-center gap-2 p-4 rounded-xl transition-all duration-300",
        "bg-surface border backdrop-blur-md overflow-hidden group",
        selected
          ? "border-accent-blue/50 shadow-[0_0_30px_-5px_rgba(10,239,255,0.3)] bg-accent-blue/[0.02]"
          : "border-border-subtle/50 hover:border-secondary/40 hover:bg-elevated/80"
      )}
    >
      {/* Spotlight Effect */}
      <motion.div
        className="pointer-events-none absolute -inset-px rounded-2xl opacity-0 transition duration-500 group-hover:opacity-100"
        style={{
          background: useMotionTemplate`
            radial-gradient(
              250px circle at ${mouseX}px ${mouseY}px,
              rgba(255, 255, 255, 0.08),
              transparent 80%
            )
          `,
        }}
      />

      {/* Floating Glowing Orb */}
      <div 
        className="relative flex items-center justify-center"
        style={{ transform: "translateZ(30px)" }}
      >
        <div className={cn(
          "absolute inset-0 blur-xl opacity-40 group-hover:opacity-80 transition-opacity duration-500 rounded-full",
          `bg-gradient-to-br ${gradient}`
        )} />
        <div className={cn(
          "w-12 h-12 rounded-full flex items-center justify-center relative z-10 shadow-inner",
          "border border-white/10",
          `bg-gradient-to-br ${gradient}`
        )}>
          {/* Subtle reflection on the orb */}
          <div className="absolute top-1 left-2 w-3 h-1.5 bg-white/30 rounded-full blur-[1px] rotate-[-45deg]" />
        </div>
      </div>

      <span 
        className={cn(
          "text-xs font-semibold tracking-wide transition-colors duration-300",
          selected ? "text-accent-blue" : "text-primary group-hover:text-white"
        )}
        style={{ transform: "translateZ(20px)" }}
      >
        {os.label}
      </span>

      {selected && (
        <motion.div
          layoutId="os-active-border"
          className="absolute inset-0 rounded-xl border-2 border-accent-blue/80 pointer-events-none"
          transition={{ type: "spring", stiffness: 300, damping: 25 }}
        />
      )}
    </motion.button>
  );
}

export default function OSSelector({ value, onChange }: OSSelectorProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-accent-cyan uppercase tracking-widest mb-6 opacity-80">
        Operating Environment
      </label>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3" style={{ perspective: "1000px" }}>
        {OS_OPTIONS.map((os, i) => (
          <OSCard
            key={os.value}
            os={os}
            selected={value === os.value}
            onClick={() => onChange(os.value as OSValue)}
            index={i}
          />
        ))}
      </div>
    </div>
  );
}
