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
  type TvSenha,
  type TvSetor,
} from "@/lib/tv-api";
import { connectTvSocket, type SenhaChamadaTv } from "@/lib/tv-socket";

type Props = {
  initialCodigo?: string | null;
};

export function TvPanel({ initialCodigo }: Props) {
  const [token, setToken] = useState<string | null>(null);
  const [setor, setSetor] = useState<TvSetor | null>(null);
  const [codigo, setCodigo] = useState(initialCodigo ?? "");
  const [bootstrapping, setBootstrapping] = useState(true);
  const [loggingIn, setLoggingIn] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [pendentes, setPendentes] = useState<TvSenha[]>([]);
  const [ultimaSenha, setUltimaSenha] = useState<string | null>(null);
  const [ultimaOperador, setUltimaOperador] = useState<string | null>(null);
  const [ultimaOperadorFoto, setUltimaOperadorFoto] = useState<string | null>(null);
  const [ultimaNormal, setUltimaNormal] = useState<string | null>(null);
  const [ultimaPreferencial, setUltimaPreferencial] = useState<string | null>(null);

  const [config, setConfig] = useState<TvConfig | null>(null);
  const [imagemIndex, setImagemIndex] = useState(0);

  const lastCallRef = useRef<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const imagens = useMemo(() => config?.imagens ?? [], [config?.imagens]);
  const showPropaganda = Boolean(config?.propagandas_ativas && imagens.length > 0);

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
    const first = lista[0];
    setUltimaSenha(first?.senha ?? null);
    setUltimaOperador(first?.operador_nome ?? null);
    setUltimaOperadorFoto(first?.operador_foto ?? null);
    const normal = lista.find((a) => a.tipo === "normal");
    const preferencial = lista.find((a) => a.tipo === "preferencial");
    if (normal) setUltimaNormal(normal.senha);
    if (preferencial) setUltimaPreferencial(preferencial.senha);
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
      setPendentes(fila.pendentes ?? []);
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

    socket.on("fila:atualizada", (data: { pendentes?: TvSenha[]; atendimentos?: TvAtendimento[] }) => {
      setPendentes(data.pendentes ?? []);
      syncFromAtendimentos(data.atendimentos ?? []);
    });

    socket.on("senha:chamada", (data: SenhaChamadaTv) => {
      if (data.senha) {
        setUltimaSenha(data.senha);
        playCallSound(data.senha);
      }
      if (data.operador_nome) setUltimaOperador(data.operador_nome);
      if (data.operador_foto !== undefined) setUltimaOperadorFoto(data.operador_foto ?? null);
      if (data.tipo === "preferencial") setUltimaPreferencial(data.senha);
      if (data.tipo === "normal") setUltimaNormal(data.senha);
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
    if (!showPropaganda || imagens.length <= 1) return;
    const ms = Math.max(1000, config?.intervalo_ms ?? 15_000);
    const id = window.setInterval(() => {
      setImagemIndex((i) => (i + 1) % imagens.length);
    }, ms);
    return () => window.clearInterval(id);
  }, [showPropaganda, imagens.length, config?.intervalo_ms]);

  // Recarrega config de propaganda periodicamente (sem socket dedicado).
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
    setPendentes([]);
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
    <div className="relative min-h-screen bg-background text-foreground">
      <button
        type="button"
        onClick={onLogout}
        className="absolute right-3 top-3 z-20 rounded-md bg-black/40 px-3 py-1 text-xs text-white opacity-40 transition hover:opacity-100"
        title="Sair"
      >
        Sair{setor?.nome ? ` · ${setor.nome}` : ""}
      </button>

      {showPropaganda ? (
        <PropagandaLayout
          imageUrl={currentImage}
          preferencial={ultimaPreferencial}
          normal={ultimaNormal}
        />
      ) : (
        <DefaultLayout
          senha={ultimaSenha}
          operadorNome={ultimaOperador}
          operadorFoto={ultimaOperadorFoto}
          pendentes={pendentes}
          error={error}
        />
      )}
    </div>
  );
}

function PropagandaLayout({
  imageUrl,
  preferencial,
  normal,
}: {
  imageUrl: string | null;
  preferencial: string | null;
  normal: string | null;
}) {
  return (
    <div className="flex h-screen w-screen flex-col">
      <div className="relative flex-[0.78] bg-black">
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={imageUrl} alt="Propaganda" className="h-full w-full object-cover" />
        ) : null}
      </div>
      <div className="flex flex-[0.22]">
        <TipoPanel titulo="PREFERENCIAL" senha={preferencial} className="bg-[#1A1A1A] text-[#F5F5F5]" />
        <TipoPanel titulo="NORMAL" senha={normal} className="bg-[#E85D04] text-white" />
      </div>
    </div>
  );
}

function TipoPanel({
  titulo,
  senha,
  className,
}: {
  titulo: string;
  senha: string | null;
  className: string;
}) {
  return (
    <div className={cn("flex flex-1 flex-col items-center justify-center px-6 py-4", className)}>
      <p className="text-xl font-semibold tracking-[0.2em] opacity-85 sm:text-2xl">{titulo}</p>
      <p className={cn("mt-1 font-black tracking-tight", senha ? "text-6xl sm:text-7xl" : "text-5xl")}>
        {senha ?? "—"}
      </p>
    </div>
  );
}

function DefaultLayout({
  senha,
  operadorNome,
  operadorFoto,
  pendentes,
  error,
}: {
  senha: string | null;
  operadorNome: string | null;
  operadorFoto: string | null;
  pendentes: TvSenha[];
  error: string | null;
}) {
  const photo = uploadsUrl(operadorFoto);
  return (
    <div className="grid h-screen w-screen grid-cols-1 gap-6 p-6 lg:grid-cols-[1.65fr_1fr] lg:p-8">
      <section className="flex flex-col items-center justify-center rounded-3xl border border-border bg-card p-8 shadow-sm">
        <p className="text-xl font-semibold tracking-[0.25em] text-primary">SENHA ATUAL</p>
        <p
          className={cn(
            "my-5 text-center font-black leading-none tracking-tight",
            senha ? "text-7xl sm:text-8xl lg:text-[6.5rem]" : "text-5xl text-muted-foreground",
          )}
        >
          {senha ?? "Aguardando"}
        </p>
        {operadorNome ? (
          <div className="flex items-center gap-4 rounded-2xl bg-secondary px-5 py-3">
            <div className="flex h-16 w-16 items-center justify-center overflow-hidden rounded-full border-2 border-primary bg-card">
              {photo ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={photo} alt={operadorNome} className="h-full w-full object-cover" />
              ) : (
                <UserRound className="h-9 w-9 text-primary" />
              )}
            </div>
            <div>
              <p className="text-sm text-muted-foreground">DIRIJA-SE A</p>
              <p className="text-2xl font-bold">{operadorNome}</p>
            </div>
          </div>
        ) : (
          <p className="text-xl text-muted-foreground">A próxima chamada aparecerá aqui</p>
        )}
      </section>

      <section className="flex min-h-0 flex-col rounded-3xl border border-border bg-card p-6">
        <h2 className="text-2xl font-bold">FILA DE ESPERA</h2>
        <p className="mb-4 mt-1 text-muted-foreground">
          {pendentes.length} {pendentes.length === 1 ? "senha aguardando" : "senhas aguardando"}
        </p>
        <ul className="min-h-0 flex-1 space-y-2.5 overflow-y-auto pr-1">
          {pendentes.map((item) => {
            const preferential = item.tipo === "preferencial";
            return (
              <li
                key={item.id}
                className="flex items-center justify-between rounded-xl bg-secondary px-4 py-3"
              >
                <span className="text-2xl font-bold">{item.senha}</span>
                <span
                  className={cn(
                    "text-sm font-bold",
                    preferential ? "text-destructive" : "text-primary",
                  )}
                >
                  {preferential ? "PREFERENCIAL" : "NORMAL"}
                </span>
              </li>
            );
          })}
        </ul>
        {error ? <p className="mt-3 text-sm text-destructive">{error}</p> : null}
      </section>
    </div>
  );
}
