"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Building2, Download, FileText, Printer, Users } from "lucide-react";
import { apiFetch, type AnalyticsData } from "@/lib/api";
import {
  DashboardFilters,
  type DashboardFiltersState,
} from "@/components/dashboard/filters";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type ReportType = "consolidado" | "setores" | "operadores";

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

function monthStartISO() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1).toLocaleDateString("en-CA");
}

function fmt(value: number | null | undefined, suffix = "") {
  return value == null ? "—" : `${value}${suffix}`;
}

function csvCell(value: unknown) {
  const text = value == null ? "" : String(value);
  return `"${text.replaceAll('"', '""')}"`;
}

function downloadCsv(filename: string, rows: unknown[][]) {
  const content = rows.map((row) => row.map(csvCell).join(";")).join("\r\n");
  const blob = new Blob([`\uFEFF${content}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function RelatoriosPage() {
  const [reportType, setReportType] = useState<ReportType>("consolidado");
  const [filters, setFilters] = useState<DashboardFiltersState>({
    from: monthStartISO(),
    to: todayISO(),
    setor_id: "",
    operador_id: "",
  });
  const [applied, setApplied] = useState(filters);
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const query = useMemo(() => {
    const params = new URLSearchParams();
    if (applied.from) params.set("from", applied.from);
    if (applied.to) params.set("to", applied.to);
    if (applied.setor_id) params.set("setor_id", applied.setor_id);
    if (applied.operador_id) params.set("operador_id", applied.operador_id);
    return params.toString();
  }, [applied]);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    apiFetch<AnalyticsData>(`/api/v1/admin/analytics?${query}`)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Erro ao gerar relatório"))
      .finally(() => setLoading(false));
  }, [query]);

  useEffect(() => {
    load();
  }, [load]);

  function exportCsv() {
    if (!data) return;
    const rows: unknown[][] = [
      ["CompuFlow — Relatório", reportLabels[reportType]],
      ["Período", applied.from, applied.to],
      ["Gerado em", new Date().toLocaleString("pt-BR")],
      [],
    ];

    if (reportType === "consolidado") {
      rows.push(
        ["RESUMO EXECUTIVO"],
        ["Métrica", "Valor"],
        ["Senhas emitidas", data.kpis.emitidas],
        ["Senhas chamadas", data.kpis.chamadas],
        ["Atendimentos", data.kpis.atendimentos],
        ["Finalizadas", data.kpis.finalizadas],
        ["Espera média (min)", data.kpis.espera.media],
        ["Mediana de espera (min)", data.kpis.espera.mediana],
        ["P90 de espera (min)", data.kpis.espera.p90],
        ["Maior espera (min)", data.kpis.espera.max],
        ["Nota média", data.kpis.nota_media],
        ["Avaliações (%)", data.kpis.pct_avaliacoes],
        ["Não chamadas", data.kpis.nao_chamadas],
        ["Abandono", data.kpis.abandono],
        ["Taxa de abandono (%)", data.kpis.taxa_abandono],
        ["QR codes escaneados", data.kpis.qr_escaneados ?? 0],
        ["Pedidos adiantados", data.kpis.pedidos_adiantados ?? 0],
        [],
      );
    }

    if (reportType === "consolidado" || reportType === "setores") {
      rows.push(
        ["DESEMPENHO POR SETOR"],
        [
          "Setor",
          "Emitidas",
          "Chamadas",
          "Finalizadas",
          "Atendimentos",
          "Não chamadas",
          "QR escaneados",
          "Pedidos adiantados",
          "Espera média (min)",
          "P90 (min)",
          "Nota média",
        ],
        ...data.por_setor.map((row) => [
          row.setor,
          row.emitidas,
          row.chamadas,
          row.finalizadas,
          row.atendimentos,
          row.nao_chamadas,
          row.qr_escaneados ?? 0,
          row.pedidos_adiantados ?? 0,
          row.espera.media,
          row.espera.p90,
          row.nota_media,
        ]),
        [],
      );
    }

    if (reportType === "consolidado" || reportType === "operadores") {
      rows.push(
        ["DESEMPENHO POR OPERADOR"],
        [
          "Operador",
          "Setor",
          "Atendimentos",
          "Espera média (min)",
          "P90 (min)",
          "Tempo médio de atendimento (min)",
          "Nota média",
          "Avaliações",
        ],
        ...data.atendentes.map((row) => [
          row.operador,
          row.setor,
          row.atendimentos,
          row.espera.media,
          row.espera.p90,
          row.tempo_atendimento_medio,
          row.nota_media,
          row.n_avaliacoes,
        ]),
      );
    }

    downloadCsv(
      `compuflow-${reportType}-${applied.from || "inicio"}-${applied.to || "hoje"}.csv`,
      rows,
    );
  }

  return (
    <div className="space-y-6">
      <div className="no-print flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Relatórios</h1>
          <p className="text-muted-foreground">
            Consolide resultados e exporte os indicadores da operação.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={exportCsv} disabled={!data || loading}>
            <Download className="mr-2 h-4 w-4" />
            Exportar CSV
          </Button>
          <Button onClick={() => window.print()} disabled={!data || loading}>
            <Printer className="mr-2 h-4 w-4" />
            Imprimir / PDF
          </Button>
        </div>
      </div>

      <div className="no-print grid gap-3 md:grid-cols-3">
        <ReportOption
          active={reportType === "consolidado"}
          icon={FileText}
          title="Consolidado"
          description="Resumo executivo, setores e operadores."
          onClick={() => setReportType("consolidado")}
        />
        <ReportOption
          active={reportType === "setores"}
          icon={Building2}
          title="Por setor"
          description="Volume, espera e qualidade de cada setor."
          onClick={() => setReportType("setores")}
        />
        <ReportOption
          active={reportType === "operadores"}
          icon={Users}
          title="Por operador"
          description="Produtividade e qualidade dos atendentes."
          onClick={() => setReportType("operadores")}
        />
      </div>

      <div className="no-print">
        <DashboardFilters
          value={filters}
          onChange={setFilters}
          onApply={() => setApplied(filters)}
          setores={data?.filtros.setores ?? []}
          operadores={data?.filtros.operadores ?? []}
        />
      </div>

      {error ? <p className="no-print text-destructive">{error}</p> : null}
      {loading && !data ? <p className="no-print text-muted-foreground">Gerando relatório...</p> : null}

      {data ? (
        <article id="report-print" className={cn("space-y-6", loading && "opacity-60")}>
          <ReportHeader type={reportType} from={applied.from} to={applied.to} />
          {reportType === "consolidado" ? <ExecutiveSummary data={data} /> : null}
          {reportType === "consolidado" || reportType === "setores" ? (
            <SectorReport rows={data.por_setor} />
          ) : null}
          {reportType === "consolidado" || reportType === "operadores" ? (
            <OperatorReport rows={data.atendentes} />
          ) : null}
        </article>
      ) : null}

      <style jsx global>{`
        @media print {
          @page {
            size: A4 landscape;
            margin: 12mm;
          }
          body {
            background: white !important;
          }
          body * {
            visibility: hidden !important;
          }
          #report-print,
          #report-print * {
            visibility: visible !important;
          }
          #report-print {
            position: absolute;
            inset: 0;
            width: 100%;
            color: #111 !important;
          }
          #report-print .report-card {
            break-inside: avoid;
            box-shadow: none !important;
          }
          .no-print {
            display: none !important;
          }
        }
      `}</style>
    </div>
  );
}

const reportLabels: Record<ReportType, string> = {
  consolidado: "Relatório consolidado",
  setores: "Relatório por setor",
  operadores: "Relatório por operador",
};

function ReportOption({
  active,
  icon: Icon,
  title,
  description,
  onClick,
}: {
  active: boolean;
  icon: typeof FileText;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-xl border bg-card p-4 text-left transition hover:border-primary/40",
        active && "border-primary ring-1 ring-primary",
      )}
    >
      <Icon className={cn("mb-3 h-5 w-5 text-muted-foreground", active && "text-primary")} />
      <span className="block font-semibold">{title}</span>
      <span className="mt-1 block text-sm text-muted-foreground">{description}</span>
    </button>
  );
}

function ReportHeader({ type, from, to }: { type: ReportType; from: string; to: string }) {
  return (
    <div className="border-b pb-4">
      <p className="text-sm font-bold uppercase tracking-[0.16em] text-primary">CompuFlow</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-3">
        <h2 className="text-3xl font-bold tracking-tight">{reportLabels[type]}</h2>
        <p className="text-sm text-muted-foreground">
          Período: {from || "início"} a {to || "hoje"}
        </p>
      </div>
    </div>
  );
}

function ExecutiveSummary({ data }: { data: AnalyticsData }) {
  const items = [
    ["Senhas emitidas", data.kpis.emitidas],
    ["Senhas chamadas", data.kpis.chamadas],
    ["Atendimentos", data.kpis.atendimentos],
    ["Espera média", fmt(data.kpis.espera.media, " min")],
    ["P90 de espera", fmt(data.kpis.espera.p90, " min")],
    ["Nota média", fmt(data.kpis.nota_media)],
    ["Não chamadas", data.kpis.nao_chamadas],
    ["Taxa de abandono", fmt(data.kpis.taxa_abandono, "%")],
    ["QR codes escaneados", data.kpis.qr_escaneados ?? 0],
    ["Pedidos adiantados", data.kpis.pedidos_adiantados ?? 0],
  ];
  return (
    <section>
      <h3 className="mb-3 text-lg font-semibold">Resumo executivo</h3>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {items.map(([label, value]) => (
          <Card key={String(label)} className="report-card">
            <CardContent className="p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
              <p className="mt-2 text-2xl font-bold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </section>
  );
}

function SectorReport({ rows }: { rows: AnalyticsData["por_setor"] }) {
  return (
    <ReportTable
      title="Desempenho por setor"
      headers={[
        "Setor",
        "Emitidas",
        "Chamadas",
        "Finalizadas",
        "Atendimentos",
        "Não chamadas",
        "QR escaneados",
        "Pedidos adiantados",
        "Espera média",
        "P90",
        "Nota",
      ]}
      rows={rows.map((row) => [
        row.setor,
        row.emitidas,
        row.chamadas,
        row.finalizadas,
        row.atendimentos,
        row.nao_chamadas,
        row.qr_escaneados ?? 0,
        row.pedidos_adiantados ?? 0,
        fmt(row.espera.media, " min"),
        fmt(row.espera.p90, " min"),
        fmt(row.nota_media),
      ])}
    />
  );
}

function OperatorReport({ rows }: { rows: AnalyticsData["atendentes"] }) {
  return (
    <ReportTable
      title="Desempenho por operador"
      headers={[
        "Operador",
        "Setor",
        "Atendimentos",
        "Espera média",
        "P90",
        "Tempo atendimento",
        "Nota",
        "Avaliações",
      ]}
      rows={rows.map((row) => [
        row.operador,
        row.setor ?? "—",
        row.atendimentos,
        fmt(row.espera.media, " min"),
        fmt(row.espera.p90, " min"),
        fmt(row.tempo_atendimento_medio, " min"),
        fmt(row.nota_media),
        row.n_avaliacoes,
      ])}
    />
  );
}

function ReportTable({
  title,
  headers,
  rows,
}: {
  title: string;
  headers: string[];
  rows: (string | number)[][];
}) {
  return (
    <Card className="report-card">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full min-w-[760px] text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              {headers.map((header) => (
                <th key={header} className="whitespace-nowrap pb-2 pr-4 font-medium">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-b last:border-0">
                {row.map((value, columnIndex) => (
                  <td key={columnIndex} className={cn("whitespace-nowrap py-2.5 pr-4", columnIndex === 0 && "font-medium")}>
                    {value}
                  </td>
                ))}
              </tr>
            ))}
            {!rows.length ? (
              <tr>
                <td colSpan={headers.length} className="py-8 text-center text-muted-foreground">
                  Nenhum dado encontrado no período.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
