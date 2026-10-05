"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, ImageIcon, MonitorPlay, Search, Smartphone, Trash2, Tv } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  apiFetch,
  setorEhStreaming,
  type CategoriaMidia,
  type Propaganda,
  type Setor,
  type TvAdmin,
} from "@/lib/api";
import { cn } from "@/lib/utils";

function midiaTipo(item: Propaganda): "image" | "video" {
  return item.tipo === "video" ? "video" : "image";
}

export default function PropagandasPage() {
  const [itens, setItens] = useState<Propaganda[]>([]);
  const [categorias, setCategorias] = useState<CategoriaMidia[]>([]);
  const [nomeCategoria, setNomeCategoria] = useState("");
  const [categoriaUpload, setCategoriaUpload] = useState("");
  const [salvandoCategoria, setSalvandoCategoria] = useState(false);
  const [tvs, setTvs] = useState<TvAdmin[]>([]);
  const [setoresCadastro, setSetoresCadastro] = useState<Setor[]>([]);
  const [arquivos, setArquivos] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [tvAtiva, setTvAtiva] = useState<TvAdmin | null>(null);
  const [midiasTv, setMidiasTv] = useState<Set<number>>(new Set());
  const [vigenciasTv, setVigenciasTv] = useState<Record<number, { inicio: string; fim: string }>>({});
  const [savingTv, setSavingTv] = useState(false);
  const [previewingTv, setPreviewingTv] = useState(false);
  const [previewMsg, setPreviewMsg] = useState<string | null>(null);
  const [clienteAtivo, setClienteAtivo] = useState<Setor | null>(null);
  const [midiasCliente, setMidiasCliente] = useState<Set<number>>(new Set());
  const [savingCliente, setSavingCliente] = useState(false);
  const [filtroBusca, setFiltroBusca] = useState("");
  const [filtroStatus, setFiltroStatus] = useState<"todos" | "online" | "offline">("todos");
  const [filtroTipo, setFiltroTipo] = useState<"todos" | "setor" | "streaming">("todos");
  const [filtroSetorId, setFiltroSetorId] = useState("");
  const [secoesAbertas, setSecoesAbertas] = useState<Record<string, boolean>>({
    senha: true,
    avulsas: true,
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function load() {
    const [midias, categoriasResponse, tvsResponse, setoresResponse] = await Promise.all([
      apiFetch<Propaganda[]>("/api/v1/admin/propagandas"),
      apiFetch<CategoriaMidia[]>("/api/v1/admin/propagandas/categorias"),
      apiFetch<TvAdmin[]>("/api/v1/admin/tvs"),
      apiFetch<Setor[]>("/api/v1/admin/setores"),
    ]);
    setItens(midias);
    setCategorias(categoriasResponse);
    setTvs(tvsResponse);
    setSetoresCadastro(setoresResponse);
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
      if (categoriaUpload) form.append("categoria_id", categoriaUpload);
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

  async function criarCategoria(e: FormEvent) {
    e.preventDefault();
    const nome = nomeCategoria.trim();
    if (!nome) return;
    setSalvandoCategoria(true);
    setError(null);
    try {
      await apiFetch("/api/v1/admin/propagandas/categorias", {
        method: "POST",
        body: JSON.stringify({ nome }),
      });
      setNomeCategoria("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar categoria");
    } finally {
      setSalvandoCategoria(false);
    }
  }

  async function renomearCategoria(categoria: CategoriaMidia, nome: string) {
    const limpo = nome.trim();
    if (!limpo || limpo === categoria.nome) return;
    await apiFetch(`/api/v1/admin/propagandas/categorias/${categoria.id}`, {
      method: "PUT",
      body: JSON.stringify({ nome: limpo }),
    });
    await load();
  }

  async function removerCategoria(categoria: CategoriaMidia) {
    if (!confirm(`Remover a categoria "${categoria.nome}"? As mídias continuam na biblioteca, sem categoria.`)) {
      return;
    }
    await apiFetch(`/api/v1/admin/propagandas/categorias/${categoria.id}`, { method: "DELETE" });
    if (categoriaUpload === String(categoria.id)) setCategoriaUpload("");
    await load();
  }

  async function definirCategoria(item: Propaganda, categoriaId: string) {
    await apiFetch(`/api/v1/admin/propagandas/${item.id}`, {
      method: "PUT",
      body: JSON.stringify({ categoria_id: categoriaId ? Number(categoriaId) : null }),
    });
    await load();
  }

  function abrirTv(tv: TvAdmin) {
    const rotacao =
      tv.rotacao_tv === 90 || tv.rotacao_tv === 180 || tv.rotacao_tv === 270
        ? tv.rotacao_tv
        : tv.orientacao_tv === "vertical"
          ? 90
          : 0;
    setTvAtiva({ ...tv, rotacao_tv: rotacao });
    setMidiasTv(new Set(tv.propaganda_ids));
    const vigencias: Record<number, { inicio: string; fim: string }> = {};
    for (const vinculo of tv.midias || []) {
      vigencias[vinculo.propaganda_id] = {
        inicio: vinculo.vigencia_inicio || "",
        fim: vinculo.vigencia_fim || "",
      };
    }
    setVigenciasTv(vigencias);
    setPreviewMsg(null);
  }

  function toggleMidiaTv(id: number) {
    setMidiasTv((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function rotacaoTvAtual(tv: TvAdmin): 0 | 90 | 180 | 270 {
    if (tv.rotacao_tv === 90 || tv.rotacao_tv === 180 || tv.rotacao_tv === 270) return tv.rotacao_tv;
    return tv.orientacao_tv === "vertical" ? 90 : 0;
  }

  async function salvarTv() {
    if (!tvAtiva) return;
    setSavingTv(true);
    setError(null);
    try {
      if (tvAtiva.tipo === "streaming") {
        await apiFetch(`/api/v1/admin/tvs/${tvAtiva.id}/setor`, {
          method: "PUT",
          body: JSON.stringify({ setor_id: tvAtiva.setor_id ?? null }),
        });
        await apiFetch(`/api/v1/admin/tvs/${tvAtiva.id}/rotacao`, {
          method: "PUT",
          body: JSON.stringify({ rotacao_tv: rotacaoTvAtual(tvAtiva) }),
        });
      }
      const selecionadas = itens.filter((item) => midiasTv.has(item.id));
      for (const item of selecionadas) {
        const vigencia = vigenciasTv[item.id];
        if (vigencia?.inicio && vigencia?.fim && vigencia.fim < vigencia.inicio) {
          throw new Error("A data final da vigência não pode ser anterior à inicial");
        }
      }
      await apiFetch("/api/v1/admin/tvs/midias", {
        method: "PUT",
        body: JSON.stringify({
          tipo: tvAtiva.tipo,
          id: tvAtiva.id,
          midias: selecionadas.map((item) => ({
            propaganda_id: item.id,
            vigencia_inicio: vigenciasTv[item.id]?.inicio || null,
            vigencia_fim: vigenciasTv[item.id]?.fim || null,
          })),
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

  async function previewNaTv(propagandaId?: number) {
    if (!tvAtiva || tvAtiva.tipo !== "streaming") return;
    setPreviewingTv(true);
    setPreviewMsg(null);
    setError(null);
    try {
      // Garante rotação salva antes do preview (APK aplica o ângulo do evento).
      await apiFetch(`/api/v1/admin/tvs/${tvAtiva.id}/rotacao`, {
        method: "PUT",
        body: JSON.stringify({ rotacao_tv: rotacaoTvAtual(tvAtiva) }),
      });
      const body: { propaganda_id?: number } = {};
      if (propagandaId != null) body.propaganda_id = propagandaId;
      await apiFetch(`/api/v1/admin/tvs/${tvAtiva.id}/preview`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      setPreviewMsg(
        propagandaId != null
          ? "Pré-visualização enviada para a TV (mídia selecionada)."
          : "Pré-visualização enviada para a TV (primeira da fila).",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao pré-visualizar na TV");
    } finally {
      setPreviewingTv(false);
    }
  }

  async function removerTv(tv: TvAdmin) {
    if (tv.tipo !== "streaming") return;
    if (!confirm(`Remover o cadastro da TV "${tv.nome}"?`)) return;
    try {
      await apiFetch(`/api/v1/admin/tvs/${tv.id}`, { method: "DELETE" });
      if (tvAtiva?.id === tv.id) setTvAtiva(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao remover TV");
    }
  }

  function toggleSecao(key: string) {
    setSecoesAbertas((current) => ({ ...current, [key]: !current[key] }));
  }

  function abrirCliente(setor: Setor) {
    setClienteAtivo(setor);
    setMidiasCliente(new Set(setor.propaganda_ids_cliente || []));
  }

  function toggleMidiaCliente(id: number) {
    setMidiasCliente((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function salvarCliente() {
    if (!clienteAtivo) return;
    setSavingCliente(true);
    setError(null);
    try {
      await apiFetch("/api/v1/admin/propagandas/cliente", {
        method: "PUT",
        body: JSON.stringify({
          setor_id: clienteAtivo.id,
          propaganda_ids: itens.filter((item) => midiasCliente.has(item.id)).map((item) => item.id),
        }),
      });
      setClienteAtivo(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao enviar mídias para a espera");
    } finally {
      setSavingCliente(false);
    }
  }

  const tvsFiltradas = useMemo(() => {
    const q = filtroBusca.trim().toLowerCase();
    return tvs.filter((tv) => {
      if (filtroTipo !== "todos" && tv.tipo !== filtroTipo) return false;
      if (filtroStatus === "online" && !tv.is_online) return false;
      if (filtroStatus === "offline" && tv.is_online) return false;
      if (filtroSetorId) {
        const sid = Number(filtroSetorId);
        if (tv.tipo === "setor" && tv.id !== sid) return false;
        if (tv.tipo === "streaming" && tv.setor_id !== sid) return false;
      }
      if (!q) return true;
      const hay = [tv.nome, tv.device_name, tv.setor_nome, tv.chave]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [tvs, filtroBusca, filtroStatus, filtroTipo, filtroSetorId]);

  const tvsSenha = useMemo(() => tvsFiltradas.filter((tv) => tv.tipo === "setor"), [tvsFiltradas]);
  const streaming = useMemo(() => tvsFiltradas.filter((tv) => tv.tipo === "streaming"), [tvsFiltradas]);
  const setoresEspera = useMemo(
    () => setoresCadastro.filter((setor) => !setorEhStreaming(setor)),
    [setoresCadastro],
  );
  const setoresStreaming = useMemo(
    () => setoresCadastro.filter(setorEhStreaming),
    [setoresCadastro],
  );
  const gruposStreaming = useMemo(() => {
    const grupos: { key: string; title: string; tvs: TvAdmin[] }[] = setoresStreaming.map((setor) => ({
      key: `setor-${setor.id}`,
      title: `TVs de streaming — ${setor.nome}`,
      tvs: streaming.filter((tv) => tv.setor_id === setor.id),
    }));
    const avulsas = streaming.filter(
      (tv) => !tv.setor_id || !setoresStreaming.some((setor) => setor.id === tv.setor_id),
    );
    grupos.push({
      key: "avulsas",
      title: "TVs de streaming avulsas",
      tvs: avulsas,
    });
    return grupos;
  }, [streaming, setoresStreaming]);

  useEffect(() => {
    setSecoesAbertas((current) => {
      const next = { ...current };
      for (const grupo of gruposStreaming) {
        if (next[grupo.key] === undefined) next[grupo.key] = true;
      }
      return next;
    });
  }, [gruposStreaming]);

  const gruposBiblioteca = useMemo(() => {
    const semCategoria = itens.filter(
      (item) => !item.categoria_id || !categorias.some((categoria) => categoria.id === item.categoria_id),
    );
    const grupos = categorias.map((categoria) => ({
      id: categoria.id,
      nome: categoria.nome,
      itens: itens.filter((item) => item.categoria_id === categoria.id),
    }));
    if (semCategoria.length) {
      grupos.push({ id: 0, nome: "Sem categoria", itens: semCategoria });
    }
    return grupos;
  }, [categorias, itens]);

  const midiasAtivasPorCategoria = useMemo(() => {
    const ativas = itens.filter((item) => item.ativo);
    const semCategoria = ativas.filter(
      (item) => !item.categoria_id || !categorias.some((categoria) => categoria.id === item.categoria_id),
    );
    const grupos = categorias
      .map((categoria) => ({
        id: categoria.id,
        nome: categoria.nome,
        itens: ativas.filter((item) => item.categoria_id === categoria.id),
      }))
      .filter((grupo) => grupo.itens.length);
    if (semCategoria.length) {
      grupos.push({ id: 0, nome: "Sem categoria", itens: semCategoria });
    }
    return grupos;
  }, [categorias, itens]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Mídias e TVs</h1>
        <p className="text-muted-foreground">
          Suba a biblioteca e clique na TV ou na tela de espera do cliente para escolher o que
          aparece. TVs de propagandas do app aparecem ao abrir <strong>TV DE PROPAGANDAS</strong> no
          setor (<code>/smart</code> e <code>/legacy</code> continuam válidos).
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Biblioteca</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <form className="flex flex-wrap items-end gap-2" onSubmit={criarCategoria}>
            <div className="min-w-[220px] flex-1 space-y-2">
              <Label htmlFor="nova-categoria">Nova categoria</Label>
              <Input
                id="nova-categoria"
                value={nomeCategoria}
                placeholder="Ex.: Açougue, Padaria, Ofertas"
                onChange={(e) => setNomeCategoria(e.target.value)}
              />
            </div>
            <Button type="submit" variant="secondary" disabled={salvandoCategoria || !nomeCategoria.trim()}>
              {salvandoCategoria ? "Salvando..." : "Criar categoria"}
            </Button>
          </form>
          {categorias.length ? (
            <ul className="flex flex-wrap gap-2">
              {categorias.map((categoria) => (
                <li key={categoria.id} className="flex items-center gap-1 rounded-lg border bg-card px-2 py-1">
                  <input
                    aria-label={`Nome da categoria ${categoria.nome}`}
                    className="w-36 bg-transparent text-sm outline-none"
                    defaultValue={categoria.nome}
                    key={`${categoria.id}-${categoria.nome}`}
                    onBlur={(e) => {
                      renomearCategoria(categoria, e.target.value).catch((err) =>
                        setError(err instanceof Error ? err.message : "Erro ao renomear categoria"),
                      );
                    }}
                  />
                  <button
                    type="button"
                    className="rounded p-1 text-muted-foreground hover:text-destructive"
                    aria-label={`Remover categoria ${categoria.nome}`}
                    onClick={() =>
                      removerCategoria(categoria).catch((err) =>
                        setError(err instanceof Error ? err.message : "Erro ao remover categoria"),
                      )
                    }
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              Crie uma categoria e envie as mídias para dentro dela.
            </p>
          )}
          <form className="grid gap-4" onSubmit={onUpload}>
            <div className="space-y-2">
              <Label htmlFor="categoria-upload">Categoria</Label>
              <select
                id="categoria-upload"
                className="flex h-10 w-full max-w-sm rounded-lg border border-input bg-card px-3 text-sm"
                value={categoriaUpload}
                onChange={(e) => setCategoriaUpload(e.target.value)}
              >
                <option value="">Sem categoria</option>
                {categorias.map((categoria) => (
                  <option key={categoria.id} value={categoria.id}>
                    {categoria.nome}
                  </option>
                ))}
              </select>
            </div>
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

      <Card>
        <CardHeader>
          <CardTitle>TVs cadastradas</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="relative sm:col-span-2 lg:col-span-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Buscar por nome, dispositivo…"
                value={filtroBusca}
                onChange={(e) => setFiltroBusca(e.target.value)}
              />
            </div>
            <select
              className="flex h-10 w-full rounded-lg border border-input bg-card px-3 text-sm"
              value={filtroTipo}
              onChange={(e) => setFiltroTipo(e.target.value as typeof filtroTipo)}
            >
              <option value="todos">Todos os tipos</option>
              <option value="setor">Senha</option>
              <option value="streaming">Streaming</option>
            </select>
            <select
              className="flex h-10 w-full rounded-lg border border-input bg-card px-3 text-sm"
              value={filtroStatus}
              onChange={(e) => setFiltroStatus(e.target.value as typeof filtroStatus)}
            >
              <option value="todos">Online e offline</option>
              <option value="online">Só online</option>
              <option value="offline">Só offline</option>
            </select>
            <select
              className="flex h-10 w-full rounded-lg border border-input bg-card px-3 text-sm"
              value={filtroSetorId}
              onChange={(e) => setFiltroSetorId(e.target.value)}
            >
              <option value="">Todos os setores</option>
              {setoresCadastro.map((setor) => (
                <option key={setor.id} value={setor.id}>
                  {setor.nome}
                  {setorEhStreaming(setor) ? " · streaming" : ""}
                </option>
              ))}
            </select>
          </div>
          <p className="text-xs text-muted-foreground">
            {tvsFiltradas.length} TV(s) · orientação de streaming é por dispositivo
          </p>
        </CardContent>
      </Card>

      {(filtroTipo === "todos" || filtroTipo === "setor") && (
        <TvGroup
          sectionKey="senha"
          open={secoesAbertas.senha !== false}
          onToggle={() => toggleSecao("senha")}
          title="TVs de senha (setores de atendimento)"
          empty="Cadastre um setor de atendimento. Ao abrir o painel da TV, ela fica online e você escolhe as mídias aqui."
          tvs={tvsSenha}
          onSelect={abrirTv}
        />
      )}

      {(filtroTipo === "todos" || filtroTipo === "streaming") &&
        gruposStreaming.map((grupo) => (
          <TvGroup
            key={grupo.key}
            sectionKey={grupo.key}
            open={secoesAbertas[grupo.key] !== false}
            onToggle={() => toggleSecao(grupo.key)}
            title={grupo.title}
            empty={
              grupo.key === "avulsas"
                ? "Nenhuma TV avulsa. No app, abra TV DE PROPAGANDAS ou use /smart|/legacy. Depois associe a um setor de streaming se quiser."
                : "Nenhuma TV vinculada a este setor. Conecte uma TV de streaming e associe-a aqui."
            }
            tvs={grupo.tvs}
            onSelect={abrirTv}
            onRemove={removerTv}
          />
        ))}

      <Card>
        <CardHeader>
          <CardTitle>Telas de espera (clientes)</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {setoresEspera.map((setor) => (
            <button
              key={setor.id}
              type="button"
              onClick={() => abrirCliente(setor)}
              className="rounded-xl border p-4 text-left transition hover:border-primary"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Smartphone className="h-5 w-5 text-primary" />
                  <span className="font-semibold">{setor.nome}</span>
                </div>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs ${
                    setor.propagandas_cliente_ativas
                      ? "bg-emerald-100 text-emerald-800"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {setor.propagandas_cliente_ativas ? "Ligada" : "Desligada"}
                </span>
              </div>
              <p className="mt-2 text-xs text-muted-foreground">
                Acompanhar / totem · {(setor.propaganda_ids_cliente || []).length} mídia(s)
              </p>
            </button>
          ))}
          {!setoresEspera.length && (
            <p className="col-span-full text-sm text-muted-foreground">
              Cadastre um setor de atendimento para enviar mídias à espera do cliente.
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Galeria ({itens.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {gruposBiblioteca.map((grupo) => (
            <div key={grupo.id} className="space-y-3">
              <h3 className="text-sm font-semibold">
                {grupo.nome}
                <span className="ml-2 font-normal text-muted-foreground">{grupo.itens.length}</span>
              </h3>
              {!grupo.itens.length ? (
                <p className="text-sm text-muted-foreground">Nenhuma mídia nesta categoria.</p>
              ) : (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {grupo.itens.map((item) => (
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
                <select
                  aria-label={`Categoria da mídia ${item.id}`}
                  className="flex h-9 w-full rounded-lg border border-input bg-card px-2 text-sm"
                  value={item.categoria_id ? String(item.categoria_id) : ""}
                  onChange={(e) =>
                    definirCategoria(item, e.target.value).catch((err) =>
                      setError(err instanceof Error ? err.message : "Erro ao mover mídia"),
                    )
                  }
                >
                  <option value="">Sem categoria</option>
                  {categorias.map((categoria) => (
                    <option key={categoria.id} value={categoria.id}>
                      {categoria.nome}
                    </option>
                  ))}
                </select>
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
                </div>
              )}
            </div>
          ))}
          {!itens.length && !categorias.length && (
            <div className="flex flex-col items-center gap-2 py-10 text-muted-foreground">
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
                Marque o que deve aparecer nesta TV e salve. A ordem segue a da biblioteca. Início e
                fim são opcionais: fora desse período a mídia não entra na TV.
              </p>
              {tvAtiva.tipo === "streaming" ? (
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="tv-setor">Setor</Label>
                    <select
                      id="tv-setor"
                      className="flex h-10 w-full rounded-lg border border-input bg-card px-3 text-sm"
                      value={tvAtiva.setor_id ? String(tvAtiva.setor_id) : ""}
                      onChange={(e) =>
                        setTvAtiva({
                          ...tvAtiva,
                          setor_id: e.target.value ? Number(e.target.value) : null,
                        })
                      }
                    >
                      <option value="">Avulsa (sem setor)</option>
                      {setoresCadastro.map((setor) => (
                        <option key={setor.id} value={setor.id}>
                          {setor.nome}
                          {setorEhStreaming(setor) ? " · streaming" : ""}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="tv-rotacao">Rotação desta TV</Label>
                    <select
                      id="tv-rotacao"
                      className="flex h-10 w-full rounded-lg border border-input bg-card px-3 text-sm"
                      value={String(rotacaoTvAtual(tvAtiva))}
                      onChange={(e) => {
                        const value = Number(e.target.value) as 0 | 90 | 180 | 270;
                        setTvAtiva({
                          ...tvAtiva,
                          rotacao_tv: value,
                          orientacao_tv: value === 90 || value === 270 ? "vertical" : "horizontal",
                        });
                      }}
                    >
                      <option value="0">0° (paisagem)</option>
                      <option value="90">90° (retrato CW)</option>
                      <option value="180">180°</option>
                      <option value="270">270° (retrato CCW)</option>
                    </select>
                    <p className="text-xs text-muted-foreground">
                      Independente do setor. O APK aplica o ângulo com ForcedDisplayOrientation.
                    </p>
                  </div>
                </div>
              ) : null}
              {tvAtiva.tipo === "streaming" && midiasTv.size > 0 ? (
                <div className="rounded-xl border bg-muted/30 p-3">
                  <p className="mb-2 text-xs font-medium text-muted-foreground">
                    Pré-visualização local (mesma rotação da TV)
                  </p>
                  <div className="flex justify-center">
                    {(() => {
                      const firstId = itens.find((item) => item.ativo && midiasTv.has(item.id))?.id;
                      const first = itens.find((item) => item.id === firstId);
                      if (!first) return <p className="text-sm text-muted-foreground">Sem mídia marcada</p>;
                      const rot = rotacaoTvAtual(tvAtiva);
                      const swapped = rot === 90 || rot === 270;
                      // 90/270: palco 9:16 (o que o cliente vê com a TV em pé) e a mídia cobre
                      // até a borda. 0/180: palco 16:9; 180° só inverte, sem faixas extras.
                      const mediaClass = `h-full w-full ${swapped || rot === 180 ? "object-cover" : "object-contain"}`;
                      const mediaStyle = rot === 180 ? { transform: "rotate(180deg)" } : undefined;
                      return (
                        <div
                          className="relative overflow-hidden rounded-lg bg-black"
                          style={
                            swapped
                              ? { height: "min(68vh, 520px)", aspectRatio: "9 / 16" }
                              : { width: "100%", aspectRatio: "16 / 9" }
                          }
                        >
                          {midiaTipo(first) === "video" ? (
                            <video
                              src={`/uploads/${first.arquivo}`}
                              muted
                              playsInline
                              className={`absolute inset-0 ${mediaClass}`}
                              style={mediaStyle}
                            />
                          ) : (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img
                              src={`/uploads/${first.arquivo}`}
                              alt=""
                              className={`absolute inset-0 ${mediaClass}`}
                              style={mediaStyle}
                            />
                          )}
                        </div>
                      );
                    })()}
                  </div>
                </div>
              ) : null}
              <div className="space-y-4">
                {midiasAtivasPorCategoria.map((grupo) => (
                  <div key={grupo.id} className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                      {grupo.nome}
                    </p>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {grupo.itens.map((item) => {
                        const checked = midiasTv.has(item.id);
                        const vigencia = vigenciasTv[item.id] || { inicio: "", fim: "" };
                        return (
                          <div
                            key={item.id}
                            className={`overflow-hidden rounded-xl border ${
                              checked ? "border-primary ring-2 ring-primary/20" : ""
                            }`}
                          >
                            <button
                              type="button"
                              onClick={() => toggleMidiaTv(item.id)}
                              className="w-full text-left"
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
                            {checked ? (
                              <div className="grid grid-cols-2 gap-2 border-t px-2 py-2">
                                <label className="space-y-1 text-xs text-muted-foreground">
                                  Início
                                  <Input
                                    type="date"
                                    value={vigencia.inicio}
                                    onChange={(e) =>
                                      setVigenciasTv((current) => ({
                                        ...current,
                                        [item.id]: { ...vigencia, inicio: e.target.value },
                                      }))
                                    }
                                  />
                                </label>
                                <label className="space-y-1 text-xs text-muted-foreground">
                                  Fim
                                  <Input
                                    type="date"
                                    value={vigencia.fim}
                                    onChange={(e) =>
                                      setVigenciasTv((current) => ({
                                        ...current,
                                        [item.id]: { ...vigencia, fim: e.target.value },
                                      }))
                                    }
                                  />
                                </label>
                              </div>
                            ) : null}
                            {tvAtiva.tipo === "streaming" ? (
                              <div className="border-t px-2 pb-2">
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-full text-xs"
                                  disabled={previewingTv}
                                  onClick={() => previewNaTv(item.id)}
                                >
                                  Pré-visualizar na TV
                                </Button>
                              </div>
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
              {!itens.filter((item) => item.ativo).length && (
                <p className="text-sm text-muted-foreground">Cadastre mídias na biblioteca primeiro.</p>
              )}
              {previewMsg ? <p className="text-sm text-emerald-700">{previewMsg}</p> : null}
              <div className="flex flex-wrap gap-2">
                <Button onClick={salvarTv} disabled={savingTv}>
                  {savingTv ? "Salvando..." : "Enviar para a TV"}
                </Button>
                {tvAtiva.tipo === "streaming" ? (
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={previewingTv}
                    onClick={() => previewNaTv()}
                  >
                    {previewingTv ? "Enviando…" : "Pré-visualizar fila na TV"}
                  </Button>
                ) : null}
                <Button variant="outline" onClick={() => setTvAtiva(null)}>
                  Cancelar
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {clienteAtivo ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <Card className="max-h-[90vh] w-full max-w-3xl overflow-y-auto">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Smartphone className="h-5 w-5" />
                Espera do cliente — {clienteAtivo.nome}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Marque o que aparece na tela de aguardando do cliente neste setor.
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                {itens.filter((item) => item.ativo).map((item) => {
                  const checked = midiasCliente.has(item.id);
                  return (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => toggleMidiaCliente(item.id)}
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
                <Button onClick={salvarCliente} disabled={savingCliente}>
                  {savingCliente ? "Salvando..." : "Enviar para a espera"}
                </Button>
                <Button variant="outline" onClick={() => setClienteAtivo(null)}>
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
  sectionKey,
  open,
  onToggle,
  title,
  empty,
  tvs,
  onSelect,
  onRemove,
}: {
  sectionKey: string;
  open: boolean;
  onToggle: () => void;
  title: string;
  empty: string;
  tvs: TvAdmin[];
  onSelect: (tv: TvAdmin) => void;
  onRemove?: (tv: TvAdmin) => void;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <button
          type="button"
          onClick={onToggle}
          className="flex w-full items-center justify-between gap-3 text-left"
          aria-expanded={open}
          aria-controls={`tv-group-${sectionKey}`}
        >
          <CardTitle className="flex items-center gap-2">
            {title}
            <span className="rounded-full bg-muted px-2 py-0.5 text-xs font-normal text-muted-foreground">
              {tvs.length}
            </span>
          </CardTitle>
          <ChevronDown
            className={cn("h-5 w-5 shrink-0 text-muted-foreground transition-transform", open && "rotate-180")}
          />
        </button>
      </CardHeader>
      {open ? (
        <CardContent id={`tv-group-${sectionKey}`} className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {tvs.map((tv) => (
            <div
              key={`${tv.tipo}-${tv.id}`}
              className="rounded-xl border p-4 transition hover:border-primary"
            >
              <button type="button" onClick={() => onSelect(tv)} className="w-full text-left">
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
                  {tv.tipo === "setor"
                    ? "Painel de senhas"
                    : tv.setor_nome
                      ? `${tv.device_name || "Streaming"} · ${tv.setor_nome}`
                      : tv.device_name || "Streaming avulsa"}{" "}
                  · {tv.propaganda_ids.length} mídia(s)
                  {tv.tipo === "streaming"
                    ? ` · ${
                        tv.rotacao_tv === 90 || tv.rotacao_tv === 180 || tv.rotacao_tv === 270
                          ? `${tv.rotacao_tv}°`
                          : tv.orientacao_tv === "vertical"
                            ? "90°"
                            : "0°"
                      }`
                    : ""}
                </p>
              </button>
              {tv.tipo === "streaming" && onRemove ? (
                <div className="mt-3 flex justify-end">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 gap-1 text-destructive hover:text-destructive"
                    onClick={() => onRemove(tv)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Remover
                  </Button>
                </div>
              ) : null}
            </div>
          ))}
          {!tvs.length && <p className="col-span-full text-sm text-muted-foreground">{empty}</p>}
        </CardContent>
      ) : null}
    </Card>
  );
}
