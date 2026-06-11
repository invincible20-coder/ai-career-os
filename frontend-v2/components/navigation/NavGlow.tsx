"use client";

import { useRef } from "react";
import { motion, useMotionValue, useTransform, useSpring } from "framer-motion";

/**
 * Cursor-reactive ambient glow layer rendered inside the floating nav.
 * A radial gradient follows the mouse X position across the navbar
 * for an intelligent lighting effect.
 */
export function NavGlow() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mouseX = useMotionValue(0.5); // normalized 0–1

  const smoothX = useSpring(mouseX, { stiffness: 150, damping: 20 });

  // Map normalized X to percentage for gradient position
  const gradientX = useTransform(smoothX, [0, 1], ["0%", "100%"]);

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const normalized = (e.clientX - rect.left) / rect.width;
    mouseX.set(Math.max(0, Math.min(1, normalized)));
  };

  return (
    <motion.div
      ref={containerRef}
      onMouseMove={handleMouseMove}
      className="absolute inset-0 overflow-hidden rounded-[inherit] pointer-events-none"
      aria-hidden
    >
      {/* Cursor-following glow */}
      <motion.div
        className="absolute top-0 h-full w-[200px]"
        style={{
          left: gradientX,
          transform: "translateX(-50%)",
          background:
            "radial-gradient(ellipse at center, rgba(20,184,166,0.10) 0%, rgba(34,211,238,0.05) 40%, transparent 70%)",
          filter: "blur(8px)",
        }}
      />

      {/* Top edge reflection */}
      <div
        className="absolute inset-x-0 top-0 h-[1px]"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.1) 20%, rgba(255,255,255,0.15) 50%, rgba(255,255,255,0.1) 80%, transparent 100%)",
        }}
      />

      {/* Subtle inner grain for depth */}
      <div
        className="absolute inset-0 opacity-[0.015]"
        style={{
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E")`,
          backgroundSize: "128px 128px",
        }}
      />

      {/* Bottom edge subtle shadow */}
      <div
        className="absolute inset-x-0 bottom-0 h-[1px]"
        style={{
          background:
            "linear-gradient(90deg, transparent 15%, rgba(255,255,255,0.04) 50%, transparent 85%)",
        }}
      />
    </motion.div>
  );
}
