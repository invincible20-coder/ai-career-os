"use client";

import { motion } from "framer-motion";
import { Bot, Loader2, Check, Clock, Zap } from "lucide-react";
import { GlassCard } from "@/components/glass/GlassCard";
import { cn } from "@/lib/utils";

interface Agent {
  name: string;
  role: string;
  status: "idle" | "active" | "complete";
  task?: string;
  latency?: string;
}

const AGENTS: Agent[] = [
  { name: "Planner Agent", role: "Strategy & goal decomposition", status: "complete", task: "Goal analysis complete", latency: "240ms" },
  { name: "Discovery Agent", role: "Job search & market scanning", status: "active", task: "Scanning 3 platforms…", latency: "1.2s" },
  { name: "Ranking Agent", role: "Relevance scoring & matching", status: "idle", task: "Waiting for discovery results" },
  { name: "Resume Agent", role: "Resume optimization & tailoring", status: "idle", task: "Standby" },
  { name: "Strategy Agent", role: "Career path evaluation", status: "idle", task: "Standby" },
];

const STATUS_CONFIG = {
  idle: { icon: Clock, color: "text-muted-foreground", bg: "bg-muted/30", dot: "bg-muted-foreground/30" },
  active: { icon: Loader2, color: "text-primary", bg: "bg-primary/10", dot: "bg-primary animate-orb-active" },
  complete: { icon: Check, color: "text-emerald-400", bg: "bg-emerald-500/10", dot: "bg-emerald-400" },
};

export function AgentActivity() {
  return (
    <GlassCard className="overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3" style={{ borderBottom: "1px solid var(--glass-border)" }}>
        <div className="flex items-center gap-2">
          <Bot className="h-4 w-4 text-primary" />
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
              Live Agent Activity
            </p>
            <h3 className="text-sm font-semibold text-foreground mt-0.5">
              AI Agent Orchestra
            </h3>
          </div>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg" style={{ background: "var(--glass-bg)" }}>
          <Zap className="h-3 w-3 text-primary" />
          <span className="text-[10px] font-semibold text-primary">
            {AGENTS.filter((a) => a.status === "active").length} Active
          </span>
        </div>
      </div>

      {/* Agent list */}
      <div className="divide-y" style={{ borderColor: "var(--glass-border)" }}>
        {AGENTS.map((agent, i) => {
          const config = STATUS_CONFIG[agent.status];
          const Icon = config.icon;
          return (
            <motion.div
              key={agent.name}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.05 }}
              className="flex items-center gap-4 px-5 py-3 hover:bg-[var(--glass-bg-hover)] transition-colors"
            >
              {/* Status dot */}
              <div className={cn("h-2.5 w-2.5 rounded-full shrink-0", config.dot)} />

              {/* Icon */}
              <div className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-lg", config.bg)}>
                <Icon className={cn("h-3.5 w-3.5", config.color, agent.status === "active" && "animate-spin")} />
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="text-xs font-semibold text-foreground">{agent.name}</p>
                  <span className="text-[10px] text-muted-foreground">{agent.role}</span>
                </div>
                <p className={cn("text-[11px] mt-0.5", agent.status === "active" ? "text-primary" : "text-muted-foreground")}>
                  {agent.task}
                </p>
              </div>

              {/* Latency */}
              {agent.latency && (
                <span className="text-[10px] font-mono text-muted-foreground shrink-0">
                  {agent.latency}
                </span>
              )}
            </motion.div>
          );
        })}
      </div>
    </GlassCard>
  );
}
