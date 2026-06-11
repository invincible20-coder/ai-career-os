"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useCursorZone } from "./useCursorZone";
import { useScrollDirection } from "./useScrollDirection";

export type NavTrigger = "cursor" | "scroll" | "focus" | "top" | "none";

interface NavVisibility {
  isVisible: boolean;
  trigger: NavTrigger;
}

const IDLE_TIMEOUT = 2500; // ms before auto-hide
const SCROLL_VELOCITY_THRESHOLD = 8; // px/frame for "aggressive" upward scroll
const INITIAL_SUPPRESS_MS = 800; // suppress all triggers for this long after mount

/**
 * Composite hook: combines cursor zone, scroll direction, and tab focus
 * to intelligently determine when the floating nav should be visible.
 *
 * Suppresses triggers for the first 800ms after mount to prevent
 * the nav from appearing immediately on page load.
 */
export function useNavVisibility(): NavVisibility {
  const cursorInZone = useCursorZone(60);
  const scroll = useScrollDirection();
  const [visibility, setVisibility] = useState<NavVisibility>({
    isVisible: false,
    trigger: "none",
  });

  const idleTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isHovering = useRef(false);
  const mountedAt = useRef(Date.now());

  // Suppress triggers during initial mount period
  const isSuppressed = useCallback(() => {
    return Date.now() - mountedAt.current < INITIAL_SUPPRESS_MS;
  }, []);

  // Allow the nav component to signal it's being hovered
  const setHovering = useCallback((hovering: boolean) => {
    isHovering.current = hovering;
  }, []);

  // Store setHovering on the window for the FloatingTopNav to access
  useEffect(() => {
    (window as unknown as Record<string, unknown>).__setNavHovering = setHovering;
    return () => {
      delete (window as unknown as Record<string, unknown>).__setNavHovering;
    };
  }, [setHovering]);

  // Reset idle timer
  const resetIdleTimer = useCallback(() => {
    if (idleTimer.current) clearTimeout(idleTimer.current);
    idleTimer.current = setTimeout(() => {
      if (!isHovering.current) {
        setVisibility({ isVisible: false, trigger: "none" });
      }
    }, IDLE_TIMEOUT);
  }, []);

  // Cursor zone trigger
  useEffect(() => {
    if (cursorInZone && !isSuppressed()) {
      setVisibility({ isVisible: true, trigger: "cursor" });
      resetIdleTimer();
    }
  }, [cursorInZone, resetIdleTimer, isSuppressed]);

  // Scroll trigger — DON'T trigger on initial atTop (page load)
  const hasScrolled = useRef(false);
  useEffect(() => {
    if (isSuppressed()) return;

    // Only use atTop trigger after user has actually scrolled away and back
    if (scroll.direction !== "idle") {
      hasScrolled.current = true;
    }

    if (scroll.atTop && hasScrolled.current) {
      setVisibility({ isVisible: true, trigger: "top" });
      resetIdleTimer();
    } else if (
      scroll.direction === "up" &&
      scroll.velocity > SCROLL_VELOCITY_THRESHOLD
    ) {
      setVisibility({ isVisible: true, trigger: "scroll" });
      resetIdleTimer();
    } else if (scroll.direction === "down" && scroll.velocity > 3) {
      if (!isHovering.current) {
        setVisibility({ isVisible: false, trigger: "none" });
      }
    }
  }, [scroll.direction, scroll.velocity, scroll.atTop, resetIdleTimer, isSuppressed]);

  // Tab focus trigger
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible" && !isSuppressed()) {
        setVisibility({ isVisible: true, trigger: "focus" });
        resetIdleTimer();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);
    return () =>
      document.removeEventListener("visibilitychange", handleVisibilityChange);
  }, [resetIdleTimer, isSuppressed]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (idleTimer.current) clearTimeout(idleTimer.current);
    };
  }, []);

  return visibility;
}
