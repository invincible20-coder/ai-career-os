"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

type Theme = "dark" | "light" | "system";

interface ThemeContextValue {
  theme: Theme;
  resolved: "dark" | "light";
  setTheme: (t: Theme) => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: "dark",
  resolved: "dark",
  setTheme: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

function getSystemPreference(): "dark" | "light" {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function resolveTheme(theme: Theme): "dark" | "light" {
  if (theme === "system") return getSystemPreference();
  return theme;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");
  const [resolved, setResolved] = useState<"dark" | "light">("dark");

  // Read saved preference on mount
  useEffect(() => {
    const saved = localStorage.getItem("huntai-theme") as Theme | null;
    const initial = saved || "dark";
    setThemeState(initial);
    const r = resolveTheme(initial);
    setResolved(r);
    applyThemeClass(r);
  }, []);

  // Listen for system theme changes
  useEffect(() => {
    if (theme !== "system") return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => {
      const r = getSystemPreference();
      setResolved(r);
      applyThemeClass(r);
    };
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, [theme]);

  const setTheme = useCallback((t: Theme) => {
    setThemeState(t);
    localStorage.setItem("huntai-theme", t);
    const r = resolveTheme(t);
    setResolved(r);

    // Smooth transition
    document.documentElement.classList.add("theme-transition");
    applyThemeClass(r);
    setTimeout(() => {
      document.documentElement.classList.remove("theme-transition");
    }, 600);
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, resolved, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

function applyThemeClass(resolved: "dark" | "light") {
  const root = document.documentElement;
  if (resolved === "light") {
    root.classList.add("light");
    root.classList.remove("dark");
  } else {
    root.classList.add("dark");
    root.classList.remove("light");
  }
}
