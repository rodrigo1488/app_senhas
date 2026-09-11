"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsData } from "@/lib/api";
import { cn } from "@/lib/utils";

function heatColor(carga: number): string {
  if (carga <= 0) return "color-mix(in oklch, var(--muted) 80%, transparent)";
  if (carga < 0.25) return "color-mix(in oklch, var(--chart-1) 35%, var(--card))";
  if (carga < 0.5) return "color-mix(in oklch, var(--chart-1) 55%, var(--card))";
  if (carga < 0.75) return "color-mix(in oklch, var(--chart-2) 70%, var(--card))";
  return "color-mix(in oklch, var(--chart-3) 85%, var(--card))";
}

export function HeatmapSetorHora({ heatmap }: { heatmap: AnalyticsData["heatmap"] }) {
  const horas = Array.from({ length: 13 }, (_, i) => i + 7); // 07–19
  const setores = heatmap.setores;
  const byKey = new Map(
    heatmap.celulas.map((c) => [`${c.setor_id}-${c.hora}`, c] as const),
  );

  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle>Heatmap horário × setor</CardTitle>
        <CardDescription>
          Carga = volume de senhas + espera média (mais escuro = mais crítico)
        </CardDescription>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-xs">
          <thead>
            <tr>
              <th className="p-2 text-left font-medium text-muted-foreground">Setor</th>
              {horas.map((h) => (
                <th key={h} className="p-2 text-center font-medium text-muted-foreground">
                  {String(h).padStart(2, "0")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {setores.map((s) => (
              <tr key={s.id}>
                <td className="whitespace-nowrap p-2 font-medium">{s.nome}</td>
                {horas.map((h) => {
                  const cell = byKey.get(`${s.id}-${h}`);
                  const carga = cell?.carga ?? 0;
                  return (
                    <td key={h} className="p-1">
                      <div
                        className={cn(
                          "flex h-9 items-center justify-center rounded-md text-[10px] font-medium",
                          carga > 0.5 ? "text-primary-foreground" : "text-foreground/80",
                        )}
                        style={{ background: heatColor(carga) }}
                        title={
                          cell
                            ? `${cell.volume} senhas · espera ${cell.espera_media ?? "—"} min`
                            : "Sem dados"
                        }
                      >
                        {cell && cell.volume > 0 ? cell.volume : ""}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
            {!setores.length ? (
              <tr>
                <td colSpan={horas.length + 1} className="p-4 text-muted-foreground">
                  Sem dados no período
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
