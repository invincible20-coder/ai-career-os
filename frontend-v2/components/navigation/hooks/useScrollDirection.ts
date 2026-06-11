"use client";

import { useState, useEffect, useRef, useCallback } from "react";

interface ScrollState {
  direction: "up" | "down" | "idle";
  velocity: number;
  atTop: boolean;
}

/**
 * Tracks scroll direction and velocity using requestAnimationFrame.
 * Detects aggressive upward scrolling and whether we're at the top.
 */
export function useScrollDirection(): ScrollState {
  const [state, setState] = useState<ScrollState>({
    direction: "idle",
    velocity: 0,
    atTop: true,
  });

  const lastScrollY = useRef(0);
  const lastTime = useRef(Date.now());
  const rafRef = useRef<number | null>(null);
  const ticking = useRef(false);

  const update = useCallback(() => {
    const currentY = window.scrollY;
    const currentTime = Date.now();
    const deltaY = lastScrollY.current - currentY; // positive = scrolling up
    const deltaTime = Math.max(currentTime - lastTime.current, 1);
    const velocity = Math.abs(deltaY / deltaTime) * 16; // normalize to ~px/frame

    const direction: ScrollState["direction"] =
      deltaY > 0 ? "up" : deltaY < 0 ? "down" : "idle";

    setState({
      direction,
      velocity,
      atTop: currentY <= 5,
    });

    lastScrollY.current = currentY;
    lastTime.current = currentTime;
    ticking.current = false;
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      if (!ticking.current) {
        ticking.current = true;
        rafRef.current = requestAnimationFrame(update);
      }
    };

    // Initialize
    lastScrollY.current = window.scrollY;
    setState((s) => ({ ...s, atTop: window.scrollY <= 5 }));

    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", handleScroll);
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [update]);

  return state;
}
