"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, type CategoriaMidia } from "@/lib/api";

export default function CategoriasMidiasPage() {
  const [itens, setItens] = useState<CategoriaMidia[]>([]);
  const [nome, setNome] = useState("");
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [nomeEdit, setNomeEdit] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    const lista = await apiFetch<CategoriaMidia[]>("/api/v1/admin/propagandas/categorias");
    setItens(lista);
  }

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    const limpo = nome.trim();
    if (!limpo) return;
    setLoading(true);
    setError(null);
    setMessage(null);
    try {
      await apiFetch("/api/v1/admin/propagandas/categorias", {
        method: "POST",
        body: JSON.stringify({ nome: limpo }),
      });
      setNome("");
      setMessage("Categoria criada.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar");
    } finally {
      setLoading(false);
    }
  }

  function comecarEdicao(item: CategoriaMidia) {
    setEditandoId(item.id);
    setNomeEdit(item.nome);
    setError(null);
    setMessage(null);
  }

  async function salvarEdicao(item: CategoriaMidia) {
    const limpo = nomeEdit.trim();
    if (!limpo) {
      setError("Informe o nome da categoria");
      return;
    }
    setError(null);
    try {
      await apiFetch(`/api/v1/admin/propagandas/categorias/${item.id}`, {
        method: "PUT",
        body: JSON.stringify({ nome: limpo }),
      });
      setEditandoId(null);
      setMessage("Categoria atualizada.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    }
  }

  async function mover(item: CategoriaMidia, delta: number) {
    const indice = itens.findIndex((atual) => atual.id === item.id);
    const vizinha = itens[indice + delta];
    if (!vizinha) return;
    setError(null);
    await Promise.all([
      apiFetch(`/api/v1/admin/propagandas/categorias/${item.id}`, {
        method: "PUT",
        body: JSON.stringify({ ordem: vizinha.ordem }),
      }),
      apiFetch(`/api/v1/admin/propagandas/categorias/${vizinha.id}`, {
        method: "PUT",
        body: JSON.stringify({ ordem: item.ordem }),
      }),
    ]);
    await load();
  }

  async function onDelete(item: CategoriaMidia) {
    const qtd = item.midias ?? 0;
    const extra =
      qtd > 0
        ? ` ${qtd} mídia(s) desta categoria ficam na biblioteca, sem categoria.`
        : "";
    if (!confirm(`Excluir a categoria "${item.nome}"?${extra}`)) return;
    setError(null);
    try {
      await apiFetch(`/api/v1/admin/propagandas/categorias/${item.id}`, { method: "DELETE" });
      if (editandoId === item.id) setEditandoId(null);
      setMessage("Categoria excluída.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao excluir");
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Categorias de mídias</h1>
        <p className="text-muted-foreground">
          Crie, edite, reordene e exclua categorias usadas na{" "}
          <Link href="/admin/propagandas" className="text-primary underline-offset-4 hover:underline">
            biblioteca de mídias
          </Link>
          .
        </p>
      </div>

      {message && <p className="text-sm text-emerald-600">{message}</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader>
          <CardTitle>Nova categoria</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3 md:flex-row md:items-end" onSubmit={onCreate}>
            <div className="flex-1 space-y-2">
              <Label htmlFor="nome-categoria">Nome</Label>
              <Input
                id="nome-categoria"
                value={nome}
                onChange={(e) => setNome(e.target.value)}
                placeholder="Ex.: Açougue, Padaria, Ofertas"
                required
              />
            </div>
            <Button type="submit" disabled={loading || !nome.trim()}>
              {loading ? "Salvando..." : "Adicionar"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Lista ({itens.length})</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {itens.map((item, indice) => {
            const editando = editandoId === item.id;
            return (
              <div
                key={item.id}
                className="flex flex-col gap-3 rounded-xl border p-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="min-w-0 flex-1 space-y-1">
                  {editando ? (
                    <Input
                      value={nomeEdit}
                      onChange={(e) => setNomeEdit(e.target.value)}
                      aria-label={`Novo nome de ${item.nome}`}
                    />
                  ) : (
                    <p className="font-medium">{item.nome}</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    {item.midias ?? 0} mídia(s) · ordem {item.ordem}
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  {editando ? (
                    <>
                      <Button type="button" size="sm" onClick={() => salvarEdicao(item)}>
                        Salvar
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => setEditandoId(null)}>
                        Cancelar
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={indice === 0}
                        onClick={() => mover(item, -1)}
                      >
                        Subir
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        disabled={indice === itens.length - 1}
                        onClick={() => mover(item, 1)}
                      >
                        Descer
                      </Button>
                      <Button type="button" size="sm" variant="outline" onClick={() => comecarEdicao(item)}>
                        Editar
                      </Button>
                      <Button type="button" size="sm" variant="destructive" onClick={() => onDelete(item)}>
                        Excluir
                      </Button>
                    </>
                  )}
                </div>
              </div>
            );
          })}
          {!itens.length && (
            <p className="text-sm text-muted-foreground">Nenhuma categoria cadastrada.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
