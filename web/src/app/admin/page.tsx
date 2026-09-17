"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { apiFetch, type AnalyticsData } from "@/lib/api";
import { KpiCard } from "@/components/dashboard/kpi-card";
import {
  DashboardFilters,
  type DashboardFiltersState,
} from "@/components/dashboard/filters";
import { DashboardAlerts } from "@/components/dashboard/alerts";
import {
  ComparativoSetorChart,
  DemandaPorHoraChart,
  DistribuicaoNotasChart,
  EsperaSatisfacaoChart,
  FluxoPorSetorChart,
} from "@/components/dashboard/charts";
import { HeatmapSetorHora } from "@/components/dashboard/heatmap";
import { AtendentesTable } from "@/components/dashboard/atendentes-table";

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function fmtMin(n: number | null | undefined) {
  if (n == null) return "—";
  return `${n} min`;
}

function fmtNum(n: number | null | undefined, suffix = "") {
  if (n == null) return "—";
  return `${n}${suffix}`;
}

export default function AdminDashboardPage() {
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

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">
          Métricas de fila, espera e satisfação por período
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
        <p className="text-muted-foreground">Carregando analytics...</p>
      ) : null}

      {data ? (
        <>
          <DashboardAlerts alertas={data.alertas} />

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <KpiCard title="Senhas emitidas" value={String(data.kpis.emitidas)} />
            <KpiCard title="Senhas chamadas" value={String(data.kpis.chamadas)} />
            <KpiCard
              title="Espera média"
              value={fmtMin(data.kpis.espera.media)}
              hint={`Mediana ${fmtMin(data.kpis.espera.mediana)} · P90 ${fmtMin(data.kpis.espera.p90)}`}
            />
            <KpiCard
              title="Maior espera"
              value={fmtMin(data.kpis.espera.max)}
              hint={`P95 ${fmtMin(data.kpis.espera.p95)}`}
            />
            <KpiCard title="Atendimentos" value={String(data.kpis.atendimentos)} />
            <KpiCard title="Nota média" value={fmtNum(data.kpis.nota_media)} />
            <KpiCard
              title="% avaliações"
              value={fmtNum(data.kpis.pct_avaliacoes, "%")}
            />
            <KpiCard
              title="Não chamadas / abandono"
              value={`${data.kpis.nao_chamadas} / ${data.kpis.abandono}`}
              hint={`Abandono: status A há +${data.kpis.abandono_minutos} min${
                data.kpis.taxa_abandono != null ? ` (${data.kpis.taxa_abandono}%)` : ""
              }`}
            />
            <KpiCard
              title="QR codes escaneados"
              value={String(data.kpis.qr_escaneados ?? 0)}
              hint="Pessoas que abriram o acompanhamento pelo QR (1 por senha)"
            />
            <KpiCard
              title="Pedidos adiantados"
              value={String(data.kpis.pedidos_adiantados ?? 0)}
              hint="Clientes que enviaram o pedido pelo acompanhamento"
            />
          </div>

          <FluxoPorSetorChart data={data.fluxo_por_setor} />

          <div className="grid gap-4 lg:grid-cols-3">
            <DemandaPorHoraChart data={data.por_hora} />
            <ComparativoSetorChart data={data.por_setor} />
          </div>

          <HeatmapSetorHora heatmap={data.heatmap} />

          <AtendentesTable rows={data.atendentes} />

          <div className="grid gap-4 lg:grid-cols-2">
            <DistribuicaoNotasChart data={data.distribuicao_notas} />
            <EsperaSatisfacaoChart data={data.espera_x_satisfacao} />
          </div>
        </>
      ) : null}
    </div>
  );
}
