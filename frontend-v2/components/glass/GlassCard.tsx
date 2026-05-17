"use client";

import { cn } from "@/lib/utils";
import { motion, type HTMLMotionProps } from "framer-motion";

interface GlassCardProps extends HTMLMotionProps<"div"> {
  active?: boolean;
  children: React.ReactNode;
}

export function GlassCard({ active = false, children, className, ...props }: GlassCardProps) {
  return (
    <motion.div
      whileHover={{ y: -2, scale: 1.005 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className={cn("glass-card", active && "glass-card-active", className)}
      {...props}
    >
      {children}
    </motion.div>
  );
}
