"use client";

import { useEffect } from "react";

/** Garante tema claro no painel TV mesmo se o sistema/admin estiver em dark. */
export function ForceLightTheme() {
  useEffect(() => {
    const root = document.documentElement;
    const hadDark = root.classList.contains("dark");
    root.classList.remove("dark");
    root.classList.add("light");
    return () => {
      root.classList.remove("light");
      if (hadDark) root.classList.add("dark");
    };
  }, []);
  return null;
}
