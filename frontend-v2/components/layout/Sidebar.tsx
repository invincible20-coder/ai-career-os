"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Command,
  MessageSquare,
  Briefcase,
  FileText,
  FlaskConical,
  BarChart3,
  Compass,
  User,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Command Center", href: "/", icon: Command },
  { label: "Chat", href: "/chat", icon: MessageSquare },
  { label: "Jobs", href: "/jobs", icon: Briefcase },
  { label: "Applications", href: "/applications", icon: FileText },
  { label: "Resume Lab", href: "/resume-lab", icon: FlaskConical },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Strategy", href: "/strategy", icon: Compass },
  { label: "Profile", href: "/profile", icon: User },
  { label: "Settings", href: "/settings", icon: Settings },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 68 : 248 }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      className="fixed left-0 top-0 z-40 flex h-screen flex-col glass-panel-elevated border-r-0"
      style={{ borderRight: "1px solid var(--glass-border)" }}
    >
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 px-4" style={{ borderBottom: "1px solid var(--glass-border)" }}>
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 shadow-lg shadow-indigo-500/20">
          <Zap className="h-4.5 w-4.5 text-white" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.2 }}
              className="min-w-0"
            >
              <p className="truncate text-sm font-bold text-foreground tracking-tight">
                HuntAI
              </p>
              <p className="truncate text-[10px] font-medium text-muted-foreground">
                Career Operating System
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* AI Status Orb */}
      <div className="flex items-center gap-3 px-5 py-3" style={{ borderBottom: "1px solid var(--glass-border)" }}>
        <div className="relative">
          <div className="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-orb-breathe" />
          <div className="absolute inset-0 h-2.5 w-2.5 rounded-full bg-emerald-400/30 animate-ping" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col"
            >
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
                AI System
              </span>
              <span className="text-[11px] font-medium text-emerald-400">
                Active · Listening
              </span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-200",
                isActive
                  ? "text-primary"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute inset-0 rounded-xl"
                  style={{
                    background: "var(--sidebar-accent)",
                    borderLeft: "2px solid var(--primary)",
                  }}
                  transition={{ type: "spring", stiffness: 350, damping: 30 }}
                />
              )}
              <Icon
                className={cn(
                  "h-[18px] w-[18px] shrink-0 relative z-10 transition-colors",
                  isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
                )}
              />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className="truncate relative z-10"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );
        })}
      </nav>

      {/* Learning Progress */}
      {!collapsed && (
        <div className="px-4 py-3" style={{ borderTop: "1px solid var(--glass-border)" }}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
              AI Learning
            </span>
            <span className="text-[10px] font-bold text-primary">34%</span>
          </div>
          <div className="h-1 rounded-full overflow-hidden" style={{ background: "var(--glass-bg-elevated)" }}>
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-violet-500"
              initial={{ width: 0 }}
              animate={{ width: "34%" }}
              transition={{ duration: 1, ease: "easeOut", delay: 0.5 }}
            />
          </div>
        </div>
      )}

      {/* User + Collapse */}
      <div className="px-2 py-3" style={{ borderTop: "1px solid var(--glass-border)" }}>
        {/* User Identity */}
        <div className={cn("flex items-center gap-3 rounded-xl px-3 py-2 mb-1", !collapsed && "")}>
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500/20 to-indigo-500/20 text-xs font-bold text-primary">
            S
          </div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="min-w-0"
              >
                <p className="truncate text-xs font-semibold text-foreground">Swaransh</p>
                <p className="truncate text-[10px] text-muted-foreground">Explorer</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={onToggle}
          className="flex w-full items-center justify-center rounded-xl py-2 text-muted-foreground transition-all hover:text-foreground"
          style={{ background: "var(--glass-bg)" }}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>
      </div>
    </motion.aside>
  );
}
