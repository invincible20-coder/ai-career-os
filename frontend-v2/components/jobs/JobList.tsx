"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { MapPin, ExternalLink } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useHuntStore } from "@/lib/store";
import { EmptyState } from "@/components/shared/EmptyState";
import type { Job, Application } from "@/lib/types";

function statusForJob(job: Job, applications: Application[]): string {
  const app = applications.find((a) => a.job_id === job.job_id);
  if (!app) return "pending";
  if (app.status === "submitted") return "applied";
  if (app.status === "failed") return "failed";
  return "prepared";
}

function filterJobs(jobs: Job[], applications: Application[], query: string): Job[] {
  const q = query.trim().toLowerCase();
  if (!q) return jobs;
  return jobs.filter((job) => {
    const status = statusForJob(job, applications);
    return [job.title, job.company, job.location, job.source, status, ...(job.requirements ?? [])]
      .join(" ")
      .toLowerCase()
      .includes(q);
  });
}

function getInitialColor(name: string): string {
  const colors = [
    "bg-indigo-500/20 text-indigo-400",
    "bg-violet-500/20 text-violet-400",
    "bg-cyan-500/20 text-cyan-400",
    "bg-emerald-500/20 text-emerald-400",
    "bg-amber-500/20 text-amber-400",
    "bg-rose-500/20 text-rose-400",
  ];
  let hash = 0;
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
  return colors[Math.abs(hash) % colors.length];
}

const STATUS_BADGE: Record<string, string> = {
  pending: "border-white/[0.08] bg-white/[0.03] text-slate-500",
  prepared: "border-indigo-500/20 bg-indigo-500/10 text-indigo-400",
  applied: "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
  failed: "border-red-500/20 bg-red-500/10 text-red-400",
};

export function JobList() {
  const jobs = useHuntStore((s) => s.jobs);
  const applications = useHuntStore((s) => s.applications);
  const jobFilter = useHuntStore((s) => s.jobFilter);
  const selectedJobId = useHuntStore((s) => s.selectedJobId);
  const setJobFilter = useHuntStore((s) => s.setJobFilter);
  const selectJob = useHuntStore((s) => s.selectJob);
  const activeAction = useHuntStore((s) => s.activeAction);

  const filtered = useMemo(
    () => filterJobs(jobs, applications, jobFilter),
    [jobs, applications, jobFilter]
  );

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111827] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.04]">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
            Job Results
          </p>
          <h2 className="text-sm font-semibold text-slate-200 mt-0.5">
            Opportunities
          </h2>
        </div>
        <Badge variant="outline" className="border-white/[0.06] bg-white/[0.02] text-[10px] text-slate-400 tabular-nums">
          {filtered.length}/{jobs.length}
        </Badge>
      </div>

      {/* Filter */}
      {jobs.length > 0 && (
        <div className="px-4 py-2">
          <Input
            value={jobFilter}
            onChange={(e) => setJobFilter(e.target.value)}
            placeholder="Filter by company, role, skill..."
            className="h-8 rounded-lg border-white/[0.06] bg-white/[0.03] text-xs text-slate-200 placeholder:text-slate-600"
          />
        </div>
      )}

      {/* Job list */}
      <div className="max-h-[420px] overflow-y-auto px-3 py-1 space-y-1">
        {filtered.length > 0 ? (
          filtered.map((job, i) => (
            <JobCard
              key={job.job_id}
              job={job}
              status={statusForJob(job, applications)}
              isSelected={job.job_id === selectedJobId}
              onSelect={() => selectJob(job.job_id)}
              index={i}
            />
          ))
        ) : activeAction === "hunt" ? (
          <EmptyState variant="scanning" className="border-0 bg-transparent py-6" />
        ) : jobs.length === 0 ? (
          <EmptyState variant="idle" className="border-0 bg-transparent py-6" />
        ) : (
          <EmptyState variant="no-results" className="border-0 bg-transparent py-6" />
        )}
      </div>
    </div>
  );
}

function JobCard({
  job,
  status,
  isSelected,
  onSelect,
  index,
}: {
  job: Job;
  status: string;
  isSelected: boolean;
  onSelect: () => void;
  index: number;
}) {
  const initial = job.company?.charAt(0)?.toUpperCase() ?? "?";
  const colorClass = getInitialColor(job.company ?? "");

  return (
    <motion.button
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      onClick={onSelect}
      className={cn(
        "w-full rounded-lg border p-3 text-left transition-all duration-150",
        isSelected
          ? "border-indigo-500/30 bg-indigo-500/[0.06]"
          : "border-white/[0.04] bg-white/[0.01] hover:border-white/[0.08] hover:bg-white/[0.02]"
      )}
    >
      <div className="flex items-start gap-3">
        {/* Company initial */}
        <div className={cn("flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-sm font-bold", colorClass)}>
          {initial}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-slate-200 truncate">{job.title}</p>
            <Badge
              variant="outline"
              className={cn("shrink-0 text-[9px] font-bold uppercase", STATUS_BADGE[status] ?? STATUS_BADGE.pending)}
            >
              {status}
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">{job.company}</p>

          <div className="flex items-center gap-3 mt-1.5">
            {job.location && (
              <span className="flex items-center gap-1 text-[10px] text-slate-500">
                <MapPin className="h-3 w-3" />
                {job.location}
              </span>
            )}
            <span className="text-[10px] text-slate-600">{job.source}</span>
          </div>

          {/* Skills */}
          {job.requirements && job.requirements.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {job.requirements.slice(0, 4).map((skill) => (
                <span
                  key={skill}
                  className="rounded-md border border-white/[0.06] bg-white/[0.03] px-1.5 py-0.5 text-[10px] text-slate-400"
                >
                  {skill}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-end gap-2 mt-2">
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="flex items-center gap-1 text-[10px] font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <ExternalLink className="h-3 w-3" />
            Apply
          </a>
        )}
      </div>
    </motion.button>
  );
}
