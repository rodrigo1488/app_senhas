"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Check, ImageIcon, MonitorPlay, Tv } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, type Propaganda, type TvAdmin } from "@/lib/api";

function midiaTipo(item: Propaganda): "image" | "video" {
  return item.tipo === "video" ? "video" : "image";
}

export default function PropagandasPage() {
  const [itens, setItens] = useState<Propaganda[]>([]);
  const [tvs, setTvs] = useState<TvAdmin[]>([]);
  const [arquivos, setArquivos] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [tvAtiva, setTvAtiva] = useState<TvAdmin | null>(null);
  const [midiasTv, setMidiasTv] = useState<Set<number>>(new Set());
  const [savingTv, setSavingTv] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    const [midias, tvsResponse] = await Promise.all([
      apiFetch<Propaganda[]>("/api/v1/admin/propagandas"),
      apiFetch<TvAdmin[]>("/api/v1/admin/tvs"),
    ]);
    setItens(midias);
    setTvs(tvsResponse);
  }

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);

  useEffect(() => {
    const timer = window.setInterval(() => {
      if (tvAtiva) return;
      apiFetch<TvAdmin[]>("/api/v1/admin/tvs")
        .then(setTvs)
        .catch(() => {});
    }, 5000);
    return () => window.clearInterval(timer);
  }, [tvAtiva]);

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!arquivos.length) {
      setError("Selecione uma ou mais imagens ou vídeos MP4");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      for (const arquivo of arquivos) {
        form.append("arquivo", arquivo);
      }
      await apiFetch("/api/v1/admin/propagandas", { method: "POST", body: form });
      setArquivos([]);
      if (fileInputRef.current) fileInputRef.current.value = "";
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao enviar");
    } finally {
      setLoading(false);
    }
  }

  async function toggleAtivo(item: Propaganda) {
    await apiFetch(`/api/v1/admin/propagandas/${item.id}`, {
      method: "PUT",
      body: JSON.stringify({ ativo: !item.ativo }),
    });
    await load();
  }

  async function move(item: Propaganda, delta: number) {
    await apiFetch(`/api/v1/admin/propagandas/${item.id}`, {
      method: "PUT",
      body: JSON.stringify({ ordem: item.ordem + delta }),
    });
    await load();
  }

  async function onDelete(id: number) {
    if (!confirm("Remover esta mídia?")) return;
    await apiFetch(`/api/v1/admin/propagandas/${id}`, { method: "DELETE" });
    await load();
  }

  function abrirTv(tv: TvAdmin) {
    setTvAtiva(tv);
    setMidiasTv(new Set(tv.propaganda_ids));
  }

  function toggleMidiaTv(id: number) {
    setMidiasTv((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function salvarTv() {
    if (!tvAtiva) return;
    setSavingTv(true);
    setError(null);
    try {
      await apiFetch("/api/v1/admin/tvs/midias", {
        method: "PUT",
        body: JSON.stringify({
          tipo: tvAtiva.tipo,
          id: tvAtiva.id,
          propaganda_ids: itens.filter((item) => midiasTv.has(item.id)).map((item) => item.id),
        }),
      });
      setTvAtiva(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao enviar mídias para a TV");
    } finally {
      setSavingTv(false);
    }
  }

  const setores = useMemo(() => tvs.filter((tv) => tv.tipo === "setor"), [tvs]);
  const streaming = useMemo(() => tvs.filter((tv) => tv.tipo === "streaming"), [tvs]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Mídias e TVs</h1>
        <p className="text-muted-foreground">
          Suba a biblioteca e clique na TV para escolher o que aparece nela. TVs de
          propagandas do app aparecem ao abrir <strong>TV DE PROPAGANDAS</strong> no
          setor (<code>/smart</code> e <code>/legacy</code> continuam válidos).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Biblioteca</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4" onSubmit={onUpload}>
            <div className="space-y-2">
              <Label>Arquivos (PNG, JPG, WEBP, GIF até 5MB ou MP4 até 80MB cada)</Label>
              <Input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/png,image/jpeg,image/webp,image/gif,video/mp4"
                onChange={(e) => setArquivos(Array.from(e.target.files || []))}
              />
              {arquivos.length > 0 && (
                <p className="text-sm text-muted-foreground">
                  {arquivos.length === 1
                    ? arquivos[0].name
                    : `${arquivos.length} arquivos selecionados`}
                </p>
              )}
              {arquivos.length > 1 && (
                <ul className="max-h-32 space-y-1 overflow-y-auto text-xs text-muted-foreground">
                  {arquivos.map((arquivo) => (
                    <li key={`${arquivo.name}-${arquivo.size}-${arquivo.lastModified}`}>{arquivo.name}</li>
                  ))}
                </ul>
              )}
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" disabled={loading || !arquivos.length} className="w-fit">
              {loading
                ? "Enviando..."
                : arquivos.length > 1
                  ? `Adicionar ${arquivos.length} mídias`
                  : "Adicionar à biblioteca"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <TvGroup
        title="TVs de senha (setores)"
        empty="Cadastre um setor. Ao abrir o painel da TV, ela fica online e você escolhe as mídias aqui."
        tvs={setores}
        onSelect={abrirTv}
      />

      <TvGroup
        title="TVs de streaming"
        empty="Nenhuma TV de streaming conectada. No app, entre no setor e abra TV DE PROPAGANDAS (ou use /smart|/legacy na TV antiga)."
        tvs={streaming}
        onSelect={abrirTv}
      />

      <Card>
        <CardHeader>
          <CardTitle>Galeria ({itens.length})</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {itens.map((item) => (
            <div key={item.id} className="overflow-hidden rounded-xl border">
              {midiaTipo(item) === "video" ? (
                <video
                  src={`/uploads/${item.arquivo}`}
                  muted
                  playsInline
                  preload="metadata"
                  className="aspect-video w-full object-cover bg-muted"
                />
              ) : (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={`/uploads/${item.arquivo}`}
                  alt={`Mídia ${item.id}`}
                  className="aspect-video w-full object-cover bg-muted"
                />
              )}
              <div className="space-y-2 p-3">
                <p className="text-xs text-muted-foreground">
                  {midiaTipo(item) === "video" ? "Vídeo" : "Imagem"} · Ordem {item.ordem} ·{" "}
                  {item.ativo ? "Ativa" : "Inativa"}
                </p>
                <div className="flex flex-wrap gap-2">
                  <Button type="button" size="sm" variant="outline" onClick={() => move(item, -1)}>
                    Subir
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => move(item, 1)}>
                    Descer
                  </Button>
                  <Button type="button" size="sm" variant="outline" onClick={() => toggleAtivo(item)}>
                    {item.ativo ? "Desativar" : "Ativar"}
                  </Button>
                  <Button type="button" size="sm" variant="destructive" onClick={() => onDelete(item.id)}>
                    Remover
                  </Button>
                </div>
              </div>
            </div>
          ))}
          {!itens.length && (
            <div className="col-span-full flex flex-col items-center gap-2 py-10 text-muted-foreground">
              <ImageIcon className="h-8 w-8" />
              <p className="text-sm">Nenhuma mídia na biblioteca.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {tvAtiva ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="max-h-[90vh] w-full max-w-3xl overflow-y-auto">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MonitorPlay className="h-5 w-5" />
                Mídias de {tvAtiva.nome}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Marque o que deve aparecer nesta TV e salve. A ordem segue a da biblioteca.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                {itens.filter((item) => item.ativo).map((item) => {
                  const checked = midiasTv.has(item.id);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => toggleMidiaTv(item.id)}
                      className={`overflow-hidden rounded-xl border text-left ${
                        checked ? "border-primary ring-2 ring-primary/20" : ""
                      }`}
                    >
                      {midiaTipo(item) === "video" ? (
                        <video
                          src={`/uploads/${item.arquivo}`}
                          muted
                          className="aspect-video w-full object-cover bg-muted"
                        />
                      ) : (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={`/uploads/${item.arquivo}`}
                          alt=""
                          className="aspect-video w-full object-cover bg-muted"
                        />
                      )}
                      <div className="flex items-center gap-2 p-2 text-sm">
                        <span
                          className={`flex h-5 w-5 items-center justify-center rounded border ${
                            checked ? "border-primary bg-primary text-primary-foreground" : "border-input"
                          }`}
                        >
                          {checked && <Check className="h-3.5 w-3.5" />}
                        </span>
                        {midiaTipo(item) === "video" ? "Vídeo" : "Imagem"} {item.id}
                      </div>
                    </button>
                  );
                })}
              </div>
              {!itens.filter((item) => item.ativo).length && (
                <p className="text-sm text-muted-foreground">Cadastre mídias na biblioteca primeiro.</p>
              )}
              <div className="flex flex-wrap gap-2">
                <Button onClick={salvarTv} disabled={savingTv}>
                  {savingTv ? "Salvando..." : "Enviar para a TV"}
                </Button>
                <Button variant="outline" onClick={() => setTvAtiva(null)}>
                  Cancelar
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

function TvGroup({
  title,
  empty,
  tvs,
  onSelect,
}: {
  title: string;
  empty: string;
  tvs: TvAdmin[];
  onSelect: (tv: TvAdmin) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {tvs.map((tv) => (
          <button
            key={`${tv.tipo}-${tv.id}`}
            type="button"
            onClick={() => onSelect(tv)}
            className="rounded-xl border p-4 text-left transition hover:border-primary"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2">
                <Tv className="h-5 w-5 text-primary" />
                <span className="font-semibold">{tv.nome}</span>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 text-xs ${
                  tv.is_online ? "bg-emerald-100 text-emerald-800" : "bg-muted text-muted-foreground"
                }`}
              >
                {tv.is_online ? "Online" : "Offline"}
              </span>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {tv.tipo === "setor" ? "Painel de senhas" : tv.device_name || "Streaming"} ·{" "}
              {tv.propaganda_ids.length} mídia(s)
            </p>
          </button>
        ))}
        {!tvs.length && <p className="col-span-full text-sm text-muted-foreground">{empty}</p>}
      </CardContent>
    </Card>
  );
}
