"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsData } from "@/lib/api";
import { cn } from "@/lib/utils";

const HORA_INICIO = 7;
const HORA_FIM = 21;
const HORA_ALERTA_ATE = 20;

function heatColor(carga: number): string {
  if (carga <= 0) return "color-mix(in oklch, var(--muted) 75%, transparent)";
  if (carga < 0.25) return "color-mix(in oklch, var(--chart-1) 40%, var(--card))";
  if (carga < 0.5) return "color-mix(in oklch, var(--chart-2) 62%, var(--card))";
  if (carga < 0.75) return "color-mix(in oklch, var(--chart-4) 78%, var(--card))";
  return "color-mix(in oklch, var(--destructive) 82%, var(--card))";
}

export function HeatmapSetorHora({ heatmap }: { heatmap: AnalyticsData["heatmap"] }) {
  const inicio = heatmap.hora_inicio ?? HORA_INICIO;
  const fim = heatmap.hora_fim ?? HORA_FIM;
  const alertaAte = heatmap.hora_alerta_ate ?? HORA_ALERTA_ATE;
  const horasBase = Array.from({ length: fim - inicio + 1 }, (_, i) => i + inicio);
  const extras = heatmap.celulas
    .filter((c) => (c.hora < inicio || c.hora > fim) && c.volume > 0)
    .map((c) => c.hora);
  const horas = Array.from(new Set([...horasBase, ...extras])).sort((a, b) => a - b);
  const setores = heatmap.setores;
  const byKey = new Map(
    heatmap.celulas.map((c) => [`${c.setor_id}-${c.hora}`, c] as const),
  );

  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle>Mapa de calor · {String(inicio).padStart(2, "0")}h às {String(fim).padStart(2, "0")}h</CardTitle>
        <CardDescription>
          Expediente até as 21h (domingo e feriados 08h–12h). Carga = volume de senhas + espera média.
          Célula tracejada no expediente é hora sem retirada.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 overflow-x-auto">
        <table className="w-full min-w-[920px] border-collapse text-xs">
          <thead>
            <tr>
              <th className="p-2 text-left font-medium text-muted-foreground">Setor</th>
              {horas.map((h) => (
                <th key={h} className="p-1 text-center font-medium text-muted-foreground">
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
                  const volume = cell?.volume ?? 0;
                  const carga = cell?.carga ?? 0;
                  const semRetirada = h >= inicio && h <= alertaAte && volume <= 0;
                  return (
                    <td key={h} className="p-1">
                      <div
                        className={cn(
                          "flex h-9 items-center justify-center rounded-md text-[10px] font-medium",
                          carga > 0.5 ? "text-primary-foreground" : "text-foreground/80",
                          semRetirada && "border border-dashed border-primary/50",
                        )}
                        style={{ background: heatColor(semRetirada ? 0 : carga) }}
                        title={
                          volume > 0 && cell
                            ? `${cell.volume} senhas · espera ${cell.espera_media ?? "—"} min`
                            : semRetirada
                              ? "Nenhuma senha retirada neste horário"
                              : "Sem dados"
                        }
                      >
                        {volume > 0 ? volume : semRetirada ? "—" : ""}
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
        <div className="flex flex-wrap items-center gap-3 text-[11px] text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-5 rounded-sm border border-dashed border-primary/50 bg-muted" />
            Sem retirada
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-5 rounded-sm" style={{ background: heatColor(0.2) }} />
            Baixa
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-5 rounded-sm" style={{ background: heatColor(0.45) }} />
            Média
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-5 rounded-sm" style={{ background: heatColor(0.7) }} />
            Alta
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-3 w-5 rounded-sm" style={{ background: heatColor(0.9) }} />
            Crítica
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
