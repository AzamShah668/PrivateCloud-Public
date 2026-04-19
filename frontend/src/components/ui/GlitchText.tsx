import { useState } from "react";
import { clsx } from "clsx";

interface GlitchTextProps extends React.HTMLAttributes<HTMLSpanElement> {
  text: string;
}

export default function GlitchText({ text, className, ...props }: GlitchTextProps) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <span 
      className={clsx("glitch-wrapper", className)}
      onMouseEnter={(e) => {
        setIsHovered(true);
        props.onMouseEnter?.(e);
      }}
      onMouseLeave={(e) => {
        setIsHovered(false);
        props.onMouseLeave?.(e);
      }}
      {...props}
    >
      <span 
        className={clsx(
          "relative inline-block text-gradient-cyber transition-all duration-300",
          isHovered ? "glitch-text" : ""
        )}
        data-text={text}
      >
        {text}
      </span>
    </span>
  );
}
