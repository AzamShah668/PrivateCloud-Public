import { motion } from "motion/react";
import { Link } from "react-router-dom";
import { PlusCircle, Cpu, HardDrive, MemoryStick, Rocket } from "lucide-react";
import Button from "@/components/ui/Button";

const presets = [
  {
    name: "Ubuntu Server",
    icon: "🐧",
    os: "ubuntu-24.04",
    specs: "2 vCPU · 4 GB · 32 GB",
    color: "#E95420",
  },
  {
    name: "Debian 12",
    icon: "🌀",
    os: "debian-12",
    specs: "2 vCPU · 2 GB · 20 GB",
    color: "#A80030",
  },
  {
    name: "CentOS Stream",
    icon: "🎯",
    os: "centos-9",
    specs: "4 vCPU · 8 GB · 50 GB",
    color: "#262577",
  },
];

export default function QuickDeploy() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden"
    >
      {/* Animated border glow */}
      <div
        className="absolute inset-0 rounded-[var(--radius-lg)] pointer-events-none animate-border-glow"
        style={{
          border: "1px solid rgba(10, 239, 255, 0.15)",
        }}
      />

      {/* Top accent line */}
      <div
        className="absolute top-0 left-6 right-6 h-[1px]"
        style={{
          background: "linear-gradient(90deg, transparent, rgba(10,239,255,0.2), transparent)",
        }}
      />

      {/* Background radial */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "radial-gradient(ellipse at bottom right, rgba(10,239,255,0.04) 0%, transparent 60%)",
        }}
      />

      {/* Header */}
      <div className="relative flex items-center justify-between mb-5">
        <div className="flex items-center gap-2.5">
          <div
            className="flex items-center justify-center h-8 w-8 rounded-[var(--radius-md)]"
            style={{
              background: "linear-gradient(135deg, rgba(10,239,255,0.12), rgba(59,130,246,0.08))",
              border: "1px solid rgba(10,239,255,0.15)",
            }}
          >
            <Rocket className="h-4 w-4 text-accent-cyan" />
          </div>
          <h2
            className="text-sm font-bold tracking-wide text-primary"
            style={{ fontFamily: "var(--font-display)" }}
          >
            Quick Deploy
          </h2>
        </div>
      </div>

      {/* Presets */}
      <div className="relative space-y-2 mb-5">
        {presets.map((preset, i) => (
          <motion.div
            key={preset.os}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{
              delay: 0.4 + i * 0.08,
              duration: 0.35,
              ease: [0.16, 1, 0.3, 1],
            }}
          >
            <Link
              to={`/vms/create?os=${preset.os}`}
              className="group flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-md)] hover:bg-elevated/40 transition-all duration-200 nav-glow"
            >
              <span className="text-lg" role="img" aria-label={preset.name}>
                {preset.icon}
              </span>
              <div className="flex-1">
                <p className="text-sm font-medium text-primary group-hover:text-accent-cyan transition-colors" style={{ fontFamily: "var(--font-body)" }}>
                  {preset.name}
                </p>
                <div className="flex items-center gap-2 text-[10px] text-muted">
                  <span className="flex items-center gap-0.5">
                    <Cpu className="h-2.5 w-2.5" />
                    <MemoryStick className="h-2.5 w-2.5" />
                    <HardDrive className="h-2.5 w-2.5" />
                  </span>
                  <span>{preset.specs}</span>
                </div>
              </div>
              <PlusCircle className="h-4 w-4 text-muted group-hover:text-accent-cyan transition-colors" />
            </Link>
          </motion.div>
        ))}
      </div>

      {/* Full CTA */}
      <Link to="/vms/create" className="block">
        <Button className="w-full">
          <PlusCircle className="h-4 w-4" />
          Custom Instance
        </Button>
      </Link>
    </motion.div>
  );
}
