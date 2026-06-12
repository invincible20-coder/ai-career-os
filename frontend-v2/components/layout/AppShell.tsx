"use client";

import { useState } from "react";
import { AnimatePresence } from "framer-motion";
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
  const [contextOpen, setContextOpen] = useState(true);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Ambient gradient background */}
      <div className="gradient-mesh fixed inset-0 pointer-events-none z-0" />

      {/* Center area — shifts width automatically when sidebar toggles */}
      <div
        className="flex-1 flex flex-col min-w-0 relative z-10 transition-[margin] duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]"
        style={{
          marginRight: showContext && contextOpen ? 340 : 0,
        }}
      >
        {/* Floating Top Nav removed from here to prevent duplicate */}

        <TopBar
          title={title}
          contextOpen={contextOpen}
          onToggleContext={() => setContextOpen(!contextOpen)}
          showContextToggle={showContext}
        />

        <main className="flex-1 overflow-y-auto overflow-x-hidden">
          <div className="max-w-[1200px] mx-auto px-6 py-6 pb-24 md:pb-6">
            {children}
          </div>
        </main>
      </div>

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