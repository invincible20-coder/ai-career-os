"use client";

import { cn } from "@/lib/utils";

export function SkeletonCard({ className, lines = 3 }: { className?: string; lines?: number }) {
  return (
    <div className={cn("rounded-xl border border-white/[0.06] bg-white/[0.02] p-4 space-y-3", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className="h-3 rounded-md animate-shimmer"
          style={{ width: `${85 - i * 15}%` }}
        />
      ))}
    </div>
  );
}

export function SkeletonMetric({ className }: { className?: string }) {
  return (
    <div className={cn("rounded-xl border border-white/[0.06] bg-white/[0.02] p-4", className)}>
      <div className="h-2.5 w-16 rounded animate-shimmer" />
      <div className="mt-3 h-6 w-12 rounded animate-shimmer" />
    </div>
  );
}
