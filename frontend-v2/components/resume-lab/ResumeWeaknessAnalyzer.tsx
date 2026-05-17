"use client";

import { motion } from "framer-motion";
import { AlertTriangle, TrendingUp, ShieldCheck, ArrowRight, Zap } from "lucide-react";
import { GlassCard } from "@/components/glass/GlassCard";

interface Weakness {
  id: string;
  category: string;
  severity: "high" | "medium" | "low";
  description: string;
  recommendation: string;
  expected_improvement: string;
  confidence: number;
}

interface ResumeWeaknessAnalyzerProps {
  weaknesses: Weakness[];
}

export function ResumeWeaknessAnalyzer({ weaknesses }: ResumeWeaknessAnalyzerProps) {
  if (!weaknesses || weaknesses.length === 0) {
    return (
      <GlassCard className="p-6 border-emerald-500/20 bg-emerald-500/5 flex items-center gap-4">
        <div className="h-12 w-12 rounded-full bg-emerald-500/10 flex items-center justify-center shrink-0">
          <ShieldCheck className="h-6 w-6 text-emerald-400" />
        </div>
        <div>
          <h3 className="text-emerald-400 font-bold tracking-tight">No Critical Weaknesses Detected</h3>
          <p className="text-xs text-muted-foreground mt-1">Your resume aligns exceptionally well with the target benchmarks.</p>
        </div>
      </GlassCard>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 px-1">
        <AlertTriangle className="h-4 w-4 text-yellow-500" />
        <h3 className="text-sm font-semibold text-foreground tracking-tight">Structural Weaknesses</h3>
        <span className="ml-auto text-[10px] uppercase font-bold text-muted-foreground tracking-wider">AI Analysis</span>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {weaknesses.map((weakness, index) => (
          <motion.div
            key={weakness.id}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <GlassCard className={`p-4 border-l-4 ${
              weakness.severity === 'high' ? 'border-l-red-500 bg-red-500/5' : 
              weakness.severity === 'medium' ? 'border-l-yellow-500 bg-yellow-500/5' : 
              'border-l-indigo-500 bg-indigo-500/5'
            }`}>
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                      weakness.severity === 'high' ? 'bg-red-500/10 text-red-400' : 
                      weakness.severity === 'medium' ? 'bg-yellow-500/10 text-yellow-400' : 
                      'bg-indigo-500/10 text-indigo-400'
                    }`}>
                      {weakness.severity} Severity
                    </span>
                    <span className="text-[10px] text-muted-foreground">{weakness.category}</span>
                  </div>
                  <h4 className="text-sm font-semibold text-foreground mt-2">{weakness.description}</h4>
                  
                  <div className="mt-3 p-3 bg-surface rounded-lg border border-border/50">
                    <div className="flex items-start gap-2">
                      <Zap className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
                      <div>
                        <span className="text-[11px] font-semibold text-indigo-300 uppercase tracking-wider mb-1 block">AI Recommendation</span>
                        <p className="text-xs text-muted-foreground">{weakness.recommendation}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="md:w-48 shrink-0 flex flex-col justify-center border-t md:border-t-0 md:border-l border-border/50 pt-3 md:pt-0 md:pl-4">
                  <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-1">Expected Impact</span>
                  <div className="flex items-center gap-2 text-emerald-400">
                    <TrendingUp className="h-4 w-4" />
                    <span className="text-sm font-bold">{weakness.expected_improvement}</span>
                  </div>
                  <div className="mt-3">
                    <div className="flex justify-between text-[10px] mb-1">
                      <span className="text-muted-foreground">Confidence</span>
                      <span className="font-bold text-foreground">{(weakness.confidence * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-1 w-full bg-surface-elevated rounded-full overflow-hidden">
                      <motion.div 
                        className="h-full bg-indigo-500" 
                        initial={{ width: 0 }}
                        animate={{ width: `${weakness.confidence * 100}%` }}
                        transition={{ delay: index * 0.1 + 0.5, duration: 1 }}
                      />
                    </div>
                  </div>
                  <button className="mt-4 w-full py-2 bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-400 text-[11px] font-bold rounded-lg transition-colors flex items-center justify-center gap-1 group">
                    Apply Fix <ArrowRight className="h-3 w-3 group-hover:translate-x-1 transition-transform" />
                  </button>
                </div>
              </div>
            </GlassCard>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
