"use client";

import { motion } from "framer-motion";
import { AppShell } from "@/components/layout/AppShell";
import { Construction } from "lucide-react";

export function StubPage({ title, description, icon: Icon = Construction }: { title: string; description: string; icon?: React.ElementType }) {
  return (
    <AppShell title={title} showContext={false}>
      <div className="flex items-center justify-center min-h-[calc(100vh-12rem)]">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.3 }}
          className="text-center"
        >
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl mb-4" style={{ background: "var(--glass-bg)", border: "1px solid var(--glass-border)" }}>
            <Icon className="h-8 w-8 text-muted-foreground" />
          </div>
          <h2 className="text-lg font-semibold text-foreground">{title}</h2>
          <p className="mt-2 text-sm text-muted-foreground max-w-sm">{description}</p>
          <div className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-[10px] font-semibold text-primary">
            Coming Soon
          </div>
        </motion.div>
      </div>
    </AppShell>
  );
}
