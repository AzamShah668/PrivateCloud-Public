import { motion } from "motion/react";
import { Link } from "react-router-dom";
import { PlusCircle, Cpu, HardDrive, MemoryStick, Rocket } from "lucide-react";
import Button from "@/components/ui/Button";
import SpotlightCard from "@/components/ui/SpotlightCard";
import GlitchText from "@/components/ui/GlitchText";

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
    <SpotlightCard
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="p-6 relative overflow-hidden"
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
          <GlitchText
            text="Quick Deploy"
            className="text-base font-bold tracking-wide text-primary"
          />
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
              className="group flex items-center gap-4 px-4 py-3 rounded-xl border border-border-subtle/40 bg-surface/50 hover:bg-elevated/80 transition-all duration-300 overflow-hidden relative"
            >
              {/* Animated hover gradient background */}
              <div
                className="absolute inset-0 opacity-0 group-hover:opacity-10 transition-opacity duration-500 pointer-events-none"
                style={{
                  background: `linear-gradient(90deg, transparent, ${preset.color}, transparent)`,
                }}
              />
              {/* Animated hover border top */}
              <div
                className="absolute top-0 left-0 right-0 h-[1px] opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"
                style={{
                  background: `linear-gradient(90deg, transparent, ${preset.color}, transparent)`,
                }}
              />

              {/* Glowing Icon */}
              <div className="relative flex items-center justify-center">
                <div 
                  className="absolute inset-0 blur-md opacity-20 group-hover:opacity-60 transition-opacity duration-300 rounded-full"
                  style={{ backgroundColor: preset.color }}
                />
                <span className="text-xl relative z-10" role="img" aria-label={preset.name}>
                  {preset.icon}
                </span>
              </div>
              
              <div className="flex-1 relative z-10">
                <p className="text-sm font-medium text-primary group-hover:text-white transition-colors" style={{ fontFamily: "var(--font-body)" }}>
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
              <PlusCircle className="h-4 w-4 text-muted group-hover:text-accent-cyan transition-colors relative z-10" />
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
    </SpotlightCard>
  );
}
