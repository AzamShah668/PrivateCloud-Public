/**
 * BackgroundEffects — Subtle animated background layer
 * Renders floating particles, gradient orbs, and cloud shapes
 * behind all dashboard content. All elements are pointer-events: none.
 */

export default function BackgroundEffects() {
  return (
    <div className="fixed inset-0 overflow-hidden pointer-events-none z-0 bg-deepest">
      {/* ── CSS Base Background ── */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-[0.03] mix-blend-screen" />
        {/* Dark gradient fade-out at the top to protect header text */}
        <div className="absolute inset-0 bg-gradient-to-b from-deepest via-deepest/50 to-transparent opacity-80" />
        {/* Subtle radial fade at edges */}
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_0%,var(--color-deepest)_120%)] opacity-80" />
      </div>
      {/* ── Gradient Orbs ─────────────────────────────── */}
      <div
        className="bg-orb"
        style={{
          width: 400,
          height: 400,
          top: "10%",
          left: "5%",
          background: "radial-gradient(circle, rgba(10,239,255,0.04) 0%, transparent 70%)",
          animation: "orb-float-1 25s ease-in-out infinite",
        }}
      />
      <div
        className="bg-orb"
        style={{
          width: 350,
          height: 350,
          top: "50%",
          right: "8%",
          background: "radial-gradient(circle, rgba(59,130,246,0.035) 0%, transparent 70%)",
          animation: "orb-float-2 30s ease-in-out infinite",
        }}
      />
      <div
        className="bg-orb"
        style={{
          width: 300,
          height: 300,
          bottom: "15%",
          left: "30%",
          background: "radial-gradient(circle, rgba(20,184,166,0.025) 0%, transparent 70%)",
          animation: "orb-float-3 35s ease-in-out infinite",
        }}
      />

      {/* ── Floating Particles ────────────────────────── */}
      {Array.from({ length: 18 }).map((_, i) => {
        const size = 2 + Math.random() * 3;
        const left = `${5 + (i * 5.2) % 90}%`;
        const top = `${60 + Math.random() * 40}%`;
        const anim = `particle-drift-${(i % 3) + 1}`;
        const dur = 12 + Math.random() * 18;
        const delay = i * 1.8;
        return (
          <div
            key={`p-${i}`}
            className="bg-particle"
            style={{
              width: size,
              height: size,
              left,
              top,
              animation: `${anim} ${dur}s ease-in-out ${delay}s infinite`,
            }}
          />
        );
      })}

      {/* ── Scan Line ─────────────────────────────────── */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          height: "1px",
          background: "linear-gradient(90deg, transparent, rgba(10,239,255,0.06), transparent)",
          animation: "line-sweep 12s linear infinite",
        }}
      />

      {/* ── Cloud Shapes (very subtle SVGs) ───────────── */}
      <svg
        className="bg-cloud"
        style={{
          width: 500,
          height: 200,
          top: "12%",
          right: "5%",
          animation: "cloud-drift-1 40s ease-in-out infinite",
        }}
        viewBox="0 0 500 200"
        fill="none"
      >
        <path
          d="M70 140c0-33 27-60 60-60 5 0 10 1 15 2C155 55 180 35 210 35c40 0 72 30 75 68 2-1 4-1 6-1 28 0 50 22 50 50s-22 50-50 50H130c-33 0-60-27-60-62z"
          fill="rgba(10,239,255,0.015)"
          stroke="rgba(10,239,255,0.02)"
          strokeWidth="0.5"
        />
      </svg>
      <svg
        className="bg-cloud"
        style={{
          width: 400,
          height: 160,
          bottom: "20%",
          left: "2%",
          animation: "cloud-drift-2 50s ease-in-out infinite",
        }}
        viewBox="0 0 400 160"
        fill="none"
      >
        <path
          d="M50 110c0-28 22-50 49-50 4 0 8 0 12 1C118 38 142 20 170 20c35 0 62 26 65 59h5c24 0 43 19 43 43s-19 43-43 43H99c-27 0-49-22-49-55z"
          fill="rgba(59,130,246,0.012)"
          stroke="rgba(59,130,246,0.018)"
          strokeWidth="0.5"
        />
      </svg>
      <svg
        className="bg-cloud"
        style={{
          width: 350,
          height: 140,
          top: "55%",
          right: "20%",
          animation: "cloud-drift-3 45s ease-in-out infinite",
        }}
        viewBox="0 0 350 140"
        fill="none"
      >
        <path
          d="M40 95c0-24 19-43 43-43 3 0 7 0 10 1C99 32 120 16 145 16c30 0 54 22 57 51h4c21 0 37 16 37 37s-16 37-37 37H83c-24 0-43-19-43-46z"
          fill="rgba(10,239,255,0.01)"
          stroke="rgba(10,239,255,0.015)"
          strokeWidth="0.5"
        />
      </svg>
    </div>
  );
}
