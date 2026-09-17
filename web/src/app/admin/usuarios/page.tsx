"use client";

import { FormEvent, useEffect, useState } from "react";
import { UserCog } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, rotuloPapel, type PainelUsuario, type PapelPainel, type Setor } from "@/lib/api";

export default function UsuariosPage() {
  const [itens, setItens] = useState<PainelUsuario[]>([]);
  const [setores, setSetores] = useState<Setor[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [nome, setNome] = useState("");
  const [papel, setPapel] = useState<PapelPainel>("gerente");
  const [setorIds, setSetorIds] = useState<number[]>([]);

  async function load() {
    const [users, secs] = await Promise.all([
      apiFetch<PainelUsuario[]>("/api/v1/admin/usuarios"),
      apiFetch<Setor[]>("/api/v1/admin/setores"),
    ]);
    setItens(users);
    setSetores(secs);
  }

  useEffect(() => {
    load().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);

  function toggleSetor(id: number) {
    setSetorIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await apiFetch("/api/v1/admin/usuarios", {
        method: "POST",
        body: JSON.stringify({
          email,
          senha,
          nome,
          papel,
          setor_ids: papel === "gerente" ? setorIds : [],
        }),
      });
      setEmail("");
      setSenha("");
      setNome("");
      setPapel("gerente");
      setSetorIds([]);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar");
    } finally {
      setLoading(false);
    }
  }

  async function onDelete(id: number) {
    if (!confirm("Remover este usuário?")) return;
    await apiFetch(`/api/v1/admin/usuarios/${id}`, { method: "DELETE" });
    await load();
  }

  async function saveSetores(user: PainelUsuario, nextIds: number[]) {
    await apiFetch(`/api/v1/admin/usuarios/${user.id}`, {
      method: "PUT",
      body: JSON.stringify({ setor_ids: nextIds, papel: user.papel }),
    });
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Usuários do painel</h1>
        <p className="text-muted-foreground">
          Administradores veem tudo. Gerentes ficam limitados aos setores atribuídos.
          Marketing gerencia apenas mídias e TVs.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UserCog className="h-5 w-5" /> Novo usuário
          </CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={onCreate}>
            <div className="space-y-2">
              <Label htmlFor="nome">Nome</Label>
              <Input id="nome" value={nome} onChange={(e) => setNome(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="senha">Senha</Label>
              <Input
                id="senha"
                type="password"
                required
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="papel">Papel</Label>
              <select
                id="papel"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={papel}
                onChange={(e) => setPapel(e.target.value as PapelPainel)}
              >
                <option value="admin">Administrador</option>
                <option value="gerente">Gerente</option>
                <option value="marketing">Marketing</option>
              </select>
            </div>
            {papel === "gerente" ? (
              <div className="space-y-2 md:col-span-2">
                <Label>Setores responsáveis</Label>
                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {setores.map((s) => (
                    <label
                      key={s.id}
                      className="flex items-center gap-2 rounded-md border border-border px-3 py-2 text-sm"
                    >
                      <input
                        type="checkbox"
                        checked={setorIds.includes(s.id)}
                        onChange={() => toggleSetor(s.id)}
                      />
                      {s.nome}
                    </label>
                  ))}
                </div>
              </div>
            ) : null}
            {error ? <p className="text-sm text-destructive md:col-span-2">{error}</p> : null}
            <div className="md:col-span-2">
              <Button type="submit" disabled={loading}>
                {loading ? "Salvando…" : "Cadastrar"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      <div className="space-y-3">
        {itens.map((u) => (
          <Card key={u.id}>
            <CardContent className="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="font-semibold">{u.nome || u.email}</p>
                <p className="text-sm text-muted-foreground">{u.email}</p>
                <p className="mt-1 text-sm">
                  Papel: <span className="font-medium">{rotuloPapel(u.papel)}</span>
                </p>
                {u.papel === "gerente" ? (
                  <div className="mt-2 grid gap-1 sm:grid-cols-2">
                    {setores.map((s) => {
                      const checked = u.setor_ids.includes(s.id);
                      return (
                        <label key={s.id} className="flex items-center gap-2 text-sm">
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={() => {
                              const next = checked
                                ? u.setor_ids.filter((id) => id !== s.id)
                                : [...u.setor_ids, s.id];
                              saveSetores(u, next).catch((e) =>
                                setError(e instanceof Error ? e.message : "Erro"),
                              );
                            }}
                          />
                          {s.nome}
                        </label>
                      );
                    })}
                  </div>
                ) : (
                  <p className="mt-1 text-xs text-muted-foreground">
                    {u.papel === "marketing"
                      ? "Acesso apenas a mídias e TVs"
                      : "Acesso a todos os setores"}
                  </p>
                )}
              </div>
              <Button variant="outline" size="sm" onClick={() => onDelete(u.id)}>
                Remover
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
