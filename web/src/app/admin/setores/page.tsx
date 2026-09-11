"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, type Setor } from "@/lib/api";

export default function SetoresPage() {
  const [setores, setSetores] = useState<Setor[]>([]);
  const [editing, setEditing] = useState<Setor | null>(null);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [senhaSetor, setSenhaSetor] = useState("");
  const [modoIdentificacao, setModoIdentificacao] = useState<"foto" | "pin">("foto");
  const [propagandasAtivas, setPropagandasAtivas] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    setSetores(await apiFetch<Setor[]>("/api/v1/admin/setores"));
  }

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);

  function startEdit(setor: Setor) {
    setEditing(setor);
    setNome(setor.nome);
    setDescricao(setor.descricao || "");
    setSenhaSetor(setor.senha_setor || "");
    setModoIdentificacao(setor.modo_identificacao_operador || "foto");
    setPropagandasAtivas(Boolean(setor.propagandas_ativas));
  }

  function resetForm() {
    setEditing(null);
    setNome("");
    setDescricao("");
    setSenhaSetor("");
    setModoIdentificacao("foto");
    setPropagandasAtivas(false);
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const body = JSON.stringify({
        nome,
        descricao,
        senha_setor: senhaSetor,
        modo_identificacao_operador: modoIdentificacao,
        propagandas_ativas: propagandasAtivas,
      });
      if (editing) {
        await apiFetch(`/api/v1/admin/setores/${editing.id}`, { method: "PUT", body });
      } else {
        await apiFetch("/api/v1/admin/setores", { method: "POST", body });
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setLoading(false);
    }
  }

  async function onDelete(id: number) {
    if (!confirm("Excluir este setor?")) return;
    await apiFetch(`/api/v1/admin/setores/${id}`, { method: "DELETE" });
    await load();
  }

  async function togglePropagandas(setor: Setor) {
    await apiFetch(`/api/v1/admin/setores/${setor.id}`, {
      method: "PUT",
      body: JSON.stringify({ propagandas_ativas: !setor.propagandas_ativas }),
    });
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Setores</h1>
        <p className="text-muted-foreground">Áreas de atendimento e códigos de acesso do app</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>{editing ? `Editar: ${editing.nome}` : "Novo setor"}</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label>Nome</Label>
              <Input value={nome} onChange={(e) => setNome(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label>Código / senha do setor</Label>
              <Input value={senhaSetor} onChange={(e) => setSenhaSetor(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>Identificação dos operadores</Label>
              <select
                className="flex h-10 w-full rounded-lg border border-input bg-card px-3 text-sm"
                value={modoIdentificacao}
                onChange={(e) => setModoIdentificacao(e.target.value as "foto" | "pin")}
              >
                <option value="foto">Clique na foto</option>
                <option value="pin">PIN numérico</option>
              </select>
            </div>
            <div className="flex items-center gap-3 space-y-0 pt-8">
              <input
                id="propagandas_ativas"
                type="checkbox"
                className="h-4 w-4 rounded border"
                checked={propagandasAtivas}
                onChange={(e) => setPropagandasAtivas(e.target.checked)}
              />
              <Label htmlFor="propagandas_ativas">Propagandas na TV</Label>
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>Descrição</Label>
              <Input value={descricao} onChange={(e) => setDescricao(e.target.value)} />
            </div>
            {error && <p className="text-sm text-destructive md:col-span-2">{error}</p>}
            <div className="flex gap-2 md:col-span-2">
              <Button type="submit" disabled={loading}>
                {loading ? "Salvando..." : editing ? "Atualizar" : "Adicionar"}
              </Button>
              {editing && (
                <Button type="button" variant="outline" onClick={resetForm}>
                  Cancelar
                </Button>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Lista</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {setores.map((s) => (
            <div key={s.id} className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <p className="font-medium">{s.nome}</p>
                <p className="text-xs text-muted-foreground">
                  Código: {s.senha_setor || "—"} · {s.descricao || "Sem descrição"}
                </p>
                <p className="text-xs text-muted-foreground">
                  Operadores: {s.modo_identificacao_operador === "pin" ? "PIN numérico" : "Clique na foto"}
                  {" · "}
                  TV: {s.propagandas_ativas ? "Propagandas ativas" : "Layout padrão"}
                </p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={() => togglePropagandas(s)}>
                  {s.propagandas_ativas ? "Desligar TV ads" : "Ligar TV ads"}
                </Button>
                <Button variant="outline" size="sm" onClick={() => startEdit(s)}>
                  Editar
                </Button>
                <Button variant="destructive" size="sm" onClick={() => onDelete(s.id)}>
                  Excluir
                </Button>
              </div>
            </div>
          ))}
          {!setores.length && <p className="text-sm text-muted-foreground">Nenhum setor cadastrado.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
