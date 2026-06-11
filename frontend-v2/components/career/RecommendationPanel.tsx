"use client";

import { motion } from "framer-motion";
import { Sparkles, ArrowRight } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { useHuntStore } from "@/lib/store";
import { EmptyState } from "@/components/shared/EmptyState";

function getGradient(index: number): string {
  const gradients = [
    "from-teal-500/10 to-cyan-500/10",
    "from-cyan-500/10 to-cyan-500/10",
    "from-cyan-500/10 to-emerald-500/10",
  ];
  return gradients[index % gradients.length];
}

export function RecommendationPanel() {
  const careerResult = useHuntStore((s) => s.careerResult);
  const activeAction = useHuntStore((s) => s.activeAction);
  const applyRoleAndStart = useHuntStore((s) => s.applyRoleAndStart);
  const busy = Boolean(activeAction);

  const roles = careerResult?.recommended_roles ?? [];

  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#111827] overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-white/[0.04]">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-cyan-400" />
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">
              AI Recommendations
            </p>
            <h2 className="text-sm font-semibold text-slate-200 mt-0.5">
              Career Vectors
            </h2>
          </div>
        </div>
        {roles.length > 0 && (
          <Badge variant="outline" className="border-cyan-500/20 bg-cyan-500/10 text-[10px] text-cyan-400">
            {roles.length} roles
          </Badge>
        )}
      </div>

      {/* Content */}
      <div className="p-4 space-y-2 max-h-[340px] overflow-y-auto">
        {roles.length > 0 ? (
          roles.map((role, i) => (
            <motion.div
              key={role.role}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className={cn(
                "rounded-lg border border-white/[0.06] bg-gradient-to-br p-4 transition-all hover:border-white/[0.1]",
                getGradient(i)
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-slate-200">{role.role}</p>
                  <p className="text-xs text-slate-400 mt-1 leading-relaxed">{role.reason}</p>
                </div>
                <Button
                  size="sm"
                  disabled={busy}
                  onClick={() => applyRoleAndStart(role.role)}
                  className="shrink-0 h-7 gap-1 rounded-md bg-white/[0.06] text-[10px] text-slate-300 hover:bg-white/[0.1] border border-white/[0.08]"
                >
                  Use
                  <ArrowRight className="h-3 w-3" />
                </Button>
              </div>

              {role.required_skills && role.required_skills.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-3">
                  {role.required_skills.slice(0, 5).map((skill) => (
                    <span
                      key={skill}
                      className="rounded-md border border-white/[0.06] bg-white/[0.03] px-1.5 py-0.5 text-[10px] text-slate-400"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              )}
            </motion.div>
          ))
        ) : (
          <EmptyState
            variant="idle"
            className="border-0 bg-transparent py-4"
          />
        )}
      </div>
    </div>
  );
}
