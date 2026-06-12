"use client";

import { useCallback, useRef } from "react";
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
  Zap,
} from "lucide-react";
import { useNavVisibility } from "./hooks/useNavVisibility";
import { NavItem } from "./NavItem";
import { NavGlow } from "./NavGlow";
import { AIStatusIndicator } from "./AIStatusIndicator";
import { MobileNavDock } from "./MobileNavDock";

interface NavItemData {
  label: string;
  href: string;
  icon: React.ElementType;
}

const NAV_ITEMS: NavItemData[] = [
  { label: "Command", href: "/", icon: Command },
  { label: "Chat", href: "/chat", icon: MessageSquare },
  { label: "Jobs", href: "/jobs", icon: Briefcase },
  { label: "Applications", href: "/applications", icon: FileText },
  { label: "Resume Lab", href: "/resume-lab", icon: FlaskConical },
  { label: "Analytics", href: "/analytics", icon: BarChart3 },
  { label: "Strategy", href: "/strategy", icon: Compass },
  { label: "Profile", href: "/profile", icon: User },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function FloatingTopNav() {
  const pathname = usePathname();
  const { isVisible } = useNavVisibility();
  const navRef = useRef<HTMLDivElement>(null);

  const handleMouseEnter = useCallback(() => {
    const setter = (window as unknown as Record<string, unknown>)
      .__setNavHovering as ((v: boolean) => void) | undefined;
    setter?.(true);
  }, []);

  const handleMouseLeave = useCallback(() => {
    const setter = (window as unknown as Record<string, unknown>)
      .__setNavHovering as ((v: boolean) => void) | undefined;
    setter?.(false);
  }, []);

  return (
    <>
      {/* ── Ambient top-edge glow ── */}
      <div
        className="absolute top-0 inset-x-0 h-[2px] z-[60] pointer-events-none"
        style={{
          background:
            "linear-gradient(90deg, transparent 20%, rgba(20,184,166,0.06) 50%, transparent 80%)",
        }}
      />

      {/* ── Desktop / Tablet floating nav ── */}
      <AnimatePresence>
        {isVisible && (
          <motion.nav
            ref={navRef}
            initial={{ y: -80, opacity: 0, filter: "blur(8px)" }}
            animate={{
              y: 0,
              opacity: 1,
              filter: "blur(0px)",
            }}
            exit={{
              y: -60,
              opacity: 0,
              filter: "blur(4px)",
            }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 28,
              mass: 0.8,
            }}
            onMouseEnter={handleMouseEnter}
            onMouseLeave={handleMouseLeave}
            /* 
              🌟 FIXED LAYOUT CLASS: Changed from 'absolute top-3 z-[55]' to 'relative'.
              This drops any manual offsets so it aligns perfectly to the parent container center!
            */
            className="relative hidden md:flex items-center"
          >
            {/* ── Glass capsule container ── */}
            <motion.div
              className="relative flex items-center gap-0.5 px-2 py-1.5 rounded-full floating-nav-glass"
              whileHover={{
                boxShadow:
                  "0 8px 40px -8px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.08), 0 0 30px -5px rgba(20,184,166,0.10)",
              }}
              transition={{ duration: 0.3 }}
            >
              {/* Glow layer */}
              <NavGlow />

              {/* Logo */}
              <div className="relative z-10 flex items-center gap-2 pr-2 mr-1 border-r border-white/[0.06]">
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-teal-500 to-cyan-500 shadow-lg shadow-teal-500/20">
                  <Zap className="h-3.5 w-3.5 text-white" />
                </div>
                <span className="hidden xl:block text-[11px] font-bold text-foreground tracking-tight">
                  HuntAI
                </span>
              </div>

              {/* Navigation items */}
              {NAV_ITEMS.map((item) => (
                <NavItem
                  key={item.href}
                  {...item}
                  isActive={pathname === item.href}
                />
              ))}

              {/* AI Status */}
              <AIStatusIndicator />
            </motion.div>
          </motion.nav>
        )}
      </AnimatePresence>

      {/* ── Mobile bottom dock ── */}
      <MobileNavDock items={NAV_ITEMS} currentPath={pathname} />
    </>
  );
}