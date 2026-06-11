"use client";

import { useState, useEffect, useCallback, useRef } from "react";

/**
 * Detects when the cursor enters a zone near the top of the viewport.
 * Uses a debounce to prevent flicker on rapid mouse movement.
 */
export function useCursorZone(threshold = 80): boolean {
  const [inZone, setInZone] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleMouseMove = useCallback(
    (e: MouseEvent) => {
      const isInZone = e.clientY < threshold;

      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }

      if (isInZone) {
        // Enter zone immediately for responsiveness
        setInZone(true);
      } else {
        // Leave zone with slight delay to prevent flicker
        timerRef.current = setTimeout(() => {
          setInZone(false);
        }, 150);
      }
    },
    [threshold]
  );

  // Also detect when cursor leaves the window entirely
  const handleMouseLeave = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setInZone(false), 300);
  }, []);

  useEffect(() => {
    document.addEventListener("mousemove", handleMouseMove, { passive: true });
    document.addEventListener("mouseleave", handleMouseLeave);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseleave", handleMouseLeave);
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [handleMouseMove, handleMouseLeave]);

  return inZone;
}
