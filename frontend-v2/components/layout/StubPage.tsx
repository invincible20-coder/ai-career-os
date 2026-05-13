"use client";

import { motion } from "framer-motion";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { useHuntStore } from "@/lib/store";
import { Construction } from "lucide-react";

export function StubPage({ title, description, icon: Icon = Construction }: { title: string; description: string; icon?: React.ElementType }) {
  const sidebarCollapsed = useHuntStore((s) => s.sidebarCollapsed);

  return (
    <div className="flex min-h-screen bg-[#0B1020]">
      <Sidebar />
      <motion.main
        initial={false}
        animate={{ marginLeft: sidebarCollapsed ? 64 : 240 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="flex-1 min-w-0"
      >
        <TopBar title={title} />
        <div className="flex items-center justify-center min-h-[calc(100vh-56px)]">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className="text-center"
          >
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl border border-white/[0.06] bg-white/[0.03] mb-4">
              <Icon className="h-8 w-8 text-slate-500" />
            </div>
            <h2 className="text-lg font-semibold text-slate-200">{title}</h2>
            <p className="mt-2 text-sm text-slate-500 max-w-sm">{description}</p>
            <div className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-indigo-500/20 bg-indigo-500/10 px-3 py-1 text-[10px] font-semibold text-indigo-400">
              Coming Soon
            </div>
          </motion.div>
        </div>
      </motion.main>
    </div>
  );
}
