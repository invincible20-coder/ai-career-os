"use client";

import { motion } from "framer-motion";
import { Zap } from "lucide-react";
import { useHuntStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export function QuickActions() {
  const presets = useHuntStore((s) => s.presets);
  const applyPreset = useHuntStore((s) => s.applyPreset);
  const startHunt = useHuntStore((s) => s.startHunt);
  const activeAction = useHuntStore((s) => s.activeAction);
  const busy = Boolean(activeAction);

  return (
    <div className="flex items-center gap-2 overflow-x-auto px-1 py-1">
      {presets.map((preset, i) => (
        <motion.button
          key={preset.label}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05 }}
          disabled={busy}
          onClick={() => {
            applyPreset(preset);
            if (preset.data.goal) startHunt(preset.data.goal);
          }}
          className={cn(
            "group flex items-center gap-2 rounded-lg border border-white/[0.06] bg-white/[0.02] px-3 py-2 text-left transition-all hover:border-indigo-500/20 hover:bg-indigo-500/5 disabled:opacity-50",
            "shrink-0"
          )}
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-white/[0.04] group-hover:bg-indigo-500/10 transition-colors">
            <Zap className="h-3.5 w-3.5 text-slate-500 group-hover:text-indigo-400 transition-colors" />
          </div>
          <div>
            <p className="text-xs font-semibold text-slate-300 group-hover:text-slate-100 transition-colors">
              {preset.label}
            </p>
            <p className="text-[10px] text-slate-600">{preset.sublabel}</p>
          </div>
        </motion.button>
      ))}
    </div>
  );
}
