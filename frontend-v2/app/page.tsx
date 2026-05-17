"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Sparkles, Zap } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { CommandInput } from "@/components/command/CommandInput";
import { SuggestionChips } from "@/components/command/SuggestionChips";
import { SignalMeter } from "@/components/command/SignalMeter";
import { AgentActivity } from "@/components/ai/AgentActivity";
import { PersonaDetector } from "@/components/ai/PersonaDetector";
import { LearningTimeline } from "@/components/ai/LearningTimeline";
import { GlassCard } from "@/components/glass/GlassCard";

export default function CommandCenterPage() {
  const [goal, setGoal] = useState("");
  const [hasSubmitted, setHasSubmitted] = useState(false);

  const handleSubmit = useCallback(() => {
    if (!goal.trim()) return;
    setHasSubmitted(true);
  }, [goal]);

  const handleChipSelect = useCallback((label: string) => {
    setGoal((prev) =>
      prev ? `${prev}\n\nI'm interested in: ${label}` : `I'm interested in: ${label}`
    );
  }, []);

  const greeting = getGreeting();

  return (
    <AppShell
      title="Command Center"
      contextContent={<CommandCenterContext />}
    >
      <div className="space-y-6">
        {/* Greeting */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
        >
          <div className="flex items-center gap-3 mb-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20">
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-foreground tracking-tight">
                {greeting}, Swaransh
              </h2>
              <p className="text-sm text-muted-foreground">
                Your AI career strategist is ready. What&apos;s on your mind?
              </p>
            </div>
          </div>
        </motion.div>

        {/* Command Input */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.1 }}
        >
          <CommandInput
            value={goal}
            onChange={setGoal}
            onSubmit={handleSubmit}
          />
        </motion.div>

        {/* Suggestion Chips */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <SuggestionChips onSelect={handleChipSelect} />
        </motion.div>

        {/* Signal Meter */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.3 }}
        >
          <SignalMeter />
        </motion.div>

        {/* Quick Intelligence Cards */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.4 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-4"
        >
          <QuickCard
            icon={<Zap className="h-4 w-4 text-amber-400" />}
            title="Quick Hunt"
            description="Launch an autonomous job search with AI agents"
            action="Start Hunt"
            gradient="from-amber-500/10 to-orange-500/5"
          />
          <QuickCard
            icon={<Sparkles className="h-4 w-4 text-violet-400" />}
            title="Career Analysis"
            description="Get AI-powered career path recommendations"
            action="Analyze"
            gradient="from-violet-500/10 to-purple-500/5"
          />
          <QuickCard
            icon={<Zap className="h-4 w-4 text-emerald-400" />}
            title="Resume Lab"
            description="Optimize your resume with AI intelligence"
            action="Open Lab"
            gradient="from-emerald-500/10 to-teal-500/5"
          />
        </motion.div>

        {/* Agent Activity */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.5 }}
        >
          <AgentActivity />
        </motion.div>
      </div>
    </AppShell>
  );
}

function CommandCenterContext() {
  return (
    <div className="space-y-4">
      <PersonaDetector />
      <LearningTimeline />
    </div>
  );
}

function QuickCard({
  icon,
  title,
  description,
  action,
  gradient,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  action: string;
  gradient: string;
}) {
  return (
    <GlassCard className={`p-4 bg-gradient-to-br ${gradient}`}>
      <div className="flex items-start gap-3">
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl"
          style={{ background: "var(--glass-bg-elevated)" }}
        >
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
          <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed">
            {description}
          </p>
          <button className="mt-3 text-[11px] font-semibold text-primary hover:text-primary/80 transition-colors flex items-center gap-1">
            {action}
            <span className="text-[10px]">→</span>
          </button>
        </div>
      </div>
    </GlassCard>
  );
}

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}
