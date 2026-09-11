"use client";

import { FormEvent, useEffect, useState } from "react";
import { ImageIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, type Propaganda } from "@/lib/api";

export default function PropagandasPage() {
  const [itens, setItens] = useState<Propaganda[]>([]);
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setItens(await apiFetch<Propaganda[]>("/api/v1/admin/propagandas"));
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
      await apiFetch("/api/v1/admin/propagandas", { method: "POST", body: form });
      setArquivo(null);
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
    if (!confirm("Remover esta propaganda?")) return;
    await apiFetch(`/api/v1/admin/propagandas/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Propagandas</h1>
        <p className="text-muted-foreground">
          Galeria global exibida na TV quando o setor tiver a função ativada. Rotação a cada 15s.
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

      <Card>
        <CardHeader>
          <CardTitle>Galeria ({itens.length})</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {itens.map((item) => (
            <div key={item.id} className="overflow-hidden rounded-xl border">
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
