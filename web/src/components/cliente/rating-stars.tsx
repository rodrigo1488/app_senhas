"use client";

import { Star } from "lucide-react";
import { cn } from "@/lib/utils";

type Props = {
  value: number | null;
  onChange: (nota: number) => void;
  disabled?: boolean;
};

export function RatingStars({ value, onChange, disabled }: Props) {
  return (
    <div className="flex items-center justify-center gap-2" role="group" aria-label="Avaliação">
      {[1, 2, 3, 4, 5].map((n) => {
        const active = value != null && n <= value;
        return (
          <button
            key={n}
            type="button"
            disabled={disabled}
            onClick={() => onChange(n)}
            className={cn(
              "rounded-full p-1.5 transition-transform hover:scale-110 disabled:opacity-50",
              active ? "text-primary" : "text-muted-foreground/40",
            )}
            aria-label={`${n} estrela${n > 1 ? "s" : ""}`}
          >
            <Star className={cn("h-9 w-9", active && "fill-current")} />
          </button>
        );
      })}
    </div>
  );
}
