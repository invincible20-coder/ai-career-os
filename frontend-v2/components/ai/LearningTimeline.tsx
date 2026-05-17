"use client";

import { motion } from "framer-motion";
import { Brain, ArrowRight } from "lucide-react";
import { GlassCard } from "@/components/glass/GlassCard";

interface TimelineEvent {
  time: string;
  label: string;
  description: string;
  type: "learn" | "adapt" | "discover";
}

const EVENTS: TimelineEvent[] = [
  {
    time: "Just now",
    label: "Session Started",
    description: "AI initialized. Waiting for goals and preferences.",
    type: "discover",
  },
  {
    time: "Earlier",
    label: "System Deployed",
    description: "All 5 agents are online and ready for your first interaction.",
    type: "adapt",
  },
];

const TYPE_COLORS = {
  learn: "bg-violet-500",
  adapt: "bg-primary",
  discover: "bg-emerald-500",
};

export function LearningTimeline() {
  return (
    <GlassCard className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <Brain className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          Learning Evolution
        </span>
      </div>

      <div className="space-y-0">
        {EVENTS.map((event, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.1 }}
            className="flex gap-3"
          >
            {/* Timeline line */}
            <div className="flex flex-col items-center">
              <div className={`h-2 w-2 rounded-full ${TYPE_COLORS[event.type]} shrink-0 mt-1.5`} />
              {i < EVENTS.length - 1 && (
                <div className="w-px flex-1 min-h-[24px]" style={{ background: "var(--glass-border)" }} />
              )}
            </div>

            {/* Content */}
            <div className="pb-4 flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="text-[11px] font-semibold text-foreground">{event.label}</p>
                <span className="text-[10px] text-muted-foreground">{event.time}</span>
              </div>
              <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">
                {event.description}
              </p>
            </div>
          </motion.div>
        ))}
      </div>

      <div className="pt-2 flex items-center gap-1" style={{ borderTop: "1px solid var(--glass-border)" }}>
        <p className="text-[10px] text-muted-foreground">
          The timeline grows as the AI learns from your interactions
        </p>
      </div>
    </GlassCard>
  );
}
