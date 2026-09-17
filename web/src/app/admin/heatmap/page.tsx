"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch, type AnalyticsData } from "@/lib/api";
import {
  DashboardFilters,
  type DashboardFiltersState,
} from "@/components/dashboard/filters";
import { HeatmapSetorHora } from "@/components/dashboard/heatmap";
import { DemandaPorHoraChart, FluxoPorSetorChart } from "@/components/dashboard/charts";
import { KpiCard } from "@/components/dashboard/kpi-card";

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function fmtMin(n: number | null | undefined) {
  if (n == null) return "—";
  return `${n} min`;
}

export default function HeatmapDashboardPage() {
  const [filters, setFilters] = useState<DashboardFiltersState>({
    from: todayISO(),
    to: todayISO(),
    setor_id: "",
    operador_id: "",
  });
  const [applied, setApplied] = useState(filters);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const query = useMemo(() => {
    const p = new URLSearchParams();
    if (applied.from) p.set("from", applied.from);
    if (applied.to) p.set("to", applied.to);
    if (applied.setor_id) p.set("setor_id", applied.setor_id);
    if (applied.operador_id) p.set("operador_id", applied.operador_id);
    return p.toString();
  }, [applied]);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    apiFetch<AnalyticsData>(`/api/v1/admin/analytics?${query}`)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar"))
      .finally(() => setLoading(false));
  }, [query]);

  useEffect(() => {
    load();
  }, [load]);

  const setores = data?.filtros.setores ?? [];
  const operadores = data?.filtros.operadores ?? [];

  const pico = useMemo(() => {
    if (!data?.heatmap.celulas.length) return null;
    return data.heatmap.celulas.reduce((best, cell) =>
      cell.carga > best.carga ? cell : best,
    );
  }, [data]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Mapa de calor</h1>
        <p className="text-muted-foreground">
          Carga operacional por horário e setor — volume de senhas e espera
        </p>
      </div>

      <DashboardFilters
        value={filters}
        onChange={setFilters}
        onApply={() => setApplied(filters)}
        setores={setores}
        operadores={operadores}
      />

      {error ? <p className="text-destructive">{error}</p> : null}
      {loading && !data ? (
        <p className="text-muted-foreground">Carregando mapa de calor...</p>
      ) : null}

      {data ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard title="Senhas emitidas" value={String(data.kpis.emitidas)} />
            <KpiCard title="Espera média" value={fmtMin(data.kpis.espera.media)} />
            <KpiCard title="Maior espera" value={fmtMin(data.kpis.espera.max)} />
            <KpiCard
              title="Pico de carga"
              value={
                pico && pico.volume > 0
                  ? `${String(pico.hora).padStart(2, "0")}h · ${pico.setor}`
                  : "—"
              }
              hint={
                pico && pico.volume > 0
                  ? `${pico.volume} senhas · espera ${pico.espera_media ?? "—"} min`
                  : undefined
              }
            />
          </div>

          <HeatmapSetorHora heatmap={data.heatmap} />

          <FluxoPorSetorChart data={data.fluxo_por_setor} />

          <div className="grid gap-4 lg:grid-cols-1">
            <DemandaPorHoraChart data={data.por_hora} />
          </div>
        </>
      ) : null}
    </div>
  );
}
