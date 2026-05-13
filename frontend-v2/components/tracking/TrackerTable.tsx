"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { ClipboardList } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useHuntStore } from "@/lib/store";
import { EmptyState } from "@/components/shared/EmptyState";
import type { Job, Application, TrackerEntry, TrackerRow } from "@/lib/types";

function formatTime(value: string | null | undefined): string {
  if (!value) return "—";
  try {
    return new Intl.DateTimeFormat(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(new Date(value));
  } catch {
    return "—";
  }
}

function normalizeStatus(status: string): string {
  if (status === "submitted") return "applied";
  if (status === "prepared") return "prepared";
  if (status === "failed") return "failed";
  return "pending";
}

function buildTrackerRows(jobs: Job[], applications: Application[], tracker: TrackerEntry[]): TrackerRow[] {
  if (tracker.length) {
    return tracker.map((e) => ({
      id: e.application_id,
      job: e.job_title,
      company: e.company,
      status: normalizeStatus(e.status),
      time: e.submitted_at ?? e.created_at ?? null,
    }));
  }

  const rows: TrackerRow[] = jobs.map((job) => {
    const app = applications.find((a) => a.job_id === job.job_id);
    return {
      id: app?.application_id ?? job.job_id,
      job: job.title,
      company: job.company,
      status: app ? normalizeStatus(app.status) : "pending",
      time: app?.submitted_at ?? app?.created_at ?? job.scraped_at ?? null,
    };
  });

  applications.forEach((app) => {
    if (!rows.some((r) => r.id === app.application_id)) {
      rows.push({
        id: app.application_id,
        job: app.job_title,
        company: app.company,
        status: normalizeStatus(app.status),
        time: app.submitted_at ?? app.created_at ?? null,
      });
    }
  });

  return rows;
}

const STATUS_STYLES: Record<string, string> = {
  pending: "border-white/[0.08] bg-white/[0.03] text-slate-500",
  prepared: "border-indigo-500/20 bg-indigo-500/10 text-indigo-400",
  applied: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
  failed: "border-red-500/20 bg-red-500/10 text-red-400",
};

export function TrackerTable() {
  const jobs = useHuntStore((s) => s.jobs);
  const applications = useHuntStore((s) => s.applications);
  const huntResult = useHuntStore((s) => s.huntResult);

  const rows = useMemo(
    () => buildTrackerRows(jobs, applications, huntResult?.tracker ?? []),
    [jobs, applications, huntResult?.tracker]
  );

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111827] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.04]">
        <div className="flex items-center gap-2">
          <ClipboardList className="h-4 w-4 text-slate-500" />
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              Application Tracker
            </p>
            <h2 className="text-sm font-semibold text-slate-200 mt-0.5">
              Status Pipeline
            </h2>
          </div>
        </div>
        <Badge variant="outline" className="border-white/[0.06] bg-white/[0.02] text-[10px] text-slate-400 tabular-nums">
          {rows.length}
        </Badge>
      </div>

      {rows.length > 0 ? (
        <div className="max-h-[300px] overflow-y-auto">
          {/* Table header */}
          <div className="grid grid-cols-[1fr_0.8fr_80px_80px] gap-3 px-5 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-white/[0.04] sticky top-0 bg-[#111827]">
            <span>Job</span>
            <span>Company</span>
            <span>Status</span>
            <span>Time</span>
          </div>

          {/* Rows */}
          {rows.map((row, i) => (
            <motion.div
              key={row.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: i * 0.02 }}
              className="grid grid-cols-[1fr_0.8fr_80px_80px] gap-3 items-center px-5 py-2.5 border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors"
            >
              <span className="text-xs text-slate-300 truncate">{row.job}</span>
              <span className="text-xs text-slate-400 truncate">{row.company}</span>
              <Badge
                variant="outline"
                className={cn("text-[9px] font-bold uppercase justify-center", STATUS_STYLES[row.status] ?? STATUS_STYLES.pending)}
              >
                {row.status}
              </Badge>
              <time className="text-[10px] text-slate-600 tabular-nums">{formatTime(row.time)}</time>
            </motion.div>
          ))}
        </div>
      ) : (
        <div className="p-4">
          <EmptyState variant="no-tracking" />
        </div>
      )}
    </div>
  );
}
