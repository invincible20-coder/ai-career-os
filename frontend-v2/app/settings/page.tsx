"use client";

import { AppShell } from "@/components/layout/AppShell";
import { GlassCard } from "@/components/glass/GlassCard";
import { Sun, Moon, Monitor, Check } from "lucide-react";
import { useTheme } from "@/components/theme/ThemeProvider";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

export default function SettingsPage() {
  const { theme, setTheme } = useTheme();

  const themes = [
    { value: "dark" as const, label: "Dark", icon: Moon, desc: "Optimized for low-light environments" },
    { value: "light" as const, label: "Light", icon: Sun, desc: "Clean and bright interface" },
    { value: "system" as const, label: "System", icon: Monitor, desc: "Follows your OS preference" },
  ];

  return (
    <AppShell title="Settings" showContext={false}>
      <div className="space-y-6 max-w-2xl">
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
          <h2 className="text-xl font-bold text-foreground tracking-tight">Settings</h2>
          <p className="text-sm text-muted-foreground">Customize your HuntAI experience</p>
        </motion.div>

        <GlassCard className="p-5">
          <h3 className="text-sm font-semibold text-foreground mb-4">Appearance</h3>
          <div className="grid grid-cols-3 gap-3">
            {themes.map((t) => {
              const Icon = t.icon;
              const active = theme === t.value;
              return (
                <button key={t.value} onClick={() => setTheme(t.value)} className={cn("relative p-4 rounded-xl text-left transition-all", active ? "glass-card-active" : "glass-card")}>
                  {active && <div className="absolute top-3 right-3"><Check className="h-4 w-4 text-primary" /></div>}
                  <Icon className={cn("h-5 w-5 mb-2", active ? "text-primary" : "text-muted-foreground")} />
                  <p className="text-sm font-semibold text-foreground">{t.label}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">{t.desc}</p>
                </button>
              );
            })}
          </div>
        </GlassCard>
      </div>
    </AppShell>
  );
}
