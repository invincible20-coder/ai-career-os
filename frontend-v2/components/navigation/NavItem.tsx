"use client";

import React, { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { 
  LayoutGrid, 
  Compass, 
  Terminal, 
  FolderGit2, 
  Users2, 
  Search, 
  Settings, 
  User,
  Zap 
} from "lucide-react";

// --- NavItem Component (Your original code optimized) ---
interface NavItemProps {
  label: string;
  href: string;
  icon: React.ElementType;
  isActive: boolean;
  onClick: () => void;
}

export function NavItem({ label, href, icon: Icon, isActive, onClick }: NavItemProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "relative flex items-center justify-center rounded-full transition-colors duration-200 group",
        "w-9 h-9",
        isActive ? "text-foreground" : "text-muted-foreground hover:text-foreground"
      )}
      title={label}
    >
      {isActive && (
        <motion.div
          layoutId="floating-nav-active"
          className="absolute inset-0 rounded-full"
          style={{
            background: "rgba(20,184,166,0.08)",
            boxShadow: "0 0 20px -4px rgba(20,184,166,0.12), inset 0 1px 0 0 rgba(255,255,255,0.04)",
            border: "1px solid rgba(20,184,166,0.12)",
          }}
          transition={{ type: "spring", stiffness: 400, damping: 30 }}
        />
      )}

      <motion.div
        className="relative z-10"
        whileHover={{ y: -1, scale: 1.1 }}
        transition={{ type: "spring", stiffness: 500, damping: 25 }}
      >
        <Icon
          className={cn(
            "h-[15px] w-[15px] transition-colors duration-200",
            isActive ? "text-primary" : "text-muted-foreground group-hover:text-foreground"
          )}
        />
      </motion.div>

      {!isActive && (
        <motion.div
          className="absolute inset-0 rounded-full opacity-0 group-hover:opacity-100 transition-opacity duration-300"
          style={{
            background: "rgba(255,255,255,0.03)",
            boxShadow: "inset 0 1px 0 0 rgba(255,255,255,0.04)",
          }}
        />
      )}
    </button>
  );
}

// --- Main Complete Navbar Layout ---
export default function Navbar() {
  const [activeTab, setActiveTab] = useState("home");

  const navItems = [
    { id: "home", label: "Dashboard", href: "#", icon: LayoutGrid },
    { id: "explore", label: "Explore", href: "#", icon: Compass },
    { id: "terminal", label: "Terminal", href: "#", icon: Terminal },
    { id: "projects", label: "Projects", href: "#", icon: FolderGit2 },
    { id: "network", label: "Network", href: "#", icon: Users2 },
  ];

  return (
    <header className="relative w-full h-16 bg-[#060b13] border-b border-slate-900 px-6 flex items-center justify-between z-50">
      
      {/* LEFT SECTION: Placeholder space to balance the screen layout */}
      <div className="flex items-center w-1/4">
        {/* Left-side branding or page title if needed */}
      </div>

      {/* CENTER SECTION: The Perfectly Centered Command Bar Dock */}
      <div className="absolute left-1/2 -translate-x-1/2 flex items-center bg-[#0d1527]/80 backdrop-blur-md border border-slate-800/60 rounded-full pl-2 pr-3 py-1 gap-3 max-w-2xl shadow-xl shadow-black/40">
        
        {/* HuntAI Badge */}
        <Link href="/" className="flex items-center gap-1.5 bg-[#00f2fe]/10 text-[#00f2fe] px-3 py-1 rounded-full text-xs font-semibold tracking-wide border border-[#00f2fe]/20 hover:bg-[#00f2fe]/20 transition-all">
          <Zap className="h-3.5 w-3.5 fill-current" />
          <span>HuntAI</span>
        </Link>

        {/* Divider */}
        <div className="h-4 w-[1px] bg-slate-800" />

        {/* Navigation Map Items (Strict non-overlapping Flex layout) */}
        <nav className="flex items-center space-x-1">
          {navItems.map((item) => (
            <NavItem
              key={item.id}
              label={item.label}
              href={item.href}
              icon={item.icon}
              isActive={activeTab === item.id}
              onClick={() => setActiveTab(item.id)}
            />
          ))}
        </nav>

        {/* Divider */}
        <div className="h-4 w-[1px] bg-slate-800" />

        {/* Search Bar - Fixed layout ensures text and icon never overlap */}
        <div className="relative flex items-center bg-slate-950/60 border border-slate-800/80 rounded-full px-2.5 py-1 w-44 focus-within:w-52 focus-within:border-teal-500/50 transition-all duration-300">
          <Search className="h-3.5 w-3.5 text-muted-foreground mr-1.5 shrink-0" />
          <input
            type="text"
            placeholder="Search..."
            className="bg-transparent text-xs text-slate-200 outline-none w-full placeholder:text-slate-500"
          />
          <kbd className="hidden sm:inline-flex h-4 select-none items-center gap-0.5 rounded border border-slate-800 bg-slate-900 px-1.5 font-mono text-[9px] font-medium text-slate-500 opacity-100 shrink-0">
            <span>⌘</span>Q
          </kbd>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-1">
          <button className="p-1.5 text-muted-foreground hover:text-foreground rounded-full hover:bg-slate-800/40 transition-colors">
            <Settings className="h-[15px] w-[15px]" />
          </button>
          <button className="p-1.5 text-muted-foreground hover:text-foreground rounded-full hover:bg-slate-800/40 transition-colors">
            <User className="h-[15px] w-[15px]" />
          </button>
        </div>
      </div>

      {/* RIGHT SECTION: AI Status indicator */}
      <div className="flex items-center justify-end w-1/4">
        <div className="flex items-center gap-2 text-[11px] font-medium text-teal-400 bg-teal-500/10 px-3 py-1 rounded-full border border-teal-500/20 shadow-[0_0_15px_rgba(20,184,166,0.1)]">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-teal-500"></span>
          </span>
          AI ACTIVE
        </div>
      </div>

    </header>
  );
}