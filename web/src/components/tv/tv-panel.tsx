"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TvFlowLayout } from "@/components/tv/tv-flow-layout";
import { TvMediaSlide } from "@/components/tv/tv-media-slide";
import { cn } from "@/lib/utils";
import {
  clearTvToken,
  getStoredTvToken,
  loginTv,
  tvApiFetch,
  uploadsUrl,
  type TvAtendimento,
  type TvConfig,
  type TvFila,
  type TvPropagandaImagem,
  type TvRecentCall,
  type TvRecentCallsResponse,
  type TvSenha,
  type TvSetor,
} from "@/lib/tv-api";
import { connectTvSocket, type SenhaChamadaTv } from "@/lib/tv-socket";

type Props = {
  initialCodigo?: string | null;
};

type ChamadaTipo = {
  senha: string | null;
  foto: string | null;
};

export function TvPanel({ initialCodigo }: Props) {
  const [token, setToken] = useState<string | null>(null);
  const [, setSetor] = useState<TvSetor | null>(null);
  const [codigo, setCodigo] = useState(initialCodigo ?? "");
  const [bootstrapping, setBootstrapping] = useState(true);
  const [loggingIn, setLoggingIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [normal, setNormal] = useState<ChamadaTipo>({ senha: null, foto: null });
  const [preferencial, setPreferencial] = useState<ChamadaTipo>({ senha: null, foto: null });

  const [config, setConfig] = useState<TvConfig | null>(null);
  const [imagemIndex, setImagemIndex] = useState(0);
  const [pendentes, setPendentes] = useState<TvSenha[]>([]);
  const [chamadas, setChamadas] = useState<TvRecentCall[]>([]);

  const lastCallRef = useRef<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const imagens = useMemo(() => config?.imagens ?? [], [config?.imagens]);

  const playCallSound = useCallback((senha: string) => {
    const normalized = senha.trim();
    if (!normalized || normalized === lastCallRef.current) return;
    lastCallRef.current = normalized;
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = 0;
    void audio.play().catch(() => {
      /* autoplay policies on some TVs — silent fail */
    });
  }, []);

  const syncFromAtendimentos = useCallback((lista: TvAtendimento[]) => {
    const n = lista.find((a) => a.tipo === "normal");
    const p = lista.find((a) => a.tipo === "preferencial");
    if (n) setNormal({ senha: n.senha, foto: n.operador_foto ?? null });
    if (p) setPreferencial({ senha: p.senha, foto: p.operador_foto ?? null });
  }, []);

  const hydrate = useCallback(
    async (sessionToken: string) => {
      const [fila, tvConfig, recentCalls] = await Promise.all([
        tvApiFetch<TvFila>("/api/v1/setor/fila", { token: sessionToken }),
        tvApiFetch<TvConfig>("/api/v1/setor/tv_config", { token: sessionToken }).catch(
          () =>
            ({
              propagandas_ativas: false,
              layout_tv_web: "propaganda",
              setor_nome: null,
              imagens: [] as TvPropagandaImagem[],
              intervalo_ms: 15_000,
            }) satisfies TvConfig,
        ),
        tvApiFetch<TvRecentCallsResponse>("/api/v1/setor/tv_chamadas_recentes", {
          token: sessionToken,
        }).catch(() => ({ chamadas: [] })),
      ]);
      syncFromAtendimentos(fila.atendimentos ?? []);
      setPendentes(fila.pendentes ?? []);
      setChamadas(recentCalls.chamadas ?? []);
      setConfig(tvConfig);
      setSetor((current) =>
        current ?? {
          id: fila.setor_id,
          nome: tvConfig.setor_nome || "Painel de atendimento",
        },
      );
      setImagemIndex(0);
    },
    [syncFromAtendimentos],
  );

  useEffect(() => {
    audioRef.current = new Audio("/sounds/call-chime.mp3");
    audioRef.current.preload = "auto";
    return () => {
      audioRef.current?.pause();
      audioRef.current = null;
    };
  }, []);

  useEffect(() => {
    const syncFullscreen = () => setIsFullscreen(tvIsFullscreen());
    document.addEventListener("fullscreenchange", syncFullscreen);
    document.addEventListener("webkitfullscreenchange", syncFullscreen);
    return () => {
      document.removeEventListener("fullscreenchange", syncFullscreen);
      document.removeEventListener("webkitfullscreenchange", syncFullscreen);
    };
  }, []);

  const toggleFullscreen = useCallback(() => {
    const panel = panelRef.current;
    if (!panel) return;
    if (tvIsFullscreen()) {
      void exitTvFullscreen();
      return;
    }
    void enterTvFullscreen(panel);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const stored = getStoredTvToken();
        if (stored) {
          await hydrate(stored);
          if (!cancelled) setToken(stored);
        } else if (initialCodigo?.trim()) {
          setLoggingIn(true);
          const result = await loginTv(initialCodigo.trim());
          if (cancelled) return;
          await hydrate(result.token);
          if (!cancelled) {
            setSetor(result.setor);
            setToken(result.token);
          }
        }
      } catch (e) {
        clearTvToken();
        if (!cancelled) {
          setToken(null);
          setError(e instanceof Error ? e.message : "Não foi possível entrar");
        }
      } finally {
        if (!cancelled) {
          setBootstrapping(false);
          setLoggingIn(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [hydrate, initialCodigo]);

  useEffect(() => {
    if (!token) return;
    const socket = connectTvSocket(token);

    socket.on("fila:atualizada", (data: { atendimentos?: TvAtendimento[]; pendentes?: TvSenha[] }) => {
      syncFromAtendimentos(data.atendimentos ?? []);
      setPendentes(data.pendentes ?? []);
    });

    socket.on("senha:chamada", (data: SenhaChamadaTv) => {
      if (data.senha) playCallSound(data.senha);
      const chamada: ChamadaTipo = {
        senha: data.senha ?? null,
        foto: data.operador_foto ?? null,
      };
      if (data.tipo === "preferencial") setPreferencial(chamada);
      if (data.tipo === "normal") setNormal(chamada);
      setChamadas((current) => {
        const next: TvRecentCall = {
          senha_id: data.senha_id ?? Date.now(),
          senha: data.senha,
          tipo: data.tipo ?? "normal",
          operador_id: data.operador_id,
          operador_nome: data.operador_nome,
          operador_foto: data.operador_foto,
          chamada_em: new Date().toISOString(),
          status: "atual",
        };
        return [
          next,
          ...current.filter((item) =>
            data.senha_id ? item.senha_id !== data.senha_id : item.senha !== data.senha,
          ),
        ].slice(0, 8);
      });
    });

    socket.on("tv:config_atualizada", (next: TvConfig) => {
      setConfig(next);
      setImagemIndex((i) => (next.imagens.length ? i % next.imagens.length : 0));
    });

    socket.on("auth:erro", (payload: { mensagem?: string }) => {
      setError(payload.mensagem || "Sessão inválida");
      clearTvToken();
      setToken(null);
    });

    return () => {
      socket.removeAllListeners();
      socket.disconnect();
    };
  }, [token, syncFromAtendimentos, playCallSound]);

  // Reserva: se o socket falhar atrás do túnel, a TV ainda acompanha as chamadas.
  useEffect(() => {
    if (!token) return;
    const refreshFila = () => {
      tvApiFetch<TvFila>("/api/v1/setor/fila", { token })
        .then((fila) => {
          syncFromAtendimentos(fila.atendimentos ?? []);
          setPendentes(fila.pendentes ?? []);
        })
        .catch(() => undefined);
      tvApiFetch<TvRecentCallsResponse>("/api/v1/setor/tv_chamadas_recentes", { token })
        .then((res) => setChamadas(res.chamadas ?? []))
        .catch(() => undefined);
    };
    const id = window.setInterval(refreshFila, 4000);
    return () => window.clearInterval(id);
  }, [token, syncFromAtendimentos]);

  const advanceMedia = useCallback(() => {
    setImagemIndex((i) => (imagens.length ? (i + 1) % imagens.length : 0));
  }, [imagens.length]);

  useEffect(() => {
    if (!token) return;
    const id = window.setInterval(() => {
      tvApiFetch<TvConfig>("/api/v1/setor/tv_config", { token })
        .then((next) => {
          setConfig(next);
          setImagemIndex((i) => (next.imagens.length ? i % next.imagens.length : 0));
        })
        .catch(() => undefined);
    }, 60_000);
    return () => window.clearInterval(id);
  }, [token]);

  async function onLogin(e: FormEvent) {
    e.preventDefault();
    setLoggingIn(true);
    setError(null);
    try {
      const result = await loginTv(codigo);
      await hydrate(result.token);
      setSetor(result.setor);
      setToken(result.token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha no login");
    } finally {
      setLoggingIn(false);
    }
  }

  const currentItem = imagens[imagemIndex] ?? null;
  const currentUrl = uploadsUrl(currentItem?.arquivo);
  const loopMedia = imagens.length <= 1;
  const layout = config?.layout_tv_web ?? "propaganda";

  const mediaSlide = (
    <TvMediaSlide
      item={currentItem}
      url={currentUrl}
      intervaloMs={config?.intervalo_ms ?? 15_000}
      onComplete={advanceMedia}
      loop={loopMedia}
      emptyLabel={layout === "fila" ? "Espaço de mídia" : "Sem mídia de propaganda"}
    />
  );

  if (bootstrapping) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background text-muted-foreground">
        Carregando painel…
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-b from-orange-50 to-zinc-100 p-6">
        <form
          onSubmit={onLogin}
          className="w-full max-w-md space-y-5 rounded-2xl border border-border bg-card p-8 shadow-sm"
        >
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">CompuFlow</p>
            <h1 className="mt-2 text-3xl font-bold tracking-tight">Painel da TV</h1>
            <p className="mt-1 text-muted-foreground">
              Entre com o código do setor para exibir as chamadas no navegador.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="codigo">Código do setor</Label>
            <Input
              id="codigo"
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
              autoFocus
              autoComplete="off"
              className="h-12 text-lg"
              placeholder="Ex.: SETOR"
            />
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button type="submit" className="h-12 w-full text-base" disabled={loggingIn || !codigo.trim()}>
            {loggingIn ? "Entrando…" : "Abrir painel"}
          </Button>
        </form>
      </div>
    );
  }

  return (
    <div
      ref={panelRef}
      className={cn(
        "relative h-screen w-screen overflow-hidden bg-black text-foreground",
        isFullscreen && "fixed inset-0 h-full w-full",
      )}
    >
      {layout === "fila" ? (
        <TvFlowLayout chamadas={chamadas} pendentes={pendentes} media={mediaSlide} />
      ) : (
      <div className="flex h-full w-full flex-col">
        <div className="relative min-h-0 flex-[78]">
          {mediaSlide}
        </div>

        <div className="flex min-h-0 flex-[22]">
          <TipoPanel
            titulo="PREFERENCIAL"
            senha={preferencial.senha}
            foto={preferencial.foto}
            className="bg-[#120B1E] text-white"
          />
          <TipoPanel
            titulo="NORMAL"
            senha={normal.senha}
            foto={normal.foto}
            className="bg-[#E85D04] text-white"
          />
        </div>
      </div>
      )}

      <button
        type="button"
        aria-label={isFullscreen ? "Sair da tela cheia" : "Tela cheia"}
        onClick={toggleFullscreen}
        className="absolute left-1/2 top-1/2 z-30 h-[min(28vmin,220px)] w-[min(28vmin,220px)] -translate-x-1/2 -translate-y-1/2 cursor-pointer rounded-full bg-transparent"
      />
    </div>
  );
}

type FullscreenElement = HTMLElement & {
  webkitRequestFullscreen?: () => Promise<void> | void;
  msRequestFullscreen?: () => Promise<void> | void;
};

type FullscreenDocument = Document & {
  webkitFullscreenElement?: Element | null;
  webkitExitFullscreen?: () => Promise<void> | void;
  msExitFullscreen?: () => Promise<void> | void;
};

function tvIsFullscreen() {
  const doc = document as FullscreenDocument;
  return Boolean(document.fullscreenElement || doc.webkitFullscreenElement);
}

function enterTvFullscreen(element: HTMLElement) {
  const el = element as FullscreenElement;
  const request =
    el.requestFullscreen?.bind(el) ||
    el.webkitRequestFullscreen?.bind(el) ||
    el.msRequestFullscreen?.bind(el);
  if (!request) return Promise.resolve();
  return Promise.resolve(request()).catch(() => undefined);
}

function exitTvFullscreen() {
  const doc = document as FullscreenDocument;
  const exit =
    document.exitFullscreen?.bind(document) ||
    doc.webkitExitFullscreen?.bind(doc) ||
    doc.msExitFullscreen?.bind(doc);
  if (!exit) return Promise.resolve();
  return Promise.resolve(exit()).catch(() => undefined);
}

function TipoPanel({
  titulo,
  senha,
  foto,
  className,
}: {
  titulo: string;
  senha: string | null;
  foto: string | null;
  className: string;
}) {
  const photo = uploadsUrl(foto);
  return (
    <div className={cn("flex flex-1 flex-col items-center justify-center px-6 py-3", className)}>
      <p className="text-lg font-bold tracking-[0.18em] sm:text-xl md:text-2xl">{titulo}</p>
      <div className="mt-2 flex items-center gap-4 sm:gap-5">
        <div className="flex h-14 w-14 shrink-0 items-center justify-center overflow-hidden rounded-full bg-white/15 sm:h-16 sm:w-16 md:h-20 md:w-20">
          {photo ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={photo} alt="" className="h-full w-full object-cover" />
          ) : (
            <UserRound className="h-8 w-8 opacity-80 sm:h-9 sm:w-9" />
          )}
        </div>
        <p
          className={cn(
            "font-black tracking-tight",
            senha ? "text-5xl sm:text-6xl md:text-7xl" : "text-4xl opacity-60 sm:text-5xl",
          )}
        >
          {senha ?? "—"}
        </p>
      </div>
    </div>
  );
}
