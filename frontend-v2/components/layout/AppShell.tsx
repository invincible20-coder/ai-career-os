"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { ContextPanel } from "./ContextPanel";

interface AppShellProps {
  title: string;
  children: React.ReactNode;
  contextContent?: React.ReactNode;
  showContext?: boolean;
}

export function AppShell({
  title,
  children,
  contextContent,
  showContext = true,
}: AppShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [contextOpen, setContextOpen] = useState(true);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Ambient gradient background */}
      <div className="gradient-mesh fixed inset-0 pointer-events-none z-0" />

      {/* Left sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      {/* Center area */}
      <motion.div
        initial={false}
        animate={{
          marginLeft: sidebarCollapsed ? 68 : 248,
          marginRight: showContext && contextOpen ? 340 : 0,
        }}
        transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
        className="flex-1 flex flex-col min-w-0 relative z-10"
      >
        <TopBar
          title={title}
          contextOpen={contextOpen}
          onToggleContext={() => setContextOpen(!contextOpen)}
          showContextToggle={showContext}
        />

        <main className="flex-1 overflow-y-auto overflow-x-hidden">
          <div className="max-w-[1200px] mx-auto px-6 py-6">
            {children}
          </div>
        </main>
      </motion.div>

      {/* Right context panel */}
      {showContext && (
        <AnimatePresence>
          {contextOpen && (
            <ContextPanel onClose={() => setContextOpen(false)}>
              {contextContent}
            </ContextPanel>
          )}
        </AnimatePresence>
      )}
    </div>
  );
}
