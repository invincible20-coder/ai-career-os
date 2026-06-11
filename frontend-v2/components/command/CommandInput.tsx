"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send } from "lucide-react";
import { GlassInput } from "@/components/glass/GlassInput";
import { cn } from "@/lib/utils";

const PLACEHOLDERS = [
  "I don't know what role fits me…",
  "I like backend systems but I'm confused about my path…",
  "I want a high-paying remote role in engineering…",
  "I enjoy solving problems but hate meetings…",
  "I'm burned out and need a career change…",
  "What roles match my Python and FastAPI skills?",
  "Should I focus on startups or big tech?",
];

interface CommandInputProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
}

export function CommandInput({
  value,
  onChange,
  onSubmit,
  disabled = false,
}: CommandInputProps) {
  const [placeholderIdx, setPlaceholderIdx] = useState(0);
  const [placeholderVisible, setPlaceholderVisible] = useState(true);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Cycle placeholders with fade
  useEffect(() => {
    const interval = setInterval(() => {
      setPlaceholderVisible(false);
      setTimeout(() => {
        setPlaceholderIdx((i) => (i + 1) % PLACEHOLDERS.length);
        setPlaceholderVisible(true);
      }, 300);
    }, 4500);
    return () => clearInterval(interval);
  }, []);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey && !disabled) {
        e.preventDefault();
        onSubmit();
      }
    },
    [disabled, onSubmit]
  );

  return (
    <div className="relative">
      <div className="relative glass-card !rounded-2xl overflow-hidden p-1">
        <div className="relative">
          <GlassInput
            ref={textareaRef}
            variant="large"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            className="!border-0 !shadow-none !bg-transparent min-h-[100px] pr-14"
            style={{
              backdropFilter: "none",
              WebkitBackdropFilter: "none",
            }}
          />

          {/* Animated placeholder overlay */}
          {!value && (
            <div className="absolute top-3 left-4 right-14 pointer-events-none">
              <AnimatePresence mode="wait">
                {placeholderVisible && (
                  <motion.p
                    key={placeholderIdx}
                    initial={{ opacity: 0, y: 4 }}
                    animate={{ opacity: 0.4, y: 0 }}
                    exit={{ opacity: 0, y: -4 }}
                    transition={{ duration: 0.3 }}
                    className="text-base leading-relaxed text-muted-foreground"
                  >
                    {PLACEHOLDERS[placeholderIdx]}
                  </motion.p>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* Submit button */}
          <div className="absolute bottom-3 right-3">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={onSubmit}
              disabled={disabled || !value.trim()}
              className={cn(
                "flex h-10 w-10 items-center justify-center rounded-xl transition-all",
                value.trim()
                  ? "bg-gradient-to-r from-teal-500 to-cyan-600 text-white shadow-lg shadow-teal-500/25"
                  : "text-muted-foreground"
              )}
              style={!value.trim() ? { background: "var(--glass-bg-elevated)" } : {}}
            >
              <Send className="h-4 w-4" />
            </motion.button>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex items-center justify-between px-4 py-2" style={{ borderTop: "1px solid var(--glass-border)" }}>
          <span className="text-[10px] text-muted-foreground">
            No limits — share goals, confusion, or raw thoughts
          </span>
          <span className="text-[10px] text-muted-foreground font-mono">Enter to send · Shift+Enter for new line</span>
        </div>
      </div>
    </div>
  );
}
