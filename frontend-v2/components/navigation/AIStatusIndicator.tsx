"use client";

import { motion } from "framer-motion";

/**
 * Live AI system status indicator — a breathing orb with label.
 * Displays at the right edge of the floating nav capsule.
 */
export function AIStatusIndicator() {
  return (
    <div className="flex items-center gap-2 pl-3 ml-1 border-l border-white/[0.06]">
      {/* Orb container */}
      <div className="relative flex items-center justify-center">
        {/* Outer glow ring */}
        <motion.div
          className="absolute inset-0 rounded-full"
          style={{
            background:
              "radial-gradient(circle, rgba(52,211,153,0.3) 0%, transparent 70%)",
          }}
          animate={{
            scale: [1, 1.8, 1],
            opacity: [0.4, 0.1, 0.4],
          }}
          transition={{
            duration: 3,
            ease: "easeInOut",
            repeat: Infinity,
          }}
        />

        {/* Core orb */}
        <motion.div
          className="relative h-2 w-2 rounded-full bg-emerald-400"
          animate={{
            scale: [1, 1.15, 1],
            boxShadow: [
              "0 0 4px 1px rgba(52,211,153,0.3)",
              "0 0 10px 3px rgba(52,211,153,0.5)",
              "0 0 4px 1px rgba(52,211,153,0.3)",
            ],
          }}
          transition={{
            duration: 3,
            ease: "easeInOut",
            repeat: Infinity,
          }}
        />
      </div>

      {/* Label */}
      <div className="hidden lg:flex flex-col">
        <span className="text-[9px] font-semibold uppercase tracking-[0.12em] text-emerald-400/80 leading-none">
          AI Active
        </span>
      </div>
    </div>
  );
}
