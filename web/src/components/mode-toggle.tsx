"use client";

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";

const ORDER = ["light", "dark", "system"] as const;

export function ModeToggle({ className }: { className?: string }) {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" className={className} aria-label="Tema" disabled>
        <Sun className="h-4 w-4" />
      </Button>
    );
  }

  const current = (theme as (typeof ORDER)[number]) || "system";
  const Icon = current === "dark" || (current === "system" && resolvedTheme === "dark") ? Moon : current === "system" ? Monitor : Sun;

  function cycle() {
    const idx = ORDER.indexOf(current);
    setTheme(ORDER[(idx + 1) % ORDER.length]);
  }

  const label =
    current === "light" ? "Claro" : current === "dark" ? "Escuro" : "Sistema";

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon"
      className={className}
      onClick={cycle}
      aria-label={`Tema: ${label}. Clique para alternar.`}
      title={`Tema: ${label}`}
    >
      <Icon className="h-4 w-4" />
    </Button>
  );
}
