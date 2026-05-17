"use client";

import { motion } from "framer-motion";
import { GlassCard } from "@/components/glass/GlassCard";

interface Signal {
  label: string;
  value: number;
  color: string;
}

interface SignalMeterProps {
  signals?: Signal[];
}

const DEFAULT_SIGNALS: Signal[] = [
  { label: "Confidence", value: 20, color: "#818CF8" },
  { label: "Profile", value: 34, color: "#A78BFA" },
  { label: "Behavioral", value: 12, color: "#22D3EE" },
  { label: "Stability", value: 0, color: "#34D399" },
];

export function SignalMeter({ signals = DEFAULT_SIGNALS }: SignalMeterProps) {
  return (
    <GlassCard className="p-4">
      <div className="flex items-center gap-2 mb-4">
        <div className="h-2 w-2 rounded-full bg-primary animate-orb-breathe" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          Adaptive Signal Meter
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {signals.map((signal, i) => (
          <SignalGauge key={signal.label} signal={signal} delay={i * 0.1} />
        ))}
      </div>
    </GlassCard>
  );
}

function SignalGauge({ signal, delay }: { signal: Signal; delay: number }) {
  const circumference = 2 * Math.PI * 28;
  const offset = circumference - (signal.value / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative h-16 w-16">
        <svg viewBox="0 0 64 64" className="h-16 w-16 confidence-ring">
          {/* Background ring */}
          <circle
            cx="32"
            cy="32"
            r="28"
            fill="none"
            stroke="var(--glass-border)"
            strokeWidth="3"
          />
          {/* Value ring */}
          <motion.circle
            cx="32"
            cy="32"
            r="28"
            fill="none"
            stroke={signal.color}
            strokeWidth="3"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 1.2, ease: "easeOut", delay: delay + 0.3 }}
            style={{ filter: `drop-shadow(0 0 6px ${signal.color}40)` }}
          />
        </svg>
        {/* Center value */}
        <div className="absolute inset-0 flex items-center justify-center">
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: delay + 0.5 }}
            className="text-sm font-bold text-foreground"
          >
            {signal.value}%
          </motion.span>
        </div>
      </div>
      <span className="text-[10px] font-medium text-muted-foreground text-center leading-tight">
        {signal.label}
      </span>
    </div>
  );
}
