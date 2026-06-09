"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Search, SlidersHorizontal, Shield, ShieldCheck, ShieldAlert, MapPin, Bookmark, ChevronDown, ChevronUp, Sparkles, TrendingUp, FileText, Zap, Star } from "lucide-react";
import { cn } from "@/lib/utils";
import { AppShell } from "@/components/layout/AppShell";
import { GlassCard } from "@/components/glass/GlassCard";

interface JobData {
  id: string; title: string; company: string; location: string; salary: string; remote: boolean;
  matchPct: number; confidencePct: number; trustScore: number;
  rankingReason: string; whyRecommended: string[];
  skills: { name: string; matched: boolean }[];
  interviewProb: number; trajectoryImpact: string;
}

const SAMPLE_JOBS: JobData[] = [
  {
    id: "1", title: "Senior Backend Engineer", company: "Vercel", location: "San Francisco, CA", salary: "$180k–$220k", remote: true,
    matchPct: 92, confidencePct: 87, trustScore: 98,
    rankingReason: "Your backend applications have a 24% interview rate — 3x above average for this segment.",
    whyRecommended: ["Strong Python/FastAPI skill alignment", "Distributed systems interest matches role", "Company culture fits Explorer persona", "Remote-first matches your preference"],
    skills: [{ name: "Python", matched: true }, { name: "FastAPI", matched: true }, { name: "PostgreSQL", matched: true }, { name: "Kubernetes", matched: false }, { name: "gRPC", matched: false }, { name: "Go", matched: false }],
    interviewProb: 34, trajectoryImpact: "Strong career accelerator — senior IC track at top-tier company",
  },
  {
    id: "2", title: "Platform Engineer", company: "Linear", location: "Remote", salary: "$160k–$200k", remote: true,
    matchPct: 85, confidencePct: 79, trustScore: 95,
    rankingReason: "Platform engineering roles have high success rates for candidates with your systems background.",
    whyRecommended: ["Systems thinking alignment", "API design experience relevant", "Growing field with strong progression"],
    skills: [{ name: "TypeScript", matched: false }, { name: "Node.js", matched: true }, { name: "AWS", matched: false }, { name: "Docker", matched: true }, { name: "CI/CD", matched: true }],
    interviewProb: 28, trajectoryImpact: "High growth potential — platform engineering is expanding rapidly",
  },
  {
    id: "3", title: "Full Stack Engineer", company: "Notion", location: "New York, NY", salary: "$150k–$190k", remote: false,
    matchPct: 78, confidencePct: 71, trustScore: 97,
    rankingReason: "Full-stack roles match your breadth of skills, though your backend strength is the primary signal.",
    whyRecommended: ["Breadth of skills valued", "Product-oriented engineering", "Strong company reputation"],
    skills: [{ name: "React", matched: true }, { name: "TypeScript", matched: false }, { name: "Python", matched: true }, { name: "PostgreSQL", matched: true }],
    interviewProb: 22, trajectoryImpact: "Solid career move — premium brand with growth opportunity",
  },
];

export default function JobsPage() {
  const [filter, setFilter] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [savedJobs, setSavedJobs] = useState<Set<string>>(new Set());

  const filtered = SAMPLE_JOBS.filter((j) => {
    const q = filter.toLowerCase();
    if (!q) return true;
    return [j.title, j.company, j.location].join(" ").toLowerCase().includes(q);
  });

  const toggleSave = (id: string) => {
    setSavedJobs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  return (
    <AppShell title="Job Discovery" contextContent={<JobsContext />}>
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-foreground">Intelligent Job Discovery</h2>
            <p className="text-sm text-muted-foreground">AI-ranked opportunities personalized to your career profile</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg" style={{ background: "var(--glass-bg)", border: "1px solid var(--glass-border)" }}>
            <Sparkles className="h-3 w-3 text-primary" />
            <span className="text-[11px] font-semibold text-foreground">{filtered.length} matches</span>
          </div>
        </div>

        {/* Search */}
        <div className="flex gap-2">
          <div className="flex-1 flex items-center gap-2 glass-input rounded-xl px-3 py-2">
            <Search className="h-4 w-4 text-muted-foreground" />
            <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Search roles, companies, skills..." className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground focus:outline-none" />
          </div>
          <button className="flex items-center gap-2 px-3 py-2 rounded-xl glass-card text-xs font-medium text-muted-foreground">
            <SlidersHorizontal className="h-3.5 w-3.5" /> Filters
          </button>
        </div>

        {/* Job list */}
        <div className="space-y-3">
          {filtered.map((job, i) => (
            <JobCard key={job.id} job={job} index={i} expanded={expandedId === job.id} onToggle={() => setExpandedId(expandedId === job.id ? null : job.id)} saved={savedJobs.has(job.id)} onSave={() => toggleSave(job.id)} />
          ))}
        </div>
      </div>
    </AppShell>
  );
}

function JobCard({ job, index, expanded, onToggle, saved, onSave }: { job: JobData; index: number; expanded: boolean; onToggle: () => void; saved: boolean; onSave: () => void }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05 }}>
      <GlassCard className={cn("overflow-hidden", expanded && "glass-card-active")}>
        {/* Main row */}
        <div className="p-4 cursor-pointer" onClick={onToggle}>
          <div className="flex items-start gap-4">
            {/* Company avatar */}
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500/15 to-violet-500/10 text-sm font-bold text-primary">
              {job.company.charAt(0)}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm font-bold text-foreground">{job.title}</h3>
                <TrustBadge score={job.trustScore} />
                {job.remote && <span className="text-[10px] px-1.5 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Remote</span>}
              </div>
              <div className="flex items-center gap-3 mt-1">
                <span className="text-xs text-muted-foreground">{job.company}</span>
                <span className="flex items-center gap-1 text-[11px] text-muted-foreground"><MapPin className="h-3 w-3" />{job.location}</span>
                <span className="text-xs font-semibold text-foreground">{job.salary}</span>
              </div>

              {/* Why recommended */}
              <div className="mt-2 flex items-start gap-1.5 px-2.5 py-1.5 rounded-lg" style={{ background: "var(--glass-bg)" }}>
                <Sparkles className="h-3 w-3 text-primary shrink-0 mt-0.5" />
                <p className="text-[11px] text-muted-foreground leading-relaxed">{job.rankingReason}</p>
              </div>
            </div>

            {/* Right metrics */}
            <div className="flex flex-col items-end gap-2 shrink-0">
              <div className="flex items-center gap-2">
                <MetricPill label="Match" value={job.matchPct} color="indigo" />
                <MetricPill label="Confidence" value={job.confidencePct} color="violet" />
              </div>
              <div className="flex items-center gap-1.5">
                <button onClick={(e) => { e.stopPropagation(); onSave(); }} className={cn("flex h-7 w-7 items-center justify-center rounded-lg transition-colors", saved ? "bg-amber-500/10 text-amber-400" : "text-muted-foreground hover:text-foreground")} style={!saved ? { background: "var(--glass-bg)" } : {}}>
                  {saved ? <Star className="h-3.5 w-3.5 fill-current" /> : <Bookmark className="h-3.5 w-3.5" />}
                </button>
                <span className="text-muted-foreground">{expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Expanded intelligence view */}
        <AnimatePresence>
          {expanded && (
            <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: "auto", opacity: 1 }} exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }}>
              <div className="px-4 pb-4 space-y-4" style={{ borderTop: "1px solid var(--glass-border)" }}>
                <div className="pt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Why recommended detail */}
                  <div>
                    <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">Why Recommended</h4>
                    <div className="space-y-1.5">
                      {job.whyRecommended.map((r, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <div className="mt-1.5 h-1 w-1 rounded-full bg-primary shrink-0" />
                          <span className="text-[11px] text-muted-foreground">{r}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Skill heatmap */}
                  <div>
                    <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-2">Resume Match Heatmap</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {job.skills.map((s) => (
                        <span key={s.name} className={cn("text-[10px] px-2 py-1 rounded-md border", s.matched ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20" : "bg-red-500/10 text-red-400 border-red-500/20")}>
                          {s.matched ? "✓" : "✗"} {s.name}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Bottom metrics */}
                <div className="flex items-center gap-4 pt-2" style={{ borderTop: "1px solid var(--glass-border)" }}>
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-3 w-3 text-primary" />
                    <span className="text-[11px] text-muted-foreground">Interview probability: <strong className="text-foreground">{job.interviewProb}%</strong></span>
                  </div>
                  <span className="text-[11px] text-muted-foreground">{job.trajectoryImpact}</span>
                  <div className="ml-auto flex gap-2">
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium text-foreground glass-card !rounded-lg">
                      <FileText className="h-3 w-3" /> Generate Resume
                    </button>
                    <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold text-white bg-gradient-to-r from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/20">
                      <Zap className="h-3 w-3" /> Apply Now
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </GlassCard>
    </motion.div>
  );
}

function TrustBadge({ score }: { score: number }) {
  if (score >= 90) return <span className="flex items-center gap-0.5 text-[10px] text-emerald-400"><ShieldCheck className="h-3 w-3" /> Verified</span>;
  if (score >= 70) return <span className="flex items-center gap-0.5 text-[10px] text-amber-400"><Shield className="h-3 w-3" /> Caution</span>;
  return <span className="flex items-center gap-0.5 text-[10px] text-red-400"><ShieldAlert className="h-3 w-3" /> Suspicious</span>;
}

function MetricPill({ label, value, color }: { label: string; value: number; color: "indigo" | "violet" }) {
  const colors = { indigo: "from-indigo-500/15 to-indigo-500/5 text-indigo-400 border-indigo-500/20", violet: "from-violet-500/15 to-violet-500/5 text-violet-400 border-violet-500/20" };
  return (
    <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded-md border bg-gradient-to-r", colors[color])}>
      {label} {value}%
    </span>
  );
}

function JobsContext() {
  return (
    <div className="space-y-4">
      <GlassCard className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="h-3.5 w-3.5 text-primary" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Ranking Intelligence</span>
        </div>
        <p className="text-[11px] text-muted-foreground leading-relaxed">Jobs are ranked by combining skill match, behavioral signals, and success predictions. Rankings update in real-time as you interact.</p>
      </GlassCard>
      <GlassCard className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <Shield className="h-3.5 w-3.5 text-emerald-400" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Trust Verification</span>
        </div>
        <p className="text-[11px] text-muted-foreground leading-relaxed">Every listing is verified for legitimacy. Trust scores factor in source quality, company verification, and suspicious pattern detection.</p>
      </GlassCard>
    </div>
  );
}
