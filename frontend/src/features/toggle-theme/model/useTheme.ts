import { useEffect, useState } from "react";

type Theme = "light" | "dark";
const KEY = "theme";

// Начальная тема уже выставлена скриптом в index.html.
const initialTheme = (): Theme => (document.documentElement.classList.contains("dark") ? "dark" : "light");

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(initialTheme);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem(KEY, theme);
    } catch {
      /* ignore */
    }
  }, [theme]);

  return { theme, toggle: () => setTheme((t) => (t === "dark" ? "light" : "dark")) };
}
