"use client";

import { useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  MoreHorizontal,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface NavItemData {
  label: string;
  href: string;
  icon: React.ElementType;
}

interface MobileNavDockProps {
  items: NavItemData[];
  currentPath: string;
}

// Show first 4 items + "more" button on mobile
const VISIBLE_COUNT = 4;

/**
 * Bottom dock for mobile viewports (< 768px).
 * Shows top nav items as icons with an overflow menu.
 * Apple-style spring animations.
 */
export function MobileNavDock({ items, currentPath }: MobileNavDockProps) {
  const [expanded, setExpanded] = useState(false);
  const visibleItems = items.slice(0, VISIBLE_COUNT);
  const overflowItems = items.slice(VISIBLE_COUNT);

  return (
    <>
      {/* Overflow sheet */}
      <AnimatePresence>
        {expanded && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-[70] bg-black/40 backdrop-blur-sm md:hidden"
              onClick={() => setExpanded(false)}
            />

            {/* Sheet */}
            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", stiffness: 400, damping: 35 }}
              className="fixed bottom-0 inset-x-0 z-[75] md:hidden"
            >
              <div
                className="mx-3 mb-20 rounded-2xl p-4 space-y-1"
                style={{
                  background: "rgba(5,8,22,0.92)",
                  backdropFilter: "blur(40px)",
                  WebkitBackdropFilter: "blur(40px)",
                  border: "1px solid rgba(255,255,255,0.06)",
                  boxShadow: "0 -8px 40px -8px rgba(0,0,0,0.6)",
                }}
              >
                <div className="flex items-center justify-between mb-3 px-1">
                  <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-muted-foreground">
                    More
                  </span>
                  <button
                    onClick={() => setExpanded(false)}
                    className="flex h-6 w-6 items-center justify-center rounded-full text-muted-foreground hover:text-foreground transition-colors"
                    style={{ background: "rgba(255,255,255,0.05)" }}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>

                {overflowItems.map((item, i) => {
                  const Icon = item.icon;
                  const isActive = currentPath === item.href;
                  return (
                    <motion.div
                      key={item.href}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.04 }}
                    >
                      <Link
                        href={item.href}
                        onClick={() => setExpanded(false)}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all",
                          isActive
                            ? "text-primary bg-primary/10"
                            : "text-muted-foreground hover:text-foreground hover:bg-white/[0.03]"
                        )}
                      >
                        <Icon className="h-4 w-4" />
                        <span>{item.label}</span>
                      </Link>
                    </motion.div>
                  );
                })}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Bottom dock bar */}
      <div className="fixed bottom-0 inset-x-0 z-[65] md:hidden">
        <div className="px-4 pb-[env(safe-area-inset-bottom,8px)] pt-1">
          <div
            className="flex items-center justify-around rounded-2xl px-2 py-2"
            style={{
              background: "rgba(5,8,22,0.88)",
              backdropFilter: "blur(40px)",
              WebkitBackdropFilter: "blur(40px)",
              border: "1px solid rgba(255,255,255,0.06)",
              boxShadow:
                "0 -4px 24px -4px rgba(0,0,0,0.5), inset 0 1px 0 0 rgba(255,255,255,0.03)",
            }}
          >
            {visibleItems.map((item) => {
              const Icon = item.icon;
              const isActive = currentPath === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className="relative flex flex-col items-center gap-0.5 px-3 py-1.5"
                >
                  {isActive && (
                    <motion.div
                      layoutId="mobile-nav-active"
                      className="absolute inset-0 rounded-xl"
                      style={{
                        background: "rgba(20,184,166,0.08)",
                        border: "1px solid rgba(20,184,166,0.10)",
                      }}
                      transition={{
                        type: "spring",
                        stiffness: 400,
                        damping: 30,
                      }}
                    />
                  )}
                  <Icon
                    className={cn(
                      "h-5 w-5 relative z-10 transition-colors",
                      isActive ? "text-primary" : "text-muted-foreground"
                    )}
                  />
                  <span
                    className={cn(
                      "text-[9px] font-medium relative z-10 transition-colors",
                      isActive ? "text-primary" : "text-muted-foreground"
                    )}
                  >
                    {item.label}
                  </span>
                </Link>
              );
            })}

            {/* More button */}
            <button
              onClick={() => setExpanded(true)}
              className="relative flex flex-col items-center gap-0.5 px-3 py-1.5"
            >
              <MoreHorizontal
                className={cn(
                  "h-5 w-5 transition-colors",
                  expanded ? "text-primary" : "text-muted-foreground"
                )}
              />
              <span className="text-[9px] font-medium text-muted-foreground">
                More
              </span>
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
