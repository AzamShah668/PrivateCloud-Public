import { useRef, useEffect, useState } from "react";

export default function TerrainBackground() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handleCanPlay = () => setIsLoaded(true);
    video.addEventListener("canplaythrough", handleCanPlay);

    // Ensure playback starts even if autoplay is delayed
    video.play().catch(() => {
      // Autoplay blocked — still show the video frame
    });

    return () => video.removeEventListener("canplaythrough", handleCanPlay);
  }, []);

  return (
    <div className="fixed inset-0 z-0">
      {/* Video element — covers the entire viewport */}
      <video
        ref={videoRef}
        autoPlay
        loop
        muted
        playsInline
        preload="auto"
        className="absolute inset-0 w-full h-full"
        style={{
          objectFit: "cover",
          opacity: isLoaded ? 1 : 0,
          transition: "opacity 1.2s ease-out",
        }}
      >
        <source src="/auth-bg.mp4" type="video/mp4" />
      </video>

      {/* Dark base — visible while video loads */}
      <div
        className="absolute inset-0"
        style={{
          background: "#060B14",
          opacity: isLoaded ? 0 : 1,
          transition: "opacity 1.2s ease-out",
          pointerEvents: "none",
        }}
      />

      {/* Vignette — darkens edges so the glass card pops */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 65% 55% at 50% 50%, transparent 20%, rgba(6,11,20,0.55) 60%, #060B14 95%)",
        }}
      />

      {/* Top fade — keeps the top edge clean */}
      <div
        className="absolute inset-x-0 top-0 h-32 pointer-events-none"
        style={{
          background: "linear-gradient(to bottom, #060B14 0%, transparent 100%)",
        }}
      />

      {/* Bottom fade — grounds the composition */}
      <div
        className="absolute inset-x-0 bottom-0 h-40 pointer-events-none"
        style={{
          background: "linear-gradient(to top, #060B14 0%, transparent 100%)",
        }}
      />

      {/* Subtle blue tint overlay — ensures video hue matches the cyan/blue theme */}
      <div
        className="absolute inset-0 pointer-events-none mix-blend-soft-light"
        style={{
          background:
            "radial-gradient(circle at 50% 50%, rgba(10,239,255,0.08) 0%, transparent 70%)",
        }}
      />
    </div>
  );
}
