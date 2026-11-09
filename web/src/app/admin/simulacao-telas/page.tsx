"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch, type SimulacaoMidia, type SimulacaoTela } from "@/lib/api";
import { cn } from "@/lib/utils";

function rotuloModo(tela: SimulacaoTela): string {
  if (tela.modo === "fila") return "Fluxo de chamadas";
  if (tela.modo === "streaming") return "Tela cheia de mídia";
  return "Propagandas + chamadas";
}

function rotuloPapelTablet(papel: string): string {
  if (papel === "operador") return "operador";
  if (papel === "avaliacao") return "avaliação";
  if (papel === "cliente") return "cliente";
  return papel;
}

function descricaoTela(tela: SimulacaoTela, midias: number): string {
  const partes = [rotuloFormato(tela), rotuloModo(tela)];
  if (midias) partes.push(`${midias} mídia(s)`);
  const ips = (tela.ips || []).filter(Boolean);
  if (ips.length === 1) partes.push(`IP ${ips[0]}`);
  else if (ips.length > 1) partes.push(`IPs ${ips.join(", ")}`);
  const tablets = tela.tablets || [];
  if (tablets.length) {
    partes.push(
      `Tablets ${tablets.map((item) => `${item.ip} (${rotuloPapelTablet(item.papel)})`).join(", ")}`,
    );
  }
  return partes.join(" · ");
}

function rotuloFormato(tela: SimulacaoTela): string {
  const base = tela.formato === "vertical" ? "Vertical" : "Horizontal";
  if (tela.tipo === "streaming" && tela.rotacao_tv) {
    return `${base} · ${tela.rotacao_tv}°`;
  }
  return base;
}

function SimulacaoSlide({ midias, intervaloMs }: { midias: SimulacaoMidia[]; intervaloMs: number }) {
  const [indice, setIndice] = useState(0);
  const atual = midias.length ? midias[indice % midias.length] : null;

  useEffect(() => {
    setIndice(0);
  }, [midias.map((item) => `${item.id}:${item.url}`).join("|")]);

  useEffect(() => {
    if (midias.length <= 1) return;
    if ((atual?.tipo || "image") === "video") return;
    const id = window.setTimeout(() => {
      setIndice((value) => (value + 1) % midias.length);
    }, Math.max(2000, intervaloMs));
    return () => window.clearTimeout(id);
  }, [atual?.id, atual?.tipo, atual?.url, intervaloMs, midias.length]);

  if (!atual?.url) {
    return (
      <div className="flex h-full items-center justify-center bg-zinc-950 text-[10px] text-white/40">
        Sem mídia no ar
      </div>
    );
  }

  if ((atual.tipo || "image") === "video") {
    return (
      <video
        key={`${atual.id}-${atual.url}`}
        src={atual.url}
        className="h-full w-full object-cover"
        muted
        playsInline
        autoPlay
        onEnded={() => setIndice((value) => (value + 1) % Math.max(midias.length, 1))}
      />
    );
  }

  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={atual.url} alt="" className="h-full w-full object-cover" />
  );
}

function TelaCard({ tela }: { tela: SimulacaoTela }) {
  const vertical = tela.formato === "vertical";
  const senhasNoTopo = (tela.posicao_senhas_tv ?? "superior") !== "inferior";
  const midias = tela.propagandas_ativas || tela.tipo === "streaming" ? tela.midias : [];
  const faixaSenhas = (
    <div className={cn("flex min-h-0 flex-[3]", vertical ? "flex-col" : "flex-row")}>
      <div className="flex flex-1 flex-col items-center justify-center bg-[#120B1E] text-white">
        <p className="text-[8px] font-bold tracking-widest">PREFERENCIAL</p>
        <p className="text-lg font-black leading-none">{tela.senha_preferencial || "—"}</p>
      </div>
      <div className="flex flex-1 flex-col items-center justify-center bg-[#E85D04] text-white">
        <p className="text-[8px] font-bold tracking-widest">NORMAL</p>
        <p className="text-lg font-black leading-none">{tela.senha_normal || "—"}</p>
      </div>
    </div>
  );

  return (
    <article className="space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-semibold">{tela.nome}</p>
          <p className="truncate text-xs text-muted-foreground">{tela.subtitulo}</p>
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium",
            tela.is_online ? "bg-emerald-100 text-emerald-800" : "bg-muted text-muted-foreground",
          )}
        >
          {tela.is_online ? "Ao vivo" : "Offline"}
        </span>
      </div>
      <div
        className={cn(
          "overflow-hidden rounded-xl border bg-black shadow-sm",
          vertical ? "mx-auto w-[min(100%,220px)]" : "w-full",
        )}
        style={{ aspectRatio: vertical ? "9 / 16" : "16 / 9" }}
      >
        {tela.modo === "streaming" ? (
          <SimulacaoSlide midias={midias} intervaloMs={tela.intervalo_ms} />
        ) : tela.modo === "fila" ? (
          <div className={cn("flex h-full bg-[#e7e3dc]", vertical ? "flex-col" : "flex-row")}>
            <div className={cn("min-h-0 min-w-0", vertical ? "flex-[1.05]" : "flex-[2]")}>
              <SimulacaoSlide midias={midias} intervaloMs={tela.intervalo_ms} />
            </div>
            <div className="flex min-h-0 min-w-0 flex-1 flex-col justify-center bg-[#f4f1ea] p-2">
              <p className="text-[9px] font-bold uppercase tracking-wider text-muted-foreground">Chamando agora</p>
              <p className="text-2xl font-black leading-none text-[#e85d04]">{tela.chamada_atual || "—"}</p>
              <p className="mt-1 text-[10px] text-muted-foreground">
                {tela.chamada_atual_tipo === "preferencial" ? "Preferencial" : tela.chamada_atual ? "Normal" : "Aguardando"}
              </p>
              {tela.proximas.length ? (
                <p className="mt-1 truncate text-[10px] text-muted-foreground">
                  Próximas: {tela.proximas.join(" · ")}
                </p>
              ) : null}
            </div>
          </div>
        ) : (
          <div className="flex h-full flex-col">
            {senhasNoTopo ? faixaSenhas : null}
            <div className="min-h-0 flex-[7]">
              <SimulacaoSlide midias={midias} intervaloMs={tela.intervalo_ms} />
            </div>
            {!senhasNoTopo ? faixaSenhas : null}
          </div>
        )}
      </div>
      <p className="text-xs text-muted-foreground">{descricaoTela(tela, midias.length)}</p>
    </article>
  );
}

export default function SimulacaoTelasPage() {
  const [telas, setTelas] = useState<SimulacaoTela[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filtro, setFiltro] = useState<"todas" | "setor" | "streaming">("todas");

  useEffect(() => {
    let ativo = true;
    async function load() {
      try {
        const data = await apiFetch<SimulacaoTela[]>("/api/v1/admin/tvs/simulacao");
        if (ativo) {
          setTelas(data);
          setError(null);
        }
      } catch (err) {
        if (ativo) setError(err instanceof Error ? err.message : "Erro ao carregar telas");
      }
    }
    void load();
    const timer = window.setInterval(() => void load(), 5000);
    return () => {
      ativo = false;
      window.clearInterval(timer);
    };
  }, []);

  const aparelhos = useMemo(() => telas.filter((tela) => tela.tipo === "tablet"), [telas]);
  const visiveis = useMemo(() => {
    const paineis = telas.filter((tela) => tela.tipo !== "tablet");
    if (filtro === "todas") return paineis;
    return paineis.filter((tela) => tela.tipo === filtro);
  }, [filtro, telas]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Simulação de telas</h1>
        <p className="text-muted-foreground">
          Prévia do que cada TV está exibindo agora, no formato horizontal ou vertical e no layout
          configurado. O IP de cada TV e tablet aparece na descrição.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {(
          [
            ["todas", "Todas"],
            ["setor", "Painéis de senha"],
            ["streaming", "Streaming"],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={cn(
              "rounded-full border px-3 py-1 text-sm",
              filtro === id ? "border-primary bg-accent" : "border-input",
            )}
            onClick={() => setFiltro(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-destructive">{error}</p>}

      <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3">
        {visiveis.map((tela) => (
          <TelaCard key={tela.chave} tela={tela} />
        ))}
      </div>
      {!visiveis.length && !error ? (
        <p className="text-sm text-muted-foreground">Nenhuma tela para simular neste filtro.</p>
      ) : null}

      <section className="space-y-3">
        <div>
          <h2 className="text-lg font-semibold">Tablets</h2>
          <p className="text-sm text-muted-foreground">
            Cliente, operador e avaliação conectados, com o IP de cada aparelho.
          </p>
        </div>
        {aparelhos.length ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {aparelhos.map((tablet) => (
              <article key={tablet.chave} className="rounded-xl border bg-card p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <p className="truncate font-semibold">{tablet.nome}</p>
                    <p className="truncate text-xs text-muted-foreground">{tablet.subtitulo}</p>
                  </div>
                  <span
                    className={cn(
                      "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium",
                      tablet.is_online ? "bg-emerald-100 text-emerald-800" : "bg-muted text-muted-foreground",
                    )}
                  >
                    {tablet.is_online ? "Ao vivo" : "Offline"}
                  </span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">
                  {tablet.ips?.length ? `IP ${tablet.ips.join(", ")}` : "IP não informado"}
                </p>
              </article>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted-foreground">Nenhum tablet informou o IP ainda.</p>
        )}
      </section>
    </div>
  );
}
