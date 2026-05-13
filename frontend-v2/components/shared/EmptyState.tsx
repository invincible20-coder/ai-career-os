"use client";

import { motion } from "framer-motion";
import { Search, Rocket, FileText, Inbox, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

type EmptyVariant = "idle" | "scanning" | "no-results" | "no-content" | "no-tracking";

interface EmptyStateProps {
  variant: EmptyVariant;
  className?: string;
}

const VARIANTS: Record<EmptyVariant, { icon: React.ElementType; title: string; description: string }> = {
  idle: {
    icon: Rocket,
    title: "Ready to launch",
    description: "Configure your goal and let AI agents autonomously hunt, tailor, and track your applications.",
  },
  scanning: {
    icon: Search,
    title: "Agents are scanning...",
    description: "Your AI agents are searching opportunities, analyzing matches, and preparing applications.",
  },
  "no-results": {
    icon: Inbox,
    title: "No matches yet",
    description: "Try broadening your search criteria or adjusting your skills profile.",
  },
  "no-content": {
    icon: FileText,
    title: "No documents generated",
    description: "Tailored resumes and cover letters will appear here once applications are prepared.",
  },
  "no-tracking": {
    icon: Sparkles,
    title: "No tracked applications",
    description: "Application status and tracking data will populate after a hunt completes.",
  },
};

export function EmptyState({ variant, className }: EmptyStateProps) {
  const config = VARIANTS[variant];
  const Icon = config.icon;
  const isScanning = variant === "scanning";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-white/[0.08] bg-white/[0.02] px-6 py-10 text-center",
        className
      )}
    >
      <div className={cn(
        "flex h-10 w-10 items-center justify-center rounded-xl bg-white/[0.04] border border-white/[0.06]",
        isScanning && "animate-pulse"
      )}>
        <Icon className="h-5 w-5 text-slate-400" />
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-300">{config.title}</p>
        <p className="mt-1 text-xs text-slate-500 max-w-[280px] leading-relaxed">
          {config.description}
        </p>
      </div>
      {isScanning && (
        <div className="flex gap-1 mt-1">
          {[0, 1, 2].map((i) => (
            <motion.div
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-indigo-400"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.2 }}
            />
          ))}
        </div>
      )}
    </motion.div>
  );
}
