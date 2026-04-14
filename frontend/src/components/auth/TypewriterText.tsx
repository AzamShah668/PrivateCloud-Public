import { useState, useEffect, type CSSProperties } from "react";
import { cn } from "@/lib/cn";

interface TypewriterTextProps {
  text: string;
  delay?: number;
  speed?: number;
  className?: string;
  style?: CSSProperties;
}

export default function TypewriterText({
  text,
  delay = 0,
  speed = 60,
  className,
  style,
}: TypewriterTextProps) {
  const [displayed, setDisplayed] = useState("");
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const timeout = setTimeout(() => setStarted(true), delay * 1000);
    return () => clearTimeout(timeout);
  }, [delay]);

  useEffect(() => {
    if (!started) return;

    let i = 0;
    const interval = setInterval(() => {
      i++;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(interval);
    }, speed);

    return () => clearInterval(interval);
  }, [started, text, speed]);

  return (
    <span className={cn(className)} style={style}>
      {displayed}
      {started && displayed.length < text.length && (
        <span className="animate-pulse text-accent-blue">|</span>
      )}
    </span>
  );
}
