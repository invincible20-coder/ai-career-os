"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  Command,
  Briefcase,
  FileText,
  BarChart3,
  Compass,
  User,
  Lightbulb,
  ChevronLeft,
  ChevronRight,
  Zap,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useHuntStore } from "@/lib/store";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  phase: string;
}

const NAV_ITEMS: NavItem[] = [
  { label: "Command Center", href: "/", icon: Command, phase: "1" },
  { label: "Job Results", href: "/jobs", icon: Briefcase, phase: "2" },
  { label: "Applications", href: "/applications", icon: FileText, phase: "2" },
  { label: "Workspace", href: "/workspace", icon: Lightbulb, phase: "2" },
  { label: "Analytics", href: "/analytics", icon: BarChart3, phase: "3" },
  { label: "Strategy", href: "/strategy", icon: Compass, phase: "3" },
  { label: "Profile", href: "/profile", icon: User, phase: "3" },
];

export function Sidebar() {
  const pathname = usePathname();
  const collapsed = useHuntStore((s) => s.sidebarCollapsed);
  const setCollapsed = useHuntStore((s) => s.setSidebarCollapsed);
  const serverState = useHuntStore((s) => s.serverState);

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.2, ease: "easeInOut" }}
      className="fixed left-0 top-0 z-40 flex h-screen flex-col border-r border-white/[0.06] bg-[#0B1020]"
    >
      {/* Logo */}
      <div className="flex h-14 items-center gap-3 border-b border-white/[0.06] px-4">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-500/10 border border-indigo-500/20">
          <Zap className="h-4 w-4 text-indigo-400" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.15 }}
              className="min-w-0"
            >
              <p className="truncate text-sm font-semibold text-slate-100">
                HuntAI
              </p>
              <p className="truncate text-[10px] font-medium text-slate-500">
                Career OS
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-3">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "group relative flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors duration-150",
                isActive
                  ? "bg-indigo-500/10 text-indigo-300"
                  : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="sidebar-active"
                  className="absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-r-full bg-indigo-400"
                  transition={{ type: "spring", stiffness: 400, damping: 30 }}
                />
              )}
              <Icon className={cn("h-[18px] w-[18px] shrink-0", isActive ? "text-indigo-400" : "text-slate-500 group-hover:text-slate-300")} />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className="truncate"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-white/[0.06] px-2 py-3">
        {/* Server status */}
        <div className={cn(
          "flex items-center gap-3 rounded-lg px-3 py-2",
          !collapsed && "mb-2"
        )}>
          <div className={cn(
            "h-2 w-2 shrink-0 rounded-full",
            serverState.tone === "online" && "bg-emerald-400 shadow-[0_0_8px_rgba(16,185,129,0.4)]",
            serverState.tone === "offline" && "bg-red-400 shadow-[0_0_8px_rgba(239,68,68,0.4)]",
            serverState.tone === "checking" && "bg-amber-400 animate-pulse"
          )} />
          <AnimatePresence>
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="truncate text-xs text-slate-500"
              >
                {serverState.tone === "online" ? "Backend Live" : serverState.tone === "offline" ? "Backend Offline" : "Connecting..."}
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="flex w-full items-center justify-center rounded-lg py-2 text-slate-500 transition-colors hover:bg-white/[0.04] hover:text-slate-300"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </button>
      </div>
    </motion.aside>
  );
}
