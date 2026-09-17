"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, Radio } from "lucide-react";
import { io, type Socket } from "socket.io-client";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { apiFetch, setorEhAtendimento, type FilaAoVivoData, type Setor } from "@/lib/api";
import { resolveApiBaseUrl } from "@/lib/cliente-socket";
import { cn } from "@/lib/utils";

function fmtMin(n: number | null | undefined) {
  if (n == null) return "—";
  return `${n} min`;
}

function fmtPct(n: number | null | undefined) {
  if (n == null) return "—";
  return `${n}%`;
}

function StatCard({
  title,
  value,
  hint,
  accent,
}: {
  title: string;
  value: string;
  hint?: string;
  accent?: boolean;
}) {
  return (
    <Card className={cn(accent && "border-primary/40")}>
      <CardHeader className="pb-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className="text-2xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      {hint ? (
        <CardContent>
          <p className="text-xs text-muted-foreground">{hint}</p>
        </CardContent>
      ) : null}
    </Card>
  );
}

export default function FilaAoVivoPage() {
  const [setores, setSetores] = useState<Setor[]>([]);
  const [setorId, setSetorId] = useState("");
  const [data, setData] = useState<FilaAoVivoData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const [ignorarAuto, setIgnorarAuto] = useState(false);

  const loadSnapshot = useCallback(async (id: string) => {
    if (!id) return;
    const snap = await apiFetch<FilaAoVivoData>(`/api/v1/admin/fila-ao-vivo?setor_id=${id}`);
    setData(snap);
    setIgnorarAuto(snap.config.ignorar_finalizados_automaticos);
    setError(null);
  }, []);

  useEffect(() => {
    apiFetch<Setor[]>("/api/v1/admin/setores")
      .then((list) => {
        const atendimento = list.filter(setorEhAtendimento);
        setSetores(atendimento);
        setSetorId((current) => current || (atendimento[0] ? String(atendimento[0].id) : ""));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erro ao carregar setores"));
  }, []);

  useEffect(() => {
    if (!setorId) return;
    loadSnapshot(setorId).catch((e) =>
      setError(e instanceof Error ? e.message : "Erro ao carregar fila"),
    );
  }, [setorId, loadSnapshot]);

  // Socket.IO: token TV do setor → escuta fila:atualizada / senha:chamada → refresh
  useEffect(() => {
    if (!setorId) return;
    let socket: Socket | null = null;
    let cancelled = false;

    (async () => {
      try {
        const { session_token } = await apiFetch<{ session_token: string }>(
          `/api/v1/admin/fila-ao-vivo/token?setor_id=${setorId}`,
        );
        if (cancelled) return;
        const base = resolveApiBaseUrl();
        const viaHttpsProxy =
          typeof window !== "undefined" &&
          window.location.protocol === "https:" &&
          (!base || base === window.location.origin);
        socket = io(base || "/", {
          path: "/socket.io",
          transports: viaHttpsProxy ? ["polling"] : ["websocket", "polling"],
          upgrade: !viaHttpsProxy,
          auth: { session_token },
        });
        socket.on("connect", () => setLive(true));
        socket.on("disconnect", () => setLive(false));
        const refresh = () => {
          loadSnapshot(setorId).catch(() => undefined);
        };
        socket.on("fila:atualizada", refresh);
        socket.on("senha:chamada", refresh);
        socket.on("auth:erro", (payload: { mensagem?: string }) => {
          setError(payload?.mensagem || "Falha na autenticação em tempo real");
          setLive(false);
        });
      } catch (e) {
        if (!cancelled) {
          setLive(false);
          setError(e instanceof Error ? e.message : "Socket indisponível");
        }
      }
    })();

    return () => {
      cancelled = true;
      setLive(false);
      if (socket) {
        socket.removeAllListeners();
        socket.disconnect();
      }
    };
  }, [setorId, loadSnapshot]);

  async function toggleIgnorar(next: boolean) {
    setIgnorarAuto(next);
    await apiFetch("/api/v1/admin/fila-ao-vivo/config", {
      method: "PUT",
      body: JSON.stringify({ ignorar_finalizados_automaticos: next }),
    });
    if (setorId) await loadSnapshot(setorId);
  }

  const selectClass =
    "flex h-9 w-full max-w-xs rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:ring-2 focus-visible:ring-ring";

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Fila ao Vivo</h1>
          <p className="text-muted-foreground">
            Monitoramento em tempo real por setor
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <span
            className={cn(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium",
              live
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-border text-muted-foreground",
            )}
          >
            {live ? <Radio className="h-3.5 w-3.5" /> : <Activity className="h-3.5 w-3.5" />}
            {live ? "Ao vivo" : "Offline"}
          </span>
          <div className="grid gap-1.5">
            <Label htmlFor="setor">Setor</Label>
            <select
              id="setor"
              className={selectClass}
              value={setorId}
              onChange={(e) => setSetorId(e.target.value)}
            >
              {!setores.length ? <option value="">Nenhum setor</option> : null}
              {setores.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.nome}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {!setorId ? (
        <p className="rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm">
          Selecione um setor para carregar o monitoramento em tempo real.
        </p>
      ) : null}

      {error ? <p className="text-sm text-destructive">{error}</p> : null}

      {data ? (
        <>
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={ignorarAuto}
              onChange={(e) => toggleIgnorar(e.target.checked)}
              className="h-4 w-4 accent-[var(--primary)]"
            />
            Ignorar finalizados automaticamente (sem avaliação) nos KPIs
          </label>

          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Agora · {data.setor.nome}
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard
                title="Normal — espera"
                value={String(data.agora.espera.normal)}
                hint={`${fmtPct(data.agora.espera.pct_normal)} do momento`}
              />
              <StatCard
                title="Preferencial — espera"
                value={String(data.agora.espera.preferencial)}
                hint={`${fmtPct(data.agora.espera.pct_preferencial)} do momento`}
                accent
              />
              <StatCard
                title="Normal — em atendimento"
                value={String(data.agora.em_atendimento.normal)}
              />
              <StatCard
                title="Preferencial — em atendimento"
                value={String(data.agora.em_atendimento.preferencial)}
                accent
              />
            </div>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Operador em atendimento</CardTitle>
                <CardDescription>
                  {data.operadores_atendendo.length
                    ? `${data.operadores_atendendo.length} ativo(s)`
                    : "Ninguém atendendo"}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {data.operadores_atendendo.map((o) => (
                  <div
                    key={o.operador_id}
                    className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm"
                  >
                    <span className="font-medium">{o.operador_nome}</span>
                    <span className="tabular-nums text-muted-foreground">
                      {o.senha} · {o.tipo}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle>Operador em pausa</CardTitle>
                <CardDescription>Status de pausa ainda não modelado</CardDescription>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">Ninguém em pausa</p>
              </CardContent>
            </Card>
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Média última hora
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
              <StatCard title="Atendimentos" value={String(data.ultima_hora.atendimentos)} />
              <StatCard title="Tempo espera" value={fmtMin(data.ultima_hora.tempo_espera_medio)} />
              <StatCard
                title="Tempo atendimento"
                value={fmtMin(data.ultima_hora.tempo_atendimento_medio)}
              />
              <StatCard title="Tempo total" value={fmtMin(data.ultima_hora.tempo_total_medio)} />
              <StatCard
                title="Desistência"
                value={fmtPct(data.ultima_hora.taxa_desistencia)}
                hint={`${data.ultima_hora.desistencias} senha(s)`}
              />
            </div>
          </section>

          <section className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
              Hoje
            </h2>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <StatCard title="Solicitações" value={String(data.hoje.solicitacoes)} />
              <StatCard title="Atendimentos" value={String(data.hoje.atendimentos)} />
              <StatCard
                title="Desistências"
                value={String(data.hoje.desistencias)}
                hint={fmtPct(data.hoje.taxa_desistencia)}
              />
              <StatCard title="Espera média" value={fmtMin(data.hoje.tempo_espera_medio)} />
            </div>
          </section>

          <Card>
            <CardHeader>
              <CardTitle>Solicitações na fila</CardTitle>
              <CardDescription>
                {data.fila.pendentes.length} aguardando · atualizado{" "}
                {new Date(data.atualizado_em).toLocaleTimeString("pt-BR")}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {data.fila.pendentes.map((s) => (
                  <span
                    key={s.id}
                    className={cn(
                      "rounded-md border px-2.5 py-1 font-mono text-sm",
                      s.tipo === "preferencial"
                        ? "border-primary/40 bg-primary/10"
                        : "bg-muted/40",
                    )}
                  >
                    {s.senha}
                  </span>
                ))}
                {!data.fila.pendentes.length ? (
                  <p className="text-sm text-muted-foreground">Fila vazia</p>
                ) : null}
              </div>
            </CardContent>
          </Card>
        </>
      ) : setorId ? (
        <p className="text-muted-foreground">Carregando…</p>
      ) : null}
    </div>
  );
}
