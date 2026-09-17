"use client";

import { FormEvent, useEffect, useState, type Dispatch, type SetStateAction } from "react";
import { Bell, BellOff, CheckCircle2, Ticket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { RatingStars } from "@/components/cliente/rating-stars";
import { ClienteEsperaSlideshow } from "@/components/cliente/cliente-espera-slideshow";
import {
  connectTicketSocket,
  parseClienteConfig,
  type ClienteConfig,
  type PedidoStatus,
  type SenhaChamada,
  type SenhaPosicao,
} from "@/lib/cliente-socket";
import { subscribePush } from "@/lib/web-push";
import { ModeToggle } from "@/components/mode-toggle";
import { cn } from "@/lib/utils";

type Props = { token: string };

type PushState = "idle" | "loading" | "on" | "local-only" | "denied" | "unsupported";

function normalizePosicao(data: Record<string, unknown>, token: string): SenhaPosicao {
  const status = String(data.status || "A");
  return {
    token_unico: String(data.token_unico || token),
    posicao:
      typeof data.posicao === "number" ? data.posicao : status === "C" ? 0 : status === "F" ? -1 : 0,
    senha: String(data.senha || ""),
    status,
    setor_nome: String(data.setor_nome || data.setor || "Fila"),
    tem_pedido: Boolean(data.tem_pedido),
    pedido: data.pedido == null ? null : String(data.pedido),
    pedido_confirmado: Boolean(data.pedido_confirmado),
    avaliacao_pendente:
      typeof data.avaliacao_pendente === "boolean" ? data.avaliacao_pendente : undefined,
  };
}

async function fetchPosicao(token: string): Promise<{ pos: SenhaPosicao; midias: ClienteConfig }> {
  const res = await fetch(`/api/verificar_senha/${encodeURIComponent(token)}`, {
    cache: "no-store",
  });
  const data = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (!res.ok) throw new Error(String(data.error || "Senha não encontrada"));
  return { pos: normalizePosicao(data, token), midias: parseClienteConfig(data) };
}

function applyPosicao(
  data: SenhaPosicao,
  token: string,
  setPos: (p: SenhaPosicao) => void,
  setChamada: Dispatch<SetStateAction<SenhaChamada | null>>,
  setAvaliado: (v: boolean) => void,
  setPedidoText: (v: string) => void,
) {
  setPos(data);
  if (data.status === "C") {
    setChamada((prev) => prev ?? { ticket_token: token, senha: data.senha });
  }
  if (data.status === "F") {
    setChamada(null);
    if (data.avaliacao_pendente === false) setAvaliado(true);
  }
  if (data.status === "A" && data.pedido) {
    setPedidoText(data.pedido);
  }
}

export function TicketTracker({ token }: Props) {
  const [pos, setPos] = useState<SenhaPosicao | null>(null);
  const [chamada, setChamada] = useState<SenhaChamada | null>(null);
  const [pedidoMsg, setPedidoMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [pushState, setPushState] = useState<PushState>("idle");
  const [pedidoText, setPedidoText] = useState("");
  const [pedidoSaving, setPedidoSaving] = useState(false);
  const [nota, setNota] = useState<number | null>(null);
  const [avaliado, setAvaliado] = useState(false);
  const [avaliando, setAvaliando] = useState(false);
  const [midias, setMidias] = useState<ClienteConfig | null>(null);

  useEffect(() => {
    if (!("Notification" in window)) {
      setPushState("unsupported");
      return;
    }
    if (Notification.permission === "denied") {
      setPushState("denied");
      return;
    }
    if (Notification.permission === "granted") {
      setPushState("loading");
      subscribePush(token)
        .then((result) => setPushState(result === "granted" ? "on" : result))
        .catch(() => setPushState("local-only"));
    }
  }, [token]);

  // Hidratação REST (funciona mesmo se o socket falhar no celular)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await fetchPosicao(token);
        if (cancelled) return;
        applyPosicao(
          data.pos,
          token,
          setPos,
          setChamada,
          setAvaliado,
          setPedidoText,
        );
        setMidias(data.midias);
        setError(null);
      } catch {
        if (!cancelled) setError("Não foi possível carregar a senha");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  // Reserva ao tempo real: posição correta mesmo se o proxy/rede interromper o Socket.IO.
  useEffect(() => {
    const id = window.setInterval(() => {
      fetchPosicao(token)
        .then((data) => {
          applyPosicao(data.pos, token, setPos, setChamada, setAvaliado, setPedidoText);
          setMidias(data.midias);
        })
        .catch(() => undefined);
    }, 8_000);
    return () => window.clearInterval(id);
  }, [token]);

  useEffect(() => {
    const socket = connectTicketSocket(token);

    socket.on("senha:posicao", (data: SenhaPosicao) => {
      applyPosicao(data, token, setPos, setChamada, setAvaliado, setPedidoText);
      setError(null);
      setLoading(false);
    });

    socket.on("senha:chamada", (data: SenhaChamada) => {
      setChamada(data);
      setPos((prev) =>
        prev
          ? { ...prev, status: "C", posicao: 0, senha: data.senha || prev.senha }
          : {
              token_unico: token,
              posicao: 0,
              senha: data.senha,
              status: "C",
              setor_nome: "Fila",
              tem_pedido: Boolean(data.tem_pedido),
              pedido: data.pedido ?? null,
              pedido_confirmado: false,
            },
      );
      if ("Notification" in window && Notification.permission === "granted") {
        try {
          new Notification(`Senha ${data.senha}: sua vez!`, {
            body: data.operador_nome
              ? `Dirija-se ao atendimento com ${data.operador_nome}.`
              : "Dirija-se ao atendimento.",
          });
        } catch {
          /* Alguns navegadores móveis só exibem notificações via Service Worker. */
        }
      }
      setLoading(false);
    });

    socket.on("pedido:status", (data: PedidoStatus) => {
      setPedidoMsg(data.mensagem || "Pedido sendo preparado");
    });

    socket.on("cliente:config_atualizada", (data: ClienteConfig) => {
      setMidias(parseClienteConfig(data));
    });

    socket.on("auth:erro", (payload: { mensagem?: string }) => {
      setError(payload?.mensagem || "Não foi possível autenticar esta senha");
      setLoading(false);
    });

    // Falha de socket não alarma: REST já hidrata e faz poll a cada 8s.
    socket.on("connect_error", () => undefined);

    return () => {
      socket.removeAllListeners();
      socket.disconnect();
    };
  }, [token]);

  async function ativarPush() {
    setPushState("loading");
    try {
      const result = await subscribePush(token);
      if (result === "granted") setPushState("on");
      else setPushState(result);
    } catch {
      setPushState("unsupported");
    }
  }

  async function enviarPedido(e: FormEvent) {
    e.preventDefault();
    const texto = pedidoText.trim();
    if (!texto) return;
    setPedidoSaving(true);
    try {
      const res = await fetch(`/api/salvar_pedido/${encodeURIComponent(token)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pedido: texto }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.error || "Erro ao salvar pedido");
      }
      setPos((prev) => (prev ? { ...prev, tem_pedido: true, pedido: texto } : prev));
      setPedidoMsg("Pedido enviado com sucesso. Aguarde a confirmação do atendente.");
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar pedido");
    } finally {
      setPedidoSaving(false);
    }
  }

  async function enviarAvaliacao(n: number) {
    setNota(n);
    setAvaliando(true);
    try {
      const res = await fetch(`/api/avaliar/${encodeURIComponent(token)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ nota: n }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Erro ao avaliar");
      setAvaliado(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao avaliar");
    } finally {
      setAvaliando(false);
    }
  }

  const status = pos?.status ?? "…";
  const finalizado = status === "F";
  const chamado = status === "C" || (Boolean(chamada) && !finalizado);
  const perto = status === "A" && typeof pos?.posicao === "number" && pos.posicao > 0 && pos.posicao <= 3;
  const aguardando = status === "A" && !perto;
  const notFound = Boolean(error && !pos && !loading);

  let titulo = loading ? "Carregando…" : "Aguardando";
  let subtitulo = loading ? "Buscando sua senha" : "Conectando à fila";
  if (notFound) {
    titulo = "Senha indisponível";
    subtitulo = error || "Token inválido";
  } else if (finalizado) {
    titulo = avaliado ? "Obrigado!" : "Atendimento finalizado";
    subtitulo = avaliado ? "Sua avaliação foi registrada." : "Como foi o atendimento?";
  } else if (chamado) {
    titulo = "Sua vez!";
    subtitulo = chamada?.operador_nome
      ? `Dirija-se ao atendimento · ${chamada.operador_nome}`
      : "Dirija-se ao atendimento";
  } else if (perto) {
    titulo = "Quase lá";
    subtitulo = `${pos?.posicao} à frente — fique por perto`;
  } else if (aguardando && pos) {
    titulo = "Aguardando";
    subtitulo =
      pos.posicao === 0
        ? "Você é o próximo"
        : `${pos.posicao} ${pos.posicao === 1 ? "pessoa" : "pessoas"} à frente`;
  }

  return (
    <div className="relative flex min-h-svh flex-col bg-background">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_oklch(0.75_0.15_55_/_0.22),_transparent_55%)] dark:bg-[radial-gradient(ellipse_at_top,_oklch(0.45_0.12_55_/_0.3),_transparent_55%)]"
      />
      <header className="relative z-10 flex items-center justify-between px-4 py-3">
        <div className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
          <Ticket className="h-4 w-4 text-primary" />
          CompuFlow
        </div>
        <ModeToggle />
      </header>

      <main className="relative z-10 mx-auto flex w-full max-w-md flex-1 flex-col items-center justify-center gap-8 px-6 pb-16 pt-4 text-center">
        <div className="space-y-2">
          <p className="text-sm uppercase tracking-[0.2em] text-muted-foreground">
            {pos?.setor_nome || "Fila"}
          </p>
          <p
            className={cn(
              "font-bold tracking-tight text-foreground",
              (pos?.senha?.length || 0) > 5 ? "text-5xl" : "text-6xl",
            )}
          >
            {pos?.senha || "—"}
          </p>
          <h1 className="text-2xl font-semibold tracking-tight">{titulo}</h1>
          <p className="text-muted-foreground">{subtitulo}</p>
        </div>

        {status === "A" && midias?.imagens.length ? (
          <ClienteEsperaSlideshow config={midias} />
        ) : null}

        {(pedidoMsg || pos?.tem_pedido) && !finalizado ? (
          <p className="flex w-full items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-left text-sm text-emerald-800 dark:text-emerald-200">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            {pedidoMsg || "Pedido enviado. Aguarde a confirmação do atendente."}
          </p>
        ) : null}

        {pos && !finalizado && !chamado ? (
          <div className="flex w-full flex-col gap-3 rounded-2xl border bg-card/80 p-4 text-left shadow-sm">
            {pushState === "idle" ? (
              <div>
                <p className="font-medium">Receba um aviso quando chegar sua vez</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Ative as notificações para não precisar acompanhar a tela o tempo todo.
                </p>
              </div>
            ) : null}
            <Button
              type="button"
              variant={pushState === "on" ? "secondary" : "default"}
              className="w-full"
              disabled={pushState === "loading" || pushState === "on" || pushState === "local-only"}
              onClick={ativarPush}
            >
              {pushState === "on" ? (
                <>
                  <Bell className="h-4 w-4" /> Notificações ativas
                </>
              ) : pushState === "local-only" ? (
                <>
                  <Bell className="h-4 w-4" /> Avisos ativos nesta tela
                </>
              ) : pushState === "loading" ? (
                "Ativando…"
              ) : (
                <>
                  <Bell className="h-4 w-4" /> Ativar notificações
                </>
              )}
            </Button>
            {pushState === "local-only" ? (
              <p className="text-center text-xs text-muted-foreground">
                Para avisos com a página fechada, configure as chaves VAPID no servidor.
              </p>
            ) : null}
            {pushState === "denied" || pushState === "unsupported" ? (
              <p className="flex items-center justify-center gap-1 text-xs text-muted-foreground">
                <BellOff className="h-3.5 w-3.5" />
                {pushState === "denied"
                  ? "Permissão negada no navegador"
                  : "Este navegador não suporta notificações"}
              </p>
            ) : null}
          </div>
        ) : null}

        {status === "A" && pos && !pos.tem_pedido && !pos.pedido_confirmado ? (
          <form onSubmit={enviarPedido} className="flex w-full flex-col gap-2 text-left">
            <label className="text-xs font-medium text-muted-foreground" htmlFor="pedido">
              Pedido (opcional)
            </label>
            <div className="flex gap-2">
              <Input
                id="pedido"
                value={pedidoText}
                onChange={(e) => setPedidoText(e.target.value)}
                placeholder="Ex.: 2 pães"
                disabled={pedidoSaving}
              />
              <Button type="submit" variant="outline" disabled={pedidoSaving || !pedidoText.trim()}>
                Enviar
              </Button>
            </div>
          </form>
        ) : null}

        {finalizado && !avaliado ? (
          <div className="w-full space-y-4">
            <RatingStars value={nota} onChange={enviarAvaliacao} disabled={avaliando} />
          </div>
        ) : null}

        {error && pos ? <p className="text-sm text-muted-foreground">{error}</p> : null}
      </main>
    </div>
  );
}
