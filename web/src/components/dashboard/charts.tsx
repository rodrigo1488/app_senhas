"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsData } from "@/lib/api";

const CHART = {
  1: "var(--chart-1)",
  2: "var(--chart-2)",
  3: "var(--chart-3)",
  4: "var(--chart-4)",
};

export function DemandaPorHoraChart({ data }: { data: AnalyticsData["por_hora"] }) {
  const rows = data.filter((d) => d.retiradas > 0 || d.chamadas > 0);
  const source = rows.length ? rows : data.slice(8, 19);

  return (
    <Card className="col-span-full lg:col-span-2">
      <CardHeader>
        <CardTitle>Demanda por horário</CardTitle>
        <CardDescription>Retiradas e chamadas ao longo do dia</CardDescription>
      </CardHeader>
      <CardContent className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={source}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis tickLine={false} axisLine={false} fontSize={12} allowDecimals={false} />
            <Tooltip />
            <Legend />
            <Area
              type="monotone"
              dataKey="retiradas"
              name="Retiradas"
              stroke={CHART[1]}
              fill={CHART[1]}
              fillOpacity={0.25}
            />
            <Area
              type="monotone"
              dataKey="chamadas"
              name="Chamadas"
              stroke={CHART[3]}
              fill={CHART[3]}
              fillOpacity={0.2}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function ComparativoSetorChart({ data }: { data: AnalyticsData["por_setor"] }) {
  const rows = data.map((s) => ({
    setor: s.setor,
    espera: s.espera.media ?? 0,
    emitidas: s.emitidas,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Espera por setor</CardTitle>
        <CardDescription>Tempo médio de espera (minutos)</CardDescription>
      </CardHeader>
      <CardContent className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="setor" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis tickLine={false} axisLine={false} fontSize={12} />
            <Tooltip />
            <Bar dataKey="espera" name="Espera média" fill={CHART[2]} radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function DistribuicaoNotasChart({
  data,
}: {
  data: AnalyticsData["distribuicao_notas"];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Distribuição de notas</CardTitle>
        <CardDescription>Volume por nota atribuída</CardDescription>
      </CardHeader>
      <CardContent className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="nota" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis tickLine={false} axisLine={false} fontSize={12} allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="total" name="Avaliações" fill={CHART[1]} radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

export function EsperaSatisfacaoChart({
  data,
}: {
  data: AnalyticsData["espera_x_satisfacao"];
}) {
  const rows = data.map((d) => ({
    faixa: d.faixa + " min",
    nota: d.nota_media ?? 0,
    amostras: d.amostras,
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Espera × satisfação</CardTitle>
        <CardDescription>Nota média por faixa de espera</CardDescription>
      </CardHeader>
      <CardContent className="h-[280px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
            <XAxis dataKey="faixa" tickLine={false} axisLine={false} fontSize={12} />
            <YAxis domain={[0, 5]} tickLine={false} axisLine={false} fontSize={12} />
            <Tooltip />
            <Bar dataKey="nota" name="Nota média" fill={CHART[3]} radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

const FLUXO_COLORS = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
];

export function FluxoPorSetorChart({
  data,
}: {
  data: AnalyticsData["fluxo_por_setor"] | undefined;
}) {
  const setores = data?.setores ?? [];
  const series = data?.series ?? [];
  const hasVolume = series.some((row) =>
    setores.some((setor) => Number(row[setor.chave] ?? 0) > 0),
  );

  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle>Fluxo por setor</CardTitle>
        <CardDescription>
          Volume de senhas {data?.granularidade === "dia" ? "por dia" : "por hora"} em cada
          setor de atendimento
        </CardDescription>
      </CardHeader>
      <CardContent className="h-[320px]">
        {!setores.length || !hasVolume ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            Sem fluxo de senhas no período selecionado.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={series}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
              <XAxis dataKey="label" tickLine={false} axisLine={false} fontSize={12} />
              <YAxis tickLine={false} axisLine={false} fontSize={12} allowDecimals={false} />
              <Tooltip />
              <Legend />
              {setores.map((setor, index) => (
                <Line
                  key={setor.id}
                  type="monotone"
                  dataKey={setor.chave}
                  name={setor.nome}
                  stroke={FLUXO_COLORS[index % FLUXO_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  activeDot={{ r: 4 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
