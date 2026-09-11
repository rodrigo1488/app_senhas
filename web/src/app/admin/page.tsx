"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { apiFetch, type DashboardData } from "@/lib/api";

export default function AdminDashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<DashboardData>("/api/v1/admin/dashboard")
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar"));
  }, []);

  if (error) return <p className="text-destructive">{error}</p>;
  if (!data) return <p className="text-muted-foreground">Carregando dashboard...</p>;

  const totalDia = data.atendimentos_dia.reduce((s, r) => s + r.total, 0);
  const totalMes = data.atendimentos_mes.reduce((s, r) => s + r.total, 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Visão geral dos atendimentos e avaliações</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card>
          <CardHeader>
            <CardDescription>Atendimentos hoje</CardDescription>
            <CardTitle className="text-3xl">{totalDia}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Atendimentos no mês</CardDescription>
            <CardTitle className="text-3xl">{totalMes}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Melhor operador</CardDescription>
            <CardTitle className="text-xl">
              {data.melhor_operador
                ? `${data.melhor_operador.operador} (${data.melhor_operador.media?.toFixed(1) ?? "-"})`
                : "—"}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader>
            <CardDescription>Pior operador</CardDescription>
            <CardTitle className="text-xl">
              {data.pior_operador
                ? `${data.pior_operador.operador} (${data.pior_operador.media?.toFixed(1) ?? "-"})`
                : "—"}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Por setor (hoje)</CardTitle>
          </CardHeader>
          <CardContent>
            <TableRows rows={data.atendimentos_dia.map((r) => [r.setor, String(r.total)])} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Por setor (mês)</CardTitle>
          </CardHeader>
          <CardContent>
            <TableRows rows={data.atendimentos_mes.map((r) => [r.setor, String(r.total)])} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Médias de avaliação</CardTitle>
          <CardDescription>Operadores ordenados pela média</CardDescription>
        </CardHeader>
        <CardContent>
          <TableRows
            headers={["Operador", "Setor", "Média"]}
            rows={data.medias_operadores.map((r) => [
              r.operador,
              r.setor || "—",
              r.media != null ? r.media.toFixed(2) : "—",
            ])}
          />
        </CardContent>
      </Card>
    </div>
  );
}

function TableRows({
  headers,
  rows,
}: {
  headers?: string[];
  rows: string[][];
}) {
  if (!rows.length) {
    return <p className="text-sm text-muted-foreground">Sem dados no período.</p>;
  }
  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        {headers && (
          <thead className="bg-muted/60">
            <tr>
              {headers.map((h) => (
                <th key={h} className="px-3 py-2 text-left font-medium">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t">
              {row.map((cell, j) => (
                <td key={j} className="px-3 py-2">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
