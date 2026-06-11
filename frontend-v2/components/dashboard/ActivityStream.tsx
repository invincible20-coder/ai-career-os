"use client";

import { motion } from "framer-motion";
import {
  CheckCircle2,
  AlertCircle,
  Info,
  AlertTriangle,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useHuntStore } from "@/lib/store";
import { EmptyState } from "@/components/shared/EmptyState";
import type { LogEntry, LogLevel } from "@/lib/types";

const LEVEL_CONFIG: Record<LogLevel, { icon: React.ElementType; color: string; bg: string }> = {
  success: { icon: CheckCircle2, color: "text-emerald-400", bg: "bg-emerald-500/10 border-emerald-500/20" },
  error: { icon: AlertCircle, color: "text-red-400", bg: "bg-red-500/10 border-red-500/20" },
  warn: { icon: AlertTriangle, color: "text-amber-400", bg: "bg-amber-500/10 border-amber-500/20" },
  info: { icon: Info, color: "text-teal-400", bg: "bg-teal-500/10 border-teal-500/20" },
};

function formatTime(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(iso));
  } catch {
    return "";
  }
}

export function ActivityStream() {
  const logs = useHuntStore((s) => s.logs);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111827] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.04]">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-slate-500" />
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Activity Stream
            </p>
            <h2 className="text-sm font-semibold text-slate-200 mt-0.5">
              AI Agent Log
            </h2>
          </div>
        </div>
        <span className="text-[10px] font-medium text-slate-600">
          {logs.length} events
        </span>
      </div>

      {/* Stream */}
      <div className="max-h-[320px] overflow-y-auto px-3 py-2 space-y-1">
        {logs.length > 0 ? (
          logs.map((log, i) => <ActivityItem key={log.id} log={log} index={i} />)
        ) : (
          <EmptyState variant="idle" className="border-0 bg-transparent py-6" />
        )}
      </div>
    </div>
  );
}

function ActivityItem({ log, index }: { log: LogEntry; index: number }) {
  const config = LEVEL_CONFIG[log.level];
  const Icon = config.icon;

  return (
    <motion.div
      initial={index === 0 ? { opacity: 0, y: -6 } : false}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex items-start gap-2.5 rounded-lg px-2 py-2 hover:bg-white/[0.02] transition-colors group"
    >
      <div className={cn("flex h-6 w-6 shrink-0 items-center justify-center rounded-md border", config.bg)}>
        <Icon className={cn("h-3 w-3", config.color)} />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-slate-300 leading-relaxed break-words">
          {log.message}
        </p>
      </div>
      <time className="shrink-0 text-[10px] text-slate-600 tabular-nums pt-0.5">
        {formatTime(log.at)}
      </time>
    </motion.div>
  );
}
