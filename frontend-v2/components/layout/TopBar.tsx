"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Sun, Moon, Monitor, PanelRightOpen, PanelRightClose, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { useTheme } from "@/components/theme/ThemeProvider";

interface TopBarProps {
  title: string;
  contextOpen?: boolean;
  onToggleContext?: () => void;
  showContextToggle?: boolean;
}

const THEME_ICONS = {
  dark: Moon,
  light: Sun,
  system: Monitor,
} as const;

const THEME_CYCLE: Array<"dark" | "light" | "system"> = ["dark", "light", "system"];

export function TopBar({
  title,
  contextOpen = true,
  onToggleContext,
  showContextToggle = true,
}: TopBarProps) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  const cycleTheme = () => {
    const idx = THEME_CYCLE.indexOf(theme);
    const next = THEME_CYCLE[(idx + 1) % THEME_CYCLE.length];
    setTheme(next);
  };

  // Use a stable fallback before mount to avoid hydration mismatch
  const ThemeIcon = mounted ? THEME_ICONS[theme] : Monitor;
  const themeLabel = mounted ? `Theme: ${theme}` : "Theme";

  return (
    <header
      className="sticky top-0 z-30 flex h-14 items-center justify-between px-6 glass-panel-elevated"
      style={{
        borderBottom: "1px solid var(--glass-border)",
        borderRadius: 0,
      }}
    >
      <div className="flex items-center gap-4">
        <h1 className="text-sm font-semibold text-foreground">{title}</h1>
      </div>

      <div className="flex items-center gap-1.5">
        {/* Search trigger */}
        <button
          className="flex h-8 items-center gap-2 rounded-lg px-3 text-xs text-muted-foreground transition-all hover:text-foreground"
          style={{ background: "var(--glass-bg)" }}
        >
          <Search className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Search</span>
          <kbd className="hidden sm:inline-flex h-5 items-center rounded border px-1.5 font-mono text-[10px] text-muted-foreground" style={{ borderColor: "var(--glass-border)" }}>
            ⌘K
          </kbd>
        </button>

        {/* Theme toggle */}
        <button
          onClick={cycleTheme}
          className="flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-all hover:text-foreground"
          style={{ background: "var(--glass-bg)" }}
          title={themeLabel}
          suppressHydrationWarning
        >
          <motion.div
            key={mounted ? theme : "initial"}
            initial={{ rotate: -30, opacity: 0, scale: 0.8 }}
            animate={{ rotate: 0, opacity: 1, scale: 1 }}
            exit={{ rotate: 30, opacity: 0, scale: 0.8 }}
            transition={{ duration: 0.1 }}
          >
            <ThemeIcon className="h-3.5 w-3.5" />
          </motion.div>
        </button>

        {/* Context panel toggle */}
        {showContextToggle && onToggleContext && (
          <button
            onClick={onToggleContext}
            className={cn(
              "flex h-8 w-8 items-center justify-center rounded-lg text-muted-foreground transition-all hover:text-foreground",
            )}
            style={{ background: contextOpen ? "var(--sidebar-accent)" : "var(--glass-bg)" }}
            title={contextOpen ? "Hide intelligence panel" : "Show intelligence panel"}
          >
            {contextOpen ? (
              <PanelRightClose className="h-3.5 w-3.5" />
            ) : (
              <PanelRightOpen className="h-3.5 w-3.5" />
            )}
          </button>
        )}
      </div>
    </header>
  );
}
