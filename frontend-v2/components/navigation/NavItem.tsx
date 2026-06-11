"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface NavItemProps {
  label: string;
  href: string;
  icon: React.ElementType;
  isActive: boolean;
}

/**
 * Individual navigation item with magnetic hover interactions.
 * Uses Framer Motion shared layout for buttery smooth
 * active indicator transitions between tabs.
 *
 * Icons-only on medium/large screens. Labels appear on xl+ (1280px).
 */
export function NavItem({ label, href, icon: Icon, isActive }: NavItemProps) {
  return (
    <Link
      href={href}
      className={cn(
        "relative flex items-center justify-center rounded-full transition-colors duration-200 group",
        "w-9 h-9",
        isActive
          ? "text-foreground"
          : "text-muted-foreground hover:text-foreground"
      )}
      title={label}
    >
      {/* Active background indicator — shared layout animation */}
      {isActive && (
        <motion.div
          layoutId="floating-nav-active"
          className="absolute inset-0 rounded-full"
          style={{
            background: "rgba(20,184,166,0.08)",
            boxShadow:
              "0 0 20px -4px rgba(20,184,166,0.12), inset 0 1px 0 0 rgba(255,255,255,0.04)",
            border: "1px solid rgba(20,184,166,0.12)",
          }}
          transition={{
            type: "spring",
            stiffness: 400,
            damping: 30,
          }}
        />
      )}

      {/* Icon with hover animation */}
      <motion.div
        className="relative z-10"
        whileHover={{ y: -1, scale: 1.1 }}
        transition={{ type: "spring", stiffness: 500, damping: 25 }}
      >
        <Icon
          className={cn(
            "h-[15px] w-[15px] transition-colors duration-200",
            isActive
              ? "text-primary"
              : "text-muted-foreground group-hover:text-foreground"
          )}
        />
      </motion.div>

      {/* Label removed for premium compact spatial menubar feel. Native title attribute provides tooltip. */}

      {/* Hover glow effect (non-active items) */}
      {!isActive && (
        <motion.div
          className="absolute inset-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          style={{
            background: "rgba(255,255,255,0.03)",
            boxShadow: "inset 0 1px 0 0 rgba(255,255,255,0.04)",
          }}
        />
      )}
    </Link>
  );
}
