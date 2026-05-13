"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Check, Loader2, X, Clock, Bot } from "lucide-react";
import { cn } from "@/lib/utils";
import { useHuntStore } from "@/lib/store";
import type { StepType, StepStatus, TimelineItem, Timeline, Job, Application, HuntResult } from "@/lib/types";

const STEP_ORDER: StepType[] = ["plan", "search", "apply", "track"];

const STEP_META: Record<StepType, { idle: string; running: string; done: string; agent: string; icon: string }> = {
  plan: { idle: "Generate Plan", running: "Planning...", done: "Plan Ready", agent: "Planner Agent", icon: "📋" },
  search: { idle: "Search Jobs", running: "Searching...", done: "Jobs Found", agent: "Finder Agent", icon: "🔍" },
  apply: { idle: "Prepare Apps", running: "Preparing...", done: "Apps Ready", agent: "Resume Agent", icon: "📄" },
  track: { idle: "Track Status", running: "Tracking...", done: "Tracked", agent: "Tracker Agent", icon: "📊" },
};

function getStepCount(step: StepType, jobs: Job[], applications: Application[], tracker: unknown[]): number {
  if (step === "search") return jobs.length;
  if (step === "apply") return applications.length;
  if (step === "track") return tracker.length || applications.length;
  return 0;
}

export function buildTimeline(huntResult: HuntResult | null, jobs: Job[], applications: Application[], activeAction: string): Timeline {
  const progressByStep = new Map(
    huntResult?.progress?.map((e) => [e.step, e]) ?? []
  );
  const planByStep = new Map(
    huntResult?.plan?.steps?.map((e) => [e.step_type, e]) ?? []
  );
  const tracker = huntResult?.tracker ?? [];

  const items: TimelineItem[] = STEP_ORDER.map((step, index) => {
    const meta = STEP_META[step];
    const progress = progressByStep.get(step);
    const count = getStepCount(step, jobs, applications, tracker);
    const planStep = planByStep.get(step);
    const completedByData =
      (step === "plan" && Boolean(huntResult?.plan)) ||
      (step === "search" && jobs.length > 0) ||
      (step === "apply" && applications.length > 0) ||
      (step === "track" && huntResult?.status === "completed");

    let status: StepStatus = progress?.status ?? (completedByData ? "completed" : "pending");
    if (!huntResult && activeAction === "hunt" && index === 0) status = "running";
    if (huntResult?.status === "running" && status === "pending") {
      const firstPending = STEP_ORDER.find((c) => !progressByStep.has(c));
      if (firstPending === step) status = "running";
    }

    const label = status === "completed" ? meta.done : status === "running" ? meta.running : meta.idle;
    const countLabel = count ? ` (${count})` : "";

    return {
      step,
      agent: meta.agent,
      label: `${label}${countLabel}`,
      status: progress?.status === "failed" ? "failed" : status,
      description: planStep?.description ?? (activeAction === "hunt" && index === 0 ? "Initializing agent pipeline..." : "Waiting for execution."),
      attempts: progress?.attempt_count ?? 0,
      latency: progress?.latency_ms ?? null,
      updatedAt: progress?.updated_at ?? null,
      errors: progress?.last_errors ?? [],
    };
  });

  const completed = items.filter((i) => i.status === "completed").length;
  const running = items.some((i) => i.status === "running") ? 0.5 : 0;
  const progress = Math.min(100, Math.round(((completed + running) / items.length) * 100));

  return { items, progress, completed };
}

const STATUS_ICON: Record<StepStatus, React.ElementType> = {
  completed: Check,
  running: Loader2,
  failed: X,
  pending: Clock,
};

const STATUS_COLORS: Record<StepStatus, string> = {
  completed: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400",
  running: "border-indigo-500/30 bg-indigo-500/10 text-indigo-400",
  failed: "border-red-500/30 bg-red-500/10 text-red-400",
  pending: "border-white/[0.08] bg-white/[0.03] text-slate-500",
};

const LINE_COLORS: Record<StepStatus, string> = {
  completed: "bg-emerald-500/40",
  running: "bg-indigo-500/40",
  failed: "bg-red-500/40",
  pending: "bg-white/[0.06]",
};

export function PlanVisualization() {
  const huntResult = useHuntStore((s) => s.huntResult);
  const jobs = useHuntStore((s) => s.jobs);
  const applications = useHuntStore((s) => s.applications);
  const activeAction = useHuntStore((s) => s.activeAction);

  const timeline = useMemo(
    () => buildTimeline(huntResult, jobs, applications, activeAction),
    [huntResult, jobs, applications, activeAction]
  );

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111827] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.04]">
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-slate-500" />
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Execution Pipeline
            </p>
            <h2 className="text-sm font-semibold text-slate-200 mt-0.5">
              Agent Workflow
            </h2>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative h-1.5 w-24 rounded-full bg-white/[0.06] overflow-hidden">
            <motion.div
              className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-indigo-500 to-emerald-500"
              animate={{ width: `${timeline.progress}%` }}
              transition={{ duration: 0.5, ease: "easeOut" }}
            />
          </div>
          <span className="text-xs font-bold text-slate-300">{timeline.progress}%</span>
        </div>
      </div>

      {/* Steps */}
      <div className="px-5 py-4">
        <div className="space-y-0">
          {timeline.items.map((item, i) => {
            const Icon = STATUS_ICON[item.status];
            const isLast = i === timeline.items.length - 1;

            return (
              <div key={item.step} className="flex gap-3">
                {/* Vertical line + icon */}
                <div className="flex flex-col items-center">
                  <motion.div
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    className={cn(
                      "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border",
                      STATUS_COLORS[item.status],
                      item.status === "running" && "animate-pulse-glow"
                    )}
                  >
                    <Icon className={cn("h-4 w-4", item.status === "running" && "animate-spin")} />
                  </motion.div>
                  {!isLast && (
                    <div className={cn("w-[2px] flex-1 min-h-[20px]", LINE_COLORS[item.status])} />
                  )}
                </div>

                {/* Content */}
                <motion.div
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.05 }}
                  className="flex-1 pb-4 min-w-0"
                >
                  <div className="flex items-center gap-2">
                    <p className={cn(
                      "text-sm font-semibold",
                      item.status === "completed" ? "text-slate-200" :
                      item.status === "running" ? "text-indigo-300" :
                      item.status === "failed" ? "text-red-300" :
                      "text-slate-500"
                    )}>
                      {item.label}
                    </p>
                    <span className="text-[10px] text-slate-600">{item.agent}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-0.5 truncate">{item.description}</p>
                  {(item.latency !== null || item.attempts > 0) && (
                    <div className="flex gap-3 mt-1">
                      {item.latency !== null && (
                        <span className="text-[10px] text-slate-600">{item.latency}ms</span>
                      )}
                      {item.attempts > 0 && (
                        <span className="text-[10px] text-slate-600">
                          {item.attempts} attempt{item.attempts !== 1 ? "s" : ""}
                        </span>
                      )}
                    </div>
                  )}
                </motion.div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
