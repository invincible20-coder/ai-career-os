"use client";

import { motion } from "framer-motion";
import { User, Crosshair, Heart, Eye, TrendingUp } from "lucide-react";
import { GlassCard } from "@/components/glass/GlassCard";
import { cn } from "@/lib/utils";

interface Persona {
  type: string;
  confidence: number;
  icon: React.ElementType;
  color: string;
  reasons: string[];
}

const CURRENT_PERSONA: Persona = {
  type: "Explorer",
  confidence: 68,
  icon: Crosshair,
  color: "text-teal-400",
  reasons: [
    "Broad interest range detected",
    "No specific role commitment yet",
    "High curiosity signals",
    "Open to multiple career paths",
  ],
};

const ALL_PERSONAS = [
  { type: "Explorer", icon: Crosshair, active: true },
  { type: "Specialist", icon: TrendingUp, active: false },
  { type: "Desperate", icon: Heart, active: false },
  { type: "Passive", icon: Eye, active: false },
  { type: "High-Potential", icon: User, active: false },
];

export function PersonaDetector() {
  const Icon = CURRENT_PERSONA.icon;

  return (
    <GlassCard className="p-4">
      <div className="flex items-center gap-2 mb-3">
        <User className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          Behavioral Persona
        </span>
      </div>

      {/* Current persona */}
      <div className="flex items-center gap-3 mb-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-teal-500/10">
          <Icon className={cn("h-5 w-5", CURRENT_PERSONA.color)} />
        </div>
        <div>
          <p className="text-sm font-bold text-foreground">{CURRENT_PERSONA.type}</p>
          <p className="text-[10px] text-muted-foreground">
            {CURRENT_PERSONA.confidence}% confidence
          </p>
        </div>
      </div>

      {/* Why */}
      <div className="space-y-1.5 mb-3">
        <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
          Why this classification
        </span>
        {CURRENT_PERSONA.reasons.map((reason, i) => (
          <motion.div
            key={reason}
            initial={{ opacity: 0, x: -4 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.08 }}
            className="flex items-start gap-2"
          >
            <div className="mt-1.5 h-1 w-1 rounded-full bg-primary shrink-0" />
            <p className="text-[11px] text-muted-foreground leading-relaxed">{reason}</p>
          </motion.div>
        ))}
      </div>

      {/* All personas mini view */}
      <div className="flex items-center gap-1.5 pt-2" style={{ borderTop: "1px solid var(--glass-border)" }}>
        {ALL_PERSONAS.map((p) => {
          const PIcon = p.icon;
          return (
            <div
              key={p.type}
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-lg transition-colors",
                p.active ? "bg-primary/10 text-primary" : "text-muted-foreground/40"
              )}
              style={!p.active ? { background: "var(--glass-bg)" } : {}}
              title={p.type}
            >
              <PIcon className="h-3 w-3" />
            </div>
          );
        })}
        <span className="text-[10px] text-muted-foreground ml-auto">5 archetypes</span>
      </div>
    </GlassCard>
  );
}
