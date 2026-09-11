import type { AnalyticsData } from "@/lib/api";
import { cn } from "@/lib/utils";

export function DashboardAlerts({ alertas }: { alertas: AnalyticsData["alertas"] }) {
  if (!alertas.length) return null;

  return (
    <div className="space-y-2">
      {alertas.map((a, i) => (
        <div
          key={`${a.tipo}-${i}`}
          className={cn(
            "rounded-lg border px-4 py-3 text-sm",
            a.severidade === "critical"
              ? "border-destructive/40 bg-destructive/10 text-destructive"
              : "border-primary/30 bg-primary/5 text-foreground",
          )}
        >
          {a.mensagem}
        </div>
      ))}
    </div>
  );
}
