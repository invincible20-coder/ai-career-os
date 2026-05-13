"use client";

import { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import { Rocket, Sparkles, RotateCcw, ChevronDown, ChevronUp, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useHuntStore, parseList } from "@/lib/store";
import type { HuntForm } from "@/lib/types";

const PLACEHOLDER_HINTS = [
  "Find backend engineering roles above ₹18L focused on distributed systems",
  "Search for product engineering positions at Series A startups",
  "Find remote Python developer roles with FastAPI experience",
  "Look for full-stack roles at AI/ML companies in Bangalore",
];

export function HeroInput() {
  const form = useHuntStore((s) => s.form);
  const activeAction = useHuntStore((s) => s.activeAction);
  const setField = useHuntStore((s) => s.setField);
  const startHunt = useHuntStore((s) => s.startHunt);
  const recommendCareer = useHuntStore((s) => s.recommendCareer);
  const resetCommandCenter = useHuntStore((s) => s.resetCommandCenter);

  const [expanded, setExpanded] = useState(false);
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const busy = Boolean(activeAction);

  // Cycle placeholder
  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderIdx((i) => (i + 1) % PLACEHOLDER_HINTS.length);
    }, 4000);
    return () => clearInterval(interval);
  }, []);

  // Keyboard shortcut: Cmd+Enter to launch
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && !busy) {
        e.preventDefault();
        startHunt();
      }
    },
    [busy, startHunt]
  );

  const skills = parseList(form.skills);
  const interests = parseList(form.interests);
  const profileSignal = Math.min(
    100,
    20 +
      [form.goal, form.education, form.experience].filter((v) => v.trim()).length * 12 +
      skills.length * 5 +
      interests.length * 4
  );

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111827] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.04]">
        <div>
          <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
            Mission Control
          </p>
          <h2 className="text-sm font-semibold text-slate-200 mt-0.5">
            Define Your Hunt
          </h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold text-slate-500">
            Profile Signal
          </span>
          <div className="relative h-1.5 w-20 rounded-full bg-white/[0.06] overflow-hidden">
            <motion.div
              className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
              initial={{ width: 0 }}
              animate={{ width: `${profileSignal}%` }}
              transition={{ duration: 0.4, ease: "easeOut" }}
            />
          </div>
          <span className="text-[10px] font-bold text-indigo-400">{profileSignal}%</span>
        </div>
      </div>

      {/* Main input */}
      <div className="px-5 pt-4 pb-3" onKeyDown={handleKeyDown}>
        <div className="relative">
          <Input
            value={form.goal}
            onChange={(e) => setField("goal", e.target.value)}
            placeholder={PLACEHOLDER_HINTS[placeholderIdx]}
            disabled={busy}
            className="h-12 rounded-lg border-white/[0.08] bg-white/[0.03] pl-4 pr-4 text-sm text-slate-100 placeholder:text-slate-600 focus:border-indigo-500/40 focus:ring-1 focus:ring-indigo-500/20"
          />
        </div>

        {/* Expand toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 mt-2 text-[11px] font-medium text-slate-500 hover:text-slate-300 transition-colors"
        >
          {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
          {expanded ? "Hide details" : "Add skills, experience & more"}
        </button>
      </div>

      {/* Expanded fields */}
      <motion.div
        initial={false}
        animate={{ height: expanded ? "auto" : 0, opacity: expanded ? 1 : 0 }}
        transition={{ duration: 0.25, ease: "easeInOut" }}
        className="overflow-hidden"
      >
        <div className="grid grid-cols-2 gap-3 px-5 pb-4">
          <FieldBlock label="Skills" name="skills" form={form} setField={setField} busy={busy} rows={3} placeholder="Python, FastAPI, React, SQL" />
          <FieldBlock label="Interests" name="interests" form={form} setField={setField} busy={busy} rows={3} placeholder="automation, systems, product UX" />
          <FieldBlock label="Education" name="education" form={form} setField={setField} busy={busy} placeholder="Degree, bootcamp, certification" isInput />
          <FieldBlock label="Experience" name="experience" form={form} setField={setField} busy={busy} rows={3} placeholder="Projects, internships, shipped tools" />
        </div>
      </motion.div>

      {/* Actions */}
      <div className="flex items-center gap-2 px-5 pb-4">
        <Button
          onClick={() => startHunt()}
          disabled={busy}
          className={cn(
            "h-10 gap-2 rounded-lg bg-gradient-to-r from-indigo-600 to-violet-600 px-5 text-sm font-semibold text-white shadow-lg shadow-indigo-500/20 transition-all hover:shadow-indigo-500/30 hover:brightness-110",
            !busy && form.goal.trim() && "animate-pulse-glow"
          )}
        >
          {activeAction === "hunt" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Rocket className="h-4 w-4" />
          )}
          {activeAction === "hunt" ? "Agents Working..." : "Launch Autonomous Hunt"}
        </Button>

        <Button
          variant="outline"
          onClick={() => recommendCareer()}
          disabled={busy}
          className="h-10 gap-2 rounded-lg border-white/[0.08] bg-white/[0.03] text-sm text-slate-300 hover:bg-white/[0.06]"
        >
          {activeAction === "recommend" ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {activeAction === "recommend" ? "Analyzing..." : "Recommend Career"}
        </Button>

        <Button
          variant="ghost"
          onClick={() => resetCommandCenter()}
          disabled={busy}
          className="h-10 rounded-lg text-sm text-slate-500 hover:text-slate-300"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </Button>

        <div className="ml-auto">
          <Badge variant="outline" className="border-white/[0.06] bg-white/[0.02] text-[10px] text-slate-500">
            ⌘ + Enter
          </Badge>
        </div>
      </div>
    </div>
  );
}

function FieldBlock({
  label,
  name,
  form,
  setField,
  busy,
  placeholder,
  rows,
  isInput,
}: {
  label: string;
  name: keyof HuntForm;
  form: HuntForm;
  setField: (name: keyof HuntForm, value: string) => void;
  busy: boolean;
  placeholder?: string;
  rows?: number;
  isInput?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
        {label}
      </label>
      {isInput ? (
        <Input
          value={form[name]}
          onChange={(e) => setField(name, e.target.value)}
          placeholder={placeholder}
          disabled={busy}
          className="h-9 rounded-lg border-white/[0.06] bg-white/[0.03] text-xs text-slate-200 placeholder:text-slate-600"
        />
      ) : (
        <Textarea
          value={form[name]}
          onChange={(e) => setField(name, e.target.value)}
          placeholder={placeholder}
          disabled={busy}
          rows={rows}
          className="rounded-lg border-white/[0.06] bg-white/[0.03] text-xs text-slate-200 placeholder:text-slate-600 resize-none"
        />
      )}
    </div>
  );
}
