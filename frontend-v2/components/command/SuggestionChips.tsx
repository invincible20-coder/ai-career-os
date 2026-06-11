"use client";

import { motion } from "framer-motion";
import {
  Server,
  Boxes,
  Database,
  Compass,
  Globe,
  FileText,
  GraduationCap,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface Chip {
  label: string;
  icon: React.ElementType;
  gradient: string;
}

const CHIPS: Chip[] = [
  { label: "Backend Roles", icon: Server, gradient: "from-teal-500/20 to-teal-500/5" },
  { label: "Product Engineering", icon: Boxes, gradient: "from-cyan-500/20 to-cyan-500/5" },
  { label: "Data Systems", icon: Database, gradient: "from-cyan-500/20 to-cyan-500/5" },
  { label: "Career Discovery", icon: Compass, gradient: "from-emerald-500/20 to-emerald-500/5" },
  { label: "Remote Jobs", icon: Globe, gradient: "from-amber-500/20 to-amber-500/5" },
  { label: "Resume Improvement", icon: FileText, gradient: "from-rose-500/20 to-rose-500/5" },
  { label: "Internship Exploration", icon: GraduationCap, gradient: "from-teal-500/20 to-teal-500/5" },
];

interface SuggestionChipsProps {
  onSelect: (label: string) => void;
}

export function SuggestionChips({ onSelect }: SuggestionChipsProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 px-1">
        <Compass className="h-3 w-3 text-muted-foreground" />
        <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
          AI Capabilities
        </span>
      </div>
      <div className="flex flex-wrap gap-2">
        {CHIPS.map((chip, i) => {
          const Icon = chip.icon;
          return (
            <motion.button
              key={chip.label}
              initial={{ opacity: 0, y: 8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{ delay: i * 0.05, duration: 0.3 }}
              whileHover={{ scale: 1.04, y: -1 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => onSelect(chip.label)}
              className={cn(
                "group flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-medium text-foreground transition-all glass-card !rounded-xl"
              )}
            >
              <div
                className={cn(
                  "flex h-6 w-6 items-center justify-center rounded-lg bg-gradient-to-br",
                  chip.gradient
                )}
              >
                <Icon className="h-3 w-3 text-foreground/70" />
              </div>
              {chip.label}
            </motion.button>
          );
        })}
      </div>
    </div>
  );
}
