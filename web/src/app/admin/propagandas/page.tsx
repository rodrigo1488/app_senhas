"use client";

import { FormEvent, useEffect, useState } from "react";
import { Check, ImageIcon, Layers3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, type Propaganda, type Setor } from "@/lib/api";

export default function PropagandasPage() {
  const [itens, setItens] = useState<Propaganda[]>([]);
  const [setores, setSetores] = useState<Setor[]>([]);
  const [selecionadas, setSelecionadas] = useState<Set<number>>(new Set());
  const [setoresSelecionados, setSetoresSelecionados] = useState<Set<number>>(new Set());
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [savingAssignments, setSavingAssignments] = useState(false);

  async function load() {
    const [midias, setoresResponse] = await Promise.all([
      apiFetch<Propaganda[]>("/api/v1/admin/propagandas"),
      apiFetch<Setor[]>("/api/v1/admin/setores"),
    ]);
    setItens(midias);
    setSetores(setoresResponse);
  }

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);

  async function onUpload(e: FormEvent) {
    e.preventDefault();
    if (!arquivo) {
      setError("Selecione uma imagem");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.set("arquivo", arquivo);
      const criada = await apiFetch<Propaganda>("/api/v1/admin/propagandas", {
        method: "POST",
        body: form,
      });
      setArquivo(null);
      await load();
      setSelecionadas(new Set([criada.id]));
      setSetoresSelecionados(new Set());
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
    if (!confirm("Remover esta propaganda?")) return;
    await apiFetch(`/api/v1/admin/propagandas/${id}`, { method: "DELETE" });
    await load();
    setSelecionadas((current) => {
      const next = new Set(current);
      next.delete(id);
      return next;
    });
  }

  function toggleMidia(item: Propaganda) {
    setSelecionadas((current) => {
      const next = new Set(current);
      if (next.has(item.id)) {
        next.delete(item.id);
        if (!next.size) setSetoresSelecionados(new Set());
      } else {
        if (!next.size) setSetoresSelecionados(new Set(item.setor_ids));
        next.add(item.id);
      }
      return next;
    });
  }

  function toggleSetor(id: number) {
    setSetoresSelecionados((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function saveAssignments() {
    if (!selecionadas.size) return;
    setSavingAssignments(true);
    setError(null);
    try {
      await apiFetch("/api/v1/admin/propagandas/setores", {
        method: "PUT",
        body: JSON.stringify({
          propaganda_ids: Array.from(selecionadas),
          setor_ids: Array.from(setoresSelecionados),
        }),
      });
      await load();
      setSelecionadas(new Set());
      setSetoresSelecionados(new Set());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao vincular setores");
    } finally {
      setSavingAssignments(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Propagandas</h1>
        <p className="text-muted-foreground">
          Selecione uma ou várias mídias e defina em quais setores elas serão exibidas.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Nova imagem</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={onUpload}>
            <div className="space-y-2 md:col-span-2">
              <Label>Imagem (PNG, JPG, WEBP — até 5MB)</Label>
              <Input
                type="file"
                accept="image/*"
                onChange={(e) => setArquivo(e.target.files?.[0] || null)}
              />
            </div>
            {error && <p className="text-sm text-destructive md:col-span-2">{error}</p>}
            <Button type="submit" disabled={loading || !arquivo} className="md:w-fit">
              {loading ? "Enviando..." : "Adicionar"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {selecionadas.size > 0 && (
        <Card className="border-primary/35">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Layers3 className="h-5 w-5 text-primary" />
              Vincular {selecionadas.size} {selecionadas.size === 1 ? "mídia" : "mídias"}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              A seleção abaixo substituirá os setores vinculados a todas as mídias marcadas.
            </p>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {setores.map((setor) => {
                const checked = setoresSelecionados.has(setor.id);
                return (
                  <button
                    key={setor.id}
                    type="button"
                    onClick={() => toggleSetor(setor.id)}
                    className={`flex items-center gap-3 rounded-xl border p-3 text-left transition ${
                      checked ? "border-primary bg-primary/5" : "hover:border-primary/40"
                    }`}
                  >
                    <span
                      className={`flex h-5 w-5 items-center justify-center rounded border ${
                        checked ? "border-primary bg-primary text-primary-foreground" : "border-input"
                      }`}
                    >
                      {checked && <Check className="h-3.5 w-3.5" />}
                    </span>
                    <span className="font-medium">{setor.nome}</span>
                  </button>
                );
              })}
            </div>
            {!setores.length && <p className="text-sm text-muted-foreground">Cadastre um setor primeiro.</p>}
            <div className="flex flex-wrap gap-2">
              <Button onClick={saveAssignments} disabled={savingAssignments}>
                {savingAssignments ? "Salvando..." : "Aplicar aos setores"}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setSelecionadas(new Set());
                  setSetoresSelecionados(new Set());
                }}
              >
                Cancelar seleção
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>Galeria ({itens.length})</CardTitle>
            {!!itens.length && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  setSelecionadas(
                    selecionadas.size === itens.length ? new Set() : new Set(itens.map((item) => item.id)),
                  );
                  setSetoresSelecionados(new Set());
                }}
              >
                {selecionadas.size === itens.length ? "Limpar seleção" : "Selecionar todas"}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {itens.map((item) => (
            <div
              key={item.id}
              className={`relative overflow-hidden rounded-xl border transition ${
                selecionadas.has(item.id) ? "border-primary ring-2 ring-primary/25" : ""
              }`}
            >
              <button
                type="button"
                aria-label={`${selecionadas.has(item.id) ? "Desmarcar" : "Selecionar"} propaganda ${item.id}`}
                onClick={() => toggleMidia(item)}
                className={`absolute left-3 top-3 z-10 flex h-8 w-8 items-center justify-center rounded-lg border shadow-sm ${
                  selecionadas.has(item.id)
                    ? "border-primary bg-primary text-primary-foreground"
                    : "border-white/70 bg-black/45 text-white"
                }`}
              >
                {selecionadas.has(item.id) && <Check className="h-5 w-5" />}
              </button>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`/uploads/${item.arquivo}`}
                alt={`Propaganda ${item.id}`}
                className="aspect-video w-full object-cover bg-muted"
              />
              <div className="space-y-2 p-3">
                <p className="text-xs text-muted-foreground">
                  Ordem {item.ordem} · {item.ativo ? "Ativa" : "Inativa"}
                </p>
                <p className="text-xs text-muted-foreground">
                  {item.setor_ids.length
                    ? `${item.setor_ids.length} ${item.setor_ids.length === 1 ? "setor vinculado" : "setores vinculados"}`
                    : "Sem setor vinculado"}
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
              <p className="text-sm">Nenhuma propaganda cadastrada.</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
