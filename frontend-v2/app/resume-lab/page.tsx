"use client";

import { useState } from "react";
import { AppShell } from "@/components/layout/AppShell";
import { motion, AnimatePresence } from "framer-motion";
import { FlaskConical, Target, BrainCircuit, Activity } from "lucide-react";
import { ResumeUploadZone } from "@/components/resume-lab/ResumeUploadZone";
import { LiveAIActivityFeed } from "@/components/resume-lab/LiveAIActivityFeed";
import { ATSScoreRing } from "@/components/resume-lab/ATSScoreRing";
import { ResumeWeaknessAnalyzer } from "@/components/resume-lab/ResumeWeaknessAnalyzer";
import { GlassCard } from "@/components/glass/GlassCard";

// Using a mock userId for demonstration, in reality this comes from next-auth useSession
const MOCK_USER_ID = "demo-user-123"; 

export default function ResumeLabPage() {
  const [analysisState, setAnalysisState] = useState<"idle" | "analyzing" | "complete">("idle");
  const [analysisData, setAnalysisData] = useState<any>(null);

  const handleUploadStart = (userId: string, fileName: string) => {
    setAnalysisState("analyzing");
  };

  const handleAnalysisComplete = (data: any) => {
    setAnalysisData(data);
    setAnalysisState("complete");
  };

  return (
    <AppShell title="Resume Lab" showContext={false}>
      <div className="space-y-6 max-w-6xl mx-auto pb-12">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <div className="flex items-center gap-3 mb-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-indigo-500/20 to-violet-500/20 shadow-[0_0_30px_-5px_rgba(129,140,248,0.3)] border border-indigo-500/20">
              <BrainCircuit className="h-6 w-6 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-3xl font-bold text-foreground tracking-tight">Intelligence Laboratory</h2>
              <p className="text-sm text-muted-foreground mt-1">Adaptive analysis and deterministic resume modeling</p>
            </div>
          </div>
        </motion.div>

        <AnimatePresence mode="wait">
          {analysisState === "idle" && (
            <motion.div
              key="upload"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95, filter: "blur(10px)" }}
              transition={{ duration: 0.4 }}
            >
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <ResumeUploadZone onUploadStart={handleUploadStart} userId={MOCK_USER_ID} />
                </div>
                <div className="space-y-4">
                  <GlassCard className="p-5 border-indigo-500/20 bg-indigo-500/5">
                    <h3 className="text-sm font-semibold flex items-center gap-2 text-indigo-300">
                      <Target className="h-4 w-4" /> Optimization Benchmarks
                    </h3>
                    <ul className="mt-4 space-y-3 text-xs text-muted-foreground">
                      <li className="flex items-start gap-2">
                        <div className="h-1.5 w-1.5 rounded-full bg-indigo-500 mt-1 shrink-0" />
                        <span>Compare against top 5% backend engineering resumes</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <div className="h-1.5 w-1.5 rounded-full bg-indigo-500 mt-1 shrink-0" />
                        <span>Quantifiable impact density modeling</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <div className="h-1.5 w-1.5 rounded-full bg-indigo-500 mt-1 shrink-0" />
                        <span>Algorithmic formatting analysis</span>
                      </li>
                    </ul>
                  </GlassCard>
                </div>
              </div>
            </motion.div>
          )}

          {analysisState === "analyzing" && (
            <motion.div
              key="analyzing"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20, filter: "blur(10px)" }}
              className="max-w-3xl mx-auto"
            >
              <LiveAIActivityFeed userId={MOCK_USER_ID} onComplete={handleAnalysisComplete} />
            </motion.div>
          )}

          {analysisState === "complete" && analysisData && (
            <motion.div
              key="results"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-1 lg:grid-cols-3 gap-6"
            >
              <div className="lg:col-span-1 space-y-6">
                <GlassCard className="p-0 overflow-hidden border-indigo-500/20 bg-gradient-to-b from-indigo-500/5 to-transparent">
                  <div className="p-4 border-b border-border/50 bg-surface/50">
                    <h3 className="text-sm font-bold tracking-tight text-foreground flex items-center gap-2">
                      <Activity className="h-4 w-4 text-indigo-400" /> System Evaluation
                    </h3>
                  </div>
                  <ATSScoreRing 
                    score={analysisData.features.ats_score} 
                    confidence={analysisData.confidence} 
                    trend="up" 
                  />
                  <div className="px-6 pb-6 pt-0">
                    <div className="space-y-3">
                      <MetricBar label="Keyword Density" value={analysisData.features.keyword_density * 100} />
                      <MetricBar label="Readability" value={analysisData.features.readability_score * 100} />
                      <MetricBar label="Action Verbs" value={analysisData.features.action_verb_usage * 100} />
                      <MetricBar label="Tech Depth" value={analysisData.features.technical_depth * 100} />
                    </div>
                  </div>
                </GlassCard>
              </div>

              <div className="lg:col-span-2">
                <ResumeWeaknessAnalyzer weaknesses={analysisData.weaknesses} />
                
                <div className="mt-6 flex justify-end">
                  <button 
                    onClick={() => { setAnalysisState("idle"); setAnalysisData(null); }}
                    className="px-4 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Analyze Another Resume
                  </button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </AppShell>
  );
}

function MetricBar({ label, value }: { label: string, value: number }) {
  return (
    <div>
      <div className="flex justify-between text-[10px] uppercase font-bold tracking-wider mb-1">
        <span className="text-muted-foreground">{label}</span>
        <span className="text-foreground">{value.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 w-full bg-surface-elevated rounded-full overflow-hidden">
        <motion.div 
          className="h-full bg-indigo-500"
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 1, delay: 0.5 }}
        />
      </div>
    </div>
  );
}
