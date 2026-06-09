"use client";

import { useState, useCallback, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Zap, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { AppShell } from "@/components/layout/AppShell";
import { CommandInput } from "@/components/command/CommandInput";
import { SuggestionChips } from "@/components/command/SuggestionChips";
import { SignalMeter } from "@/components/command/SignalMeter";
import { AgentActivity } from "@/components/ai/AgentActivity";
import { PersonaDetector } from "@/components/ai/PersonaDetector";
import { LearningTimeline } from "@/components/ai/LearningTimeline";
import { GlassCard } from "@/components/glass/GlassCard";
import { useHuntStore } from "@/lib/store";

export default function CommandCenterPage() {
  const [goal, setGoal] = useState("");

  // ── Backend-connected store ──
  const startHunt = useHuntStore((s) => s.startHunt);
  const recommendCareer = useHuntStore((s) => s.recommendCareer);
  const checkHealth = useHuntStore((s) => s.checkHealth);
  const setField = useHuntStore((s) => s.setField);
  const activeAction = useHuntStore((s) => s.activeAction);
  const serverState = useHuntStore((s) => s.serverState);
  const huntResult = useHuntStore((s) => s.huntResult);
  const errorMessage = useHuntStore((s) => s.errorMessage);
  const jobs = useHuntStore((s) => s.jobs);
  const applications = useHuntStore((s) => s.applications);

  // ── Health check on mount ──
  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  // ── Submit handler — calls actual backend ──
  const handleSubmit = useCallback(() => {
    if (!goal.trim() || activeAction) return;
    setField("goal", goal.trim());
    startHunt(goal.trim());
  }, [goal, activeAction, setField, startHunt]);

  // ── Chip select → populate goal and launch career recommendation ──
  const handleChipSelect = useCallback(
    (label: string) => {
      setGoal(label);
      setField("goal", label);
    },
    [setField]
  );

  const isWorking = !!activeAction;
  const greeting = getGreeting();

  return (
    <AppShell
      title="Command Center"
      contextContent={<CommandCenterContext />}
    >
      <div className="space-y-6">
        {/* Server Status */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-2"
        >
          <div
            className={`h-2 w-2 rounded-full ${
              serverState.tone === "online"
                ? "bg-emerald-400"
                : serverState.tone === "checking"
                ? "bg-amber-400 animate-pulse"
                : "bg-red-400"
            }`}
          />
          <span className="text-[10px] font-mono text-muted-foreground">
            Backend: {serverState.label}
          </span>
        </motion.div>

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
            disabled={isWorking}
          />
        </motion.div>

        {/* Error display */}
        <AnimatePresence>
          {errorMessage && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
            >
              <GlassCard className="p-4 border-red-500/20 bg-red-500/5">
                <div className="flex items-center gap-2 text-red-400">
                  <AlertCircle className="h-4 w-4 shrink-0" />
                  <p className="text-xs">{errorMessage}</p>
                </div>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Active operation indicator */}
        <AnimatePresence>
          {isWorking && (
            <motion.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <GlassCard className="p-4 border-indigo-500/20 bg-indigo-500/5">
                <div className="flex items-center gap-3">
                  <Loader2 className="h-4 w-4 text-indigo-400 animate-spin" />
                  <div>
                    <p className="text-xs font-semibold text-indigo-300">
                      {activeAction === "hunt"
                        ? "Autonomous hunt in progress…"
                        : "Analyzing career options…"}
                    </p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      Agents are communicating with the backend
                    </p>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Hunt results */}
        <AnimatePresence>
          {huntResult && !isWorking && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
            >
              <GlassCard className="p-5 border-emerald-500/20 bg-emerald-500/5">
                <div className="flex items-center gap-2 mb-3">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  <h3 className="text-sm font-semibold text-emerald-300">
                    Hunt Complete
                  </h3>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-2xl font-bold text-foreground">
                      {jobs.length}
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      Jobs Found
                    </p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-foreground">
                      {applications.length}
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      Applications
                    </p>
                  </div>
                  <div>
                    <p className="text-2xl font-bold text-foreground capitalize">
                      {huntResult?.status ?? "done"}
                    </p>
                    <p className="text-[10px] text-muted-foreground">Status</p>
                  </div>
                </div>
              </GlassCard>
            </motion.div>
          )}
        </AnimatePresence>

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
            onClick={() => {
              if (goal.trim()) {
                setField("goal", goal.trim());
                startHunt(goal.trim());
              }
            }}
            disabled={isWorking || !goal.trim()}
          />
          <QuickCard
            icon={<Sparkles className="h-4 w-4 text-violet-400" />}
            title="Career Analysis"
            description="Get AI-powered career path recommendations"
            action="Analyze"
            gradient="from-violet-500/10 to-purple-500/5"
            onClick={() => recommendCareer()}
            disabled={isWorking}
          />
          <QuickCard
            icon={<Zap className="h-4 w-4 text-emerald-400" />}
            title="Resume Lab"
            description="Optimize your resume with AI intelligence"
            action="Open Lab"
            gradient="from-emerald-500/10 to-teal-500/5"
            onClick={() => {
              window.location.href = "/resume-lab";
            }}
            disabled={false}
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
  onClick,
  disabled = false,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  action: string;
  gradient: string;
  onClick?: () => void;
  disabled?: boolean;
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
          <button
            onClick={onClick}
            disabled={disabled}
            className="mt-3 text-[11px] font-semibold text-primary hover:text-primary/80 transition-colors flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed"
          >
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
