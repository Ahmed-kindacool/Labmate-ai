import * as React from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "labmate-theme";

function getPreferredTheme(): Theme {
  if (typeof window === "undefined") return "light";

  const stored = window.localStorage.getItem(STORAGE_KEY);
  if (stored === "light" || stored === "dark") return stored;

  // No stored choice yet — fall back to the OS/browser preference.
  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function applyTheme(theme: Theme) {
  // index.css defines both palettes via `:root` (light) and `.dark`
  // (@custom-variant dark (&:is(.dark *))) — toggling this class is all
  // that's needed to switch every themed color token at once.
  document.documentElement.classList.toggle("dark", theme === "dark");
}

export function useTheme() {
  const [theme, setThemeState] = React.useState<Theme>(getPreferredTheme);

  // Apply on mount too, in case getPreferredTheme() ran before hydration
  // settled or the class was stripped by a prior render.
  React.useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const setTheme = React.useCallback((next: Theme) => {
    setThemeState(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const toggleTheme = React.useCallback(() => {
    setTheme(theme === "dark" ? "light" : "dark");
  }, [theme, setTheme]);

  return { theme, setTheme, toggleTheme };
}
