"use client";

import { Badge } from "@/components/ui/badge";
import { useHuntStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Radio } from "lucide-react";

export function TopBar({ title }: { title: string }) {
  const serverState = useHuntStore((s) => s.serverState);
  const huntId = useHuntStore((s) => s.huntId);
  const isPolling = useHuntStore((s) => s.isPolling);

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-white/[0.06] bg-[#0B1020]/80 px-6 backdrop-blur-xl">
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-semibold text-slate-100">{title}</h1>
        {isPolling && (
          <div className="flex items-center gap-1.5">
            <Radio className="h-3 w-3 text-indigo-400 animate-pulse" />
            <span className="text-[11px] font-medium text-indigo-400">Live</span>
          </div>
        )}
      </div>

      <div className="flex items-center gap-2">
        {huntId && (
          <Badge
            variant="outline"
            className="max-w-[200px] truncate border-white/[0.08] bg-white/[0.03] font-mono text-[10px] text-slate-400"
          >
            {huntId}
          </Badge>
        )}
        <Badge
          variant="outline"
          className={cn(
            "text-[10px] font-semibold",
            serverState.tone === "online" &&
              "border-emerald-500/20 bg-emerald-500/10 text-emerald-400",
            serverState.tone === "offline" &&
              "border-red-500/20 bg-red-500/10 text-red-400",
            serverState.tone === "checking" &&
              "border-amber-500/20 bg-amber-500/10 text-amber-400"
          )}
        >
          {serverState.label}
        </Badge>
      </div>
    </header>
  );
}
