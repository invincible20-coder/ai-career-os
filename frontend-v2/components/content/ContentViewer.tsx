"use client";

import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText, Mail } from "lucide-react";
import { useHuntStore } from "@/lib/store";
import { EmptyState } from "@/components/shared/EmptyState";
import type { Application, ContentTab } from "@/lib/types";

function textFromApplication(application: Application | null, tab: ContentTab): string {
  if (!application) return "";
  if (tab === "cover") {
    const letter = application.cover_letter;
    return (
      letter?.full_text ||
      [letter?.greeting, letter?.body, letter?.closing].filter(Boolean).join("\n\n")
    );
  }
  const resume = application.resume;
  return (
    resume?.full_text ||
    [resume?.summary, resume?.skills_section, resume?.experience_section].filter(Boolean).join("\n\n")
  );
}

export function ContentViewer() {
  const jobs = useHuntStore((s) => s.jobs);
  const applications = useHuntStore((s) => s.applications);
  const selectedJobId = useHuntStore((s) => s.selectedJobId);
  const contentTab = useHuntStore((s) => s.contentTab);
  const selectJob = useHuntStore((s) => s.selectJob);
  const setContentTab = useHuntStore((s) => s.setContentTab);

  const selectedJob = jobs.find((j) => j.job_id === selectedJobId) ?? jobs[0];
  const selectedApp = applications.find((a) => a.job_id === selectedJob?.job_id) ?? applications[0];
  const docText = textFromApplication(selectedApp ?? null, contentTab);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111827] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.04]">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
            Generated Content
          </p>
          <h2 className="text-sm font-semibold text-slate-200 mt-0.5">
            Application Drafts
          </h2>
        </div>
      </div>

      {/* Job selector */}
      {jobs.length > 0 && (
        <div className="px-4 pt-3">
          <select
            value={selectedJobId}
            onChange={(e) => selectJob(e.target.value)}
            className="w-full h-8 rounded-lg border border-white/[0.06] bg-white/[0.03] px-3 text-xs text-slate-300 outline-none focus:border-indigo-500/40"
          >
            {jobs.map((job) => (
              <option key={job.job_id} value={job.job_id}>
                {job.title} — {job.company}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Tabs */}
      <div className="px-4 pt-3">
        <Tabs value={contentTab} onValueChange={(v) => setContentTab(v as ContentTab)}>
          <TabsList className="h-8 bg-white/[0.03] border border-white/[0.06] rounded-lg p-0.5">
            <TabsTrigger
              value="resume"
              className="h-7 gap-1.5 rounded-md text-xs data-[state=active]:bg-indigo-500/20 data-[state=active]:text-indigo-300"
            >
              <FileText className="h-3 w-3" />
              Resume
            </TabsTrigger>
            <TabsTrigger
              value="cover"
              className="h-7 gap-1.5 rounded-md text-xs data-[state=active]:bg-indigo-500/20 data-[state=active]:text-indigo-300"
            >
              <Mail className="h-3 w-3" />
              Cover Letter
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Document preview */}
      <div className="p-4">
        {docText ? (
          <div className="rounded-lg border border-white/[0.06] bg-[#0B1020] overflow-hidden">
            {selectedJob && (
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-white/[0.04] bg-white/[0.02]">
                <div>
                  <p className="text-xs font-semibold text-slate-200">{selectedJob.title}</p>
                  <p className="text-[10px] text-slate-500">{selectedJob.company}</p>
                </div>
              </div>
            )}
            <pre className="p-4 text-xs text-slate-300 font-mono leading-relaxed whitespace-pre-wrap break-words max-h-[350px] overflow-y-auto">
              {docText}
            </pre>
          </div>
        ) : (
          <EmptyState variant="no-content" />
        )}
      </div>
    </div>
  );
}
