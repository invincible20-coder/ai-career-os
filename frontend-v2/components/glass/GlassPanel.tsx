"use client";

import { cn } from "@/lib/utils";
import { motion, type HTMLMotionProps } from "framer-motion";

interface GlassPanelProps extends HTMLMotionProps<"div"> {
  depth?: 1 | 2 | 3;
  glow?: boolean;
  active?: boolean;
  children: React.ReactNode;
}

export function GlassPanel({
  depth = 1,
  glow = false,
  active = false,
  children,
  className,
  ...props
}: GlassPanelProps) {
  return (
    <motion.div
      className={cn(
        "rounded-2xl",
        depth === 1 && "glass-panel",
        depth === 2 && "glass-panel-elevated",
        depth === 3 && "glass-panel-elevated",
        active && "glass-card-active",
        glow && "animate-pulse-glow",
        className
      )}
      {...props}
    >
      {children}
    </motion.div>
  );
}
