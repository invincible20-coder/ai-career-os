"use client";

import { motion } from "framer-motion";
import { X, Brain, Activity, Sparkles, TrendingUp } from "lucide-react";
import { GlassCard } from "@/components/glass/GlassCard";

interface ContextPanelProps {
  children?: React.ReactNode;
  onClose: () => void;
}

export function ContextPanel({ children, onClose }: ContextPanelProps) {
  return (
    <motion.aside
      initial={{ x: 340, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 340, opacity: 0 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="fixed right-0 top-0 z-40 flex h-screen w-[340px] flex-col glass-panel-elevated"
      style={{ borderLeft: "1px solid var(--glass-border)", borderRadius: 0 }}
    >
      {/* Header */}
      <div
        className="flex h-14 items-center justify-between px-4"
        style={{ borderBottom: "1px solid var(--glass-border)" }}
      >
        <div className="flex items-center gap-2">
          <Brain className="h-4 w-4 text-primary" />
          <span className="text-xs font-semibold text-foreground">AI Intelligence</span>
        </div>
        <button
          onClick={onClose}
          className="flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {children || <DefaultContextContent />}
      </div>
    </motion.aside>
  );
}

function DefaultContextContent() {
  return (
    <>
      {/* AI Activity */}
      <ContextSection
        icon={<Activity className="h-3.5 w-3.5 text-emerald-400" />}
        title="Live AI Activity"
      >
        <div className="space-y-2">
          <ActivityItem agent="Discovery Agent" status="Monitoring job feeds" active />
          <ActivityItem agent="Ranking Agent" status="Idle — waiting for data" />
          <ActivityItem agent="Resume Agent" status="Ready" />
        </div>
      </ContextSection>

      {/* Recommendation Confidence */}
      <ContextSection
        icon={<TrendingUp className="h-3.5 w-3.5 text-primary" />}
        title="Recommendation Confidence"
      >
        <div className="space-y-2">
          <ConfidenceRow label="Profile Understanding" value={34} />
          <ConfidenceRow label="Job Match Accuracy" value={0} />
          <ConfidenceRow label="Behavioral Certainty" value={12} />
        </div>
        <p className="text-[10px] text-muted-foreground mt-3 leading-relaxed">
          Confidence increases as the AI learns from your interactions, applications, and feedback.
        </p>
      </ContextSection>

      {/* Adaptive Hints */}
      <ContextSection
        icon={<Sparkles className="h-3.5 w-3.5 text-violet-400" />}
        title="Adaptive Hints"
      >
        <div className="space-y-2">
          <HintItem text="Complete your profile to improve match accuracy by ~40%" />
          <HintItem text="Try the Chat to tell the AI about your career goals" />
          <HintItem text="Launch your first hunt to activate all agents" />
        </div>
      </ContextSection>
    </>
  );
}

function ContextSection({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <GlassCard className="p-4">
      <div className="flex items-center gap-2 mb-3">
        {icon}
        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          {title}
        </span>
      </div>
      {children}
    </GlassCard>
  );
}

function ActivityItem({
  agent,
  status,
  active = false,
}: {
  agent: string;
  status: string;
  active?: boolean;
}) {
  return (
    <div className="flex items-center gap-2.5">
      <div className="relative">
        <div
          className={`h-2 w-2 rounded-full ${
            active ? "bg-emerald-400 animate-orb-breathe" : "bg-muted-foreground/30"
          }`}
        />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-semibold text-foreground truncate">{agent}</p>
        <p className="text-[10px] text-muted-foreground truncate">{status}</p>
      </div>
    </div>
  );
}

function ConfidenceRow({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-[11px] text-muted-foreground">{label}</span>
        <span className="text-[10px] font-bold text-primary">{value}%</span>
      </div>
      <div
        className="h-1 rounded-full overflow-hidden"
        style={{ background: "var(--glass-bg-elevated)" }}
      >
        <motion.div
          className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 0.8, ease: "easeOut", delay: 0.2 }}
        />
      </div>
    </div>
  );
}

function HintItem({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-2">
      <div className="mt-1 h-1 w-1 rounded-full bg-violet-400 shrink-0" />
      <p className="text-[11px] text-muted-foreground leading-relaxed">{text}</p>
    </div>
  );
}
