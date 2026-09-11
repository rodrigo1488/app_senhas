import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { AnalyticsData } from "@/lib/api";

function fmt(n: number | null | undefined, suffix = "") {
  if (n == null) return "—";
  return `${n}${suffix}`;
}

export function AtendentesTable({ rows }: { rows: AnalyticsData["atendentes"] }) {
  return (
    <Card className="col-span-full">
      <CardHeader>
        <CardTitle>Atendentes</CardTitle>
        <CardDescription>
          Produtividade (volume), espera na fila e qualidade — métricas separadas
        </CardDescription>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="border-b text-left text-muted-foreground">
              <th className="pb-2 pr-3 font-medium">Atendente</th>
              <th className="pb-2 pr-3 font-medium">Setor</th>
              <th className="pb-2 pr-3 font-medium">Atendimentos</th>
              <th className="pb-2 pr-3 font-medium">Espera média</th>
              <th className="pb-2 pr-3 font-medium">P90 espera</th>
              <th className="pb-2 pr-3 font-medium">Tempo atendimento</th>
              <th className="pb-2 font-medium">Nota média</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.operador_id} className="border-b last:border-0">
                <td className="py-2.5 pr-3 font-medium">{r.operador}</td>
                <td className="py-2.5 pr-3 text-muted-foreground">{r.setor ?? "—"}</td>
                <td className="py-2.5 pr-3">{r.atendimentos}</td>
                <td className="py-2.5 pr-3">{fmt(r.espera.media, " min")}</td>
                <td className="py-2.5 pr-3">{fmt(r.espera.p90, " min")}</td>
                <td className="py-2.5 pr-3">{fmt(r.tempo_atendimento_medio, " min")}</td>
                <td className="py-2.5">{fmt(r.nota_media)}</td>
              </tr>
            ))}
            {!rows.length ? (
              <tr>
                <td colSpan={7} className="py-6 text-muted-foreground">
                  Sem atendimentos no período
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
