import { motion } from "motion/react";
import { MoreHorizontal, Database, Loader2 } from "lucide-react";

// Simplified world map outline as SVG path
const WORLD_MAP_PATH =
  "M60,45 Q65,40 75,42 L85,38 Q90,35 95,38 L105,35 Q110,32 118,35 L125,32 Q130,30 138,33 L145,30 Q152,28 160,32 L168,35 Q175,38 178,42 L182,38 Q188,35 195,38 L202,42 Q208,45 215,42 L222,45 Q228,48 235,45 L242,42 Q248,38 255,40 L262,42 Q268,45 275,42 Q278,40 282,42 L288,45 Q292,48 298,45 L305,42 Q310,38 318,40 L325,45 M65,52 Q70,55 78,52 L85,55 Q90,58 98,55 L105,58 Q110,62 118,60 L125,65 Q130,68 138,65 L145,62 Q150,58 158,60 L165,65 Q172,70 180,68 L188,72 Q195,75 202,72 M210,58 Q218,55 225,58 L232,62 Q238,65 245,62 L252,65 Q258,68 265,65 L275,68 Q282,72 290,68 L298,65 Q305,62 312,65 M80,78 Q88,75 95,78 L105,82 Q112,85 120,82 L128,78 M140,80 Q148,78 155,82 L165,85 Q172,88 180,85 M230,75 Q238,72 245,75 L252,78 Q258,82 265,78 L272,75";

function AlertItem({
  icon,
  label,
  delay,
}: {
  icon: React.ReactNode;
  label: string;
  delay: number;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
      className="flex items-center justify-between py-2 px-3 rounded-[var(--radius-sm)] hover:bg-elevated/30 transition-colors group"
    >
      <div className="flex items-center gap-2.5">
        {icon}
        <span className="text-xs text-secondary group-hover:text-primary transition-colors">
          {label}
        </span>
      </div>
      <button className="p-0.5 text-muted hover:text-primary transition-colors opacity-0 group-hover:opacity-100 cursor-pointer">
        <MoreHorizontal className="h-3.5 w-3.5" />
      </button>
    </motion.div>
  );
}

export default function SystemAlerts() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      className="glass-panel rounded-[var(--radius-lg)] p-6 relative overflow-hidden"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2
          className="text-xs font-bold uppercase tracking-[0.15em] text-primary"
          style={{ fontFamily: "var(--font-display)" }}
        >
          System Alerts
        </h2>
      </div>

      {/* World map */}
      <div className="relative h-[120px] mb-4 overflow-hidden rounded-[var(--radius-md)]">
        <div
          className="absolute inset-0"
          style={{
            background: "radial-gradient(ellipse at center, rgba(10,22,40,0.8) 0%, rgba(6,11,20,1) 100%)",
          }}
        />
        <svg
          viewBox="40 20 290 80"
          className="absolute inset-0 w-full h-full"
          preserveAspectRatio="xMidYMid meet"
        >
          {/* World map outline */}
          <path
            d={WORLD_MAP_PATH}
            fill="none"
            stroke="rgba(10,239,255,0.12)"
            strokeWidth="0.8"
          />

          {/* Data center dots with pulse */}
          {[
            { cx: 95, cy: 48, label: "US-East" },
            { cx: 135, cy: 42, label: "EU-West" },
            { cx: 205, cy: 55, label: "Asia-SE" },
            { cx: 260, cy: 65, label: "Oceania" },
            { cx: 160, cy: 70, label: "Africa" },
          ].map((dc, i) => (
            <g key={dc.label}>
              {/* Pulse ring */}
              <circle cx={dc.cx} cy={dc.cy} r="2" fill="none" stroke="rgba(255,107,53,0.4)">
                <animate
                  attributeName="r"
                  values="2;8;2"
                  dur="3s"
                  begin={`${i * 0.6}s`}
                  repeatCount="indefinite"
                />
                <animate
                  attributeName="opacity"
                  values="0.6;0;0.6"
                  dur="3s"
                  begin={`${i * 0.6}s`}
                  repeatCount="indefinite"
                />
              </circle>
              {/* Core dot */}
              <circle
                cx={dc.cx}
                cy={dc.cy}
                r="2.5"
                fill="#FF6B35"
              />
              <circle
                cx={dc.cx}
                cy={dc.cy}
                r="1"
                fill="#FFD700"
              />
            </g>
          ))}

          {/* Connection lines between data centers */}
          {[
            { x1: 95, y1: 48, x2: 135, y2: 42 },
            { x1: 135, y1: 42, x2: 205, y2: 55 },
            { x1: 205, y1: 55, x2: 260, y2: 65 },
          ].map((line, i) => (
            <line
              key={`dc-line-${i}`}
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke="rgba(255,107,53,0.15)"
              strokeWidth="0.5"
              strokeDasharray="4,3"
            >
              <animate
                attributeName="stroke-dashoffset"
                values="7;0"
                dur="2s"
                repeatCount="indefinite"
              />
            </line>
          ))}
        </svg>
      </div>

      {/* Alert items */}
      <div className="space-y-1">
        <AlertItem
          icon={
            <div className="flex items-center justify-center h-6 w-6 rounded bg-accent-blue/10 border border-accent-blue/20">
              <Database className="h-3 w-3 text-accent-blue" />
            </div>
          }
          label="data center"
          delay={0.5}
        />
        <AlertItem
          icon={
            <div className="flex items-center justify-center h-6 w-6 rounded bg-accent-amber/10 border border-accent-amber/20">
              <Loader2 className="h-3 w-3 text-accent-amber animate-spin" />
            </div>
          }
          label="loading"
          delay={0.6}
        />
      </div>
    </motion.div>
  );
}
