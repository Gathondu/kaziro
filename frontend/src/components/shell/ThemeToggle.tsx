"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect, useState } from "react";

export function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return false;
    const saved = localStorage.getItem("kaziro-theme");
    return saved
      ? saved === "terracotta_dark"
      : matchMedia("(prefers-color-scheme: dark)").matches;
  });

  useEffect(() => {
    document.documentElement.dataset.theme = dark
      ? "terracotta_dark"
      : "terracotta";
  }, [dark]);

  function toggle(): void {
    const next = !dark;
    setDark(next);
    const theme = next ? "terracotta_dark" : "terracotta";
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("kaziro-theme", theme);
  }

  return (
    <button
      className="btn btn-ghost btn-circle btn-sm"
      onClick={toggle}
      type="button"
      aria-label={dark ? "Use light theme" : "Use dark theme"}
    >
      {dark ? <Sun className="size-4" /> : <Moon className="size-4" />}
    </button>
  );
}
