"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AlertCircle, RefreshCw, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useHuntStore } from "@/lib/store";
import type { ErrorDetail } from "@/lib/types";

export function ErrorPanel() {
  const errorMessage = useHuntStore((s) => s.errorMessage);
  const pollError = useHuntStore((s) => s.pollError);
  const huntResult = useHuntStore((s) => s.huntResult);
  const huntId = useHuntStore((s) => s.huntId);
  const refreshHunt = useHuntStore((s) => s.refreshHunt);
  const clearError = useHuntStore((s) => s.clearError);

  const backendErrors: ErrorDetail[] = huntResult?.errors ?? [];
  const hasError = errorMessage || pollError || backendErrors.length > 0;

  return (
    <AnimatePresence>
      {hasError && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          transition={{ duration: 0.2 }}
          className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-2xl rounded-xl border border-red-500/20 bg-red-950/80 px-5 py-4 shadow-2xl backdrop-blur-xl"
        >
          <div className="flex items-start gap-3">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-red-500/10 border border-red-500/20">
              <AlertCircle className="h-4 w-4 text-red-400" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-red-300">Attention Required</p>
              <div className="mt-1 space-y-1">
                {errorMessage && <p className="text-xs text-red-200/80 break-words">{errorMessage}</p>}
                {pollError && <p className="text-xs text-red-200/80 break-words">{pollError}</p>}
                {backendErrors.map((e) => (
                  <p key={`${e.code}-${e.step}-${e.message}`} className="text-xs text-red-200/80 break-words">
                    <span className="font-mono font-semibold text-red-300">{e.code}</span>
                    {e.step ? ` at ${e.step}: ` : " "}
                    {e.message}
                  </p>
                ))}
              </div>
            </div>
            <div className="flex gap-1.5 shrink-0">
              {huntId && (
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => refreshHunt()}
                  className="h-7 gap-1 text-[10px] text-red-300 hover:bg-red-500/10"
                >
                  <RefreshCw className="h-3 w-3" />
                  Retry
                </Button>
              )}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => clearError()}
                className="h-7 text-[10px] text-red-400 hover:bg-red-500/10"
              >
                <XCircle className="h-3 w-3" />
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
