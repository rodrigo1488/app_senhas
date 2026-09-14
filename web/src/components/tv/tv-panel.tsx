"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { UserRound } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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
  const [setor, setSetor] = useState<TvSetor | null>(null);
  const [codigo, setCodigo] = useState(initialCodigo ?? "");
  const [bootstrapping, setBootstrapping] = useState(true);
  const [loggingIn, setLoggingIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [normal, setNormal] = useState<ChamadaTipo>({ senha: null, foto: null });
  const [preferencial, setPreferencial] = useState<ChamadaTipo>({ senha: null, foto: null });

  const [config, setConfig] = useState<TvConfig | null>(null);
  const [imagemIndex, setImagemIndex] = useState(0);

  const lastCallRef = useRef<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

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
      const [fila, tvConfig] = await Promise.all([
        tvApiFetch<TvFila>("/api/v1/setor/fila", { token: sessionToken }),
        tvApiFetch<TvConfig>("/api/v1/setor/tv_config", { token: sessionToken }).catch(
          () =>
            ({
              propagandas_ativas: false,
              imagens: [] as TvPropagandaImagem[],
              intervalo_ms: 15_000,
            }) satisfies TvConfig,
        ),
      ]);
      syncFromAtendimentos(fila.atendimentos ?? []);
      setConfig(tvConfig);
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

    socket.on("fila:atualizada", (data: { atendimentos?: TvAtendimento[] }) => {
      syncFromAtendimentos(data.atendimentos ?? []);
    });

    socket.on("senha:chamada", (data: SenhaChamadaTv) => {
      if (data.senha) playCallSound(data.senha);
      const chamada: ChamadaTipo = {
        senha: data.senha ?? null,
        foto: data.operador_foto ?? null,
      };
      if (data.tipo === "preferencial") setPreferencial(chamada);
      if (data.tipo === "normal") setNormal(chamada);
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

  useEffect(() => {
    if (imagens.length <= 1) return;
    const ms = Math.max(1000, config?.intervalo_ms ?? 15_000);
    const id = window.setInterval(() => {
      setImagemIndex((i) => (i + 1) % imagens.length);
    }, ms);
    return () => window.clearInterval(id);
  }, [imagens.length, config?.intervalo_ms]);

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

  function onLogout() {
    clearTvToken();
    setToken(null);
    setSetor(null);
    setConfig(null);
    setError(null);
  }

  const currentImage = useMemo(() => {
    const arquivo = imagens[imagemIndex]?.arquivo;
    return uploadsUrl(arquivo);
  }, [imagens, imagemIndex]);

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
            <p className="text-sm font-semibold uppercase tracking-[0.2em] text-primary">AppSenhas</p>
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
    <div className="relative h-screen w-screen overflow-hidden bg-black text-foreground">
      <button
        type="button"
        onClick={onLogout}
        className="absolute right-3 top-3 z-20 rounded-md bg-black/40 px-3 py-1 text-xs text-white opacity-40 transition hover:opacity-100"
        title="Sair"
      >
        Sair{setor?.nome ? ` · ${setor.nome}` : ""}
      </button>

      <div className="flex h-full w-full flex-col">
        <div className="relative min-h-0 flex-[78]">
          {currentImage ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={currentImage} alt="Propaganda" className="h-full w-full object-cover" />
          ) : (
            <div className="flex h-full items-center justify-center bg-zinc-950 text-white/40">
              Sem imagem de propaganda
            </div>
          )}
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
    </div>
  );
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
