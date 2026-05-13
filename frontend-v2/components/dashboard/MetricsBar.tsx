"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { Briefcase, FileCheck, TrendingUp, GitBranch } from "lucide-react";
import { AnimatedCounter } from "@/components/shared/AnimatedCounter";
import { cn } from "@/lib/utils";
import { useHuntStore } from "@/lib/store";

interface Metric {
  label: string;
  value: number;
  suffix?: string;
  icon: React.ElementType;
  color: string;
}

function humanize(value: string): string {
  return value.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase());
}

export function MetricsBar() {
  const huntResult = useHuntStore((s) => s.huntResult);
  const jobs = useHuntStore((s) => s.jobs);
  const applications = useHuntStore((s) => s.applications);
  const analytics = useHuntStore((s) => s.analytics);

  const metrics: Metric[] = useMemo(() => [
    {
      label: "Jobs Found",
      value: huntResult?.summary?.total_jobs ?? jobs.length,
      icon: Briefcase,
      color: "text-indigo-400",
    },
    {
      label: "Applications",
      value: huntResult?.summary?.total_applications ?? applications.length,
      icon: FileCheck,
      color: "text-violet-400",
    },
    {
      label: "Success Rate",
      value: Math.round((analytics?.metrics?.success_rate ?? 0) * 100),
      suffix: "%",
      icon: TrendingUp,
      color: "text-emerald-400",
    },
    {
      label: "Pipeline",
      value: huntResult?.plan?.steps?.length ?? 4,
      suffix: " steps",
      icon: GitBranch,
      color: "text-cyan-400",
    },
  ], [huntResult, jobs, applications, analytics]);

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {metrics.map((metric, i) => {
        const Icon = metric.icon;
        return (
          <motion.div
            key={metric.label}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05 }}
            className="rounded-xl border border-white/[0.06] bg-[#111827] p-4 group hover:border-white/[0.1] transition-colors"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
                {metric.label}
              </span>
              <Icon className={cn("h-3.5 w-3.5", metric.color)} />
            </div>
            <p className="mt-2 text-2xl font-bold text-slate-100 tabular-nums">
              <AnimatedCounter value={metric.value} />
              {metric.suffix && <span className="text-sm font-medium text-slate-400">{metric.suffix}</span>}
            </p>
          </motion.div>
        );
      })}
    </div>
  );
}

export function BehaviorStrip() {
  const analytics = useHuntStore((s) => s.analytics);
  const classification = analytics?.classification ?? "insufficient_data";

  return (
    <div className="flex items-center justify-between rounded-xl border border-amber-500/10 bg-amber-500/[0.04] px-4 py-2.5">
      <div className="flex items-center gap-2">
        <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
          Behavior Profile
        </span>
        <span className="text-xs font-semibold text-amber-400">
          {humanize(classification)}
        </span>
      </div>
      <span className="text-[10px] text-slate-600">
        {analytics?.metrics?.total_applications ?? 0} applications tracked
      </span>
    </div>
  );
}
