"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, type Operador, type Setor } from "@/lib/api";

export default function OperadoresPage() {
  const [operadores, setOperadores] = useState<Operador[]>([]);
  const [setores, setSetores] = useState<Setor[]>([]);
  const [nome, setNome] = useState("");
  const [setorId, setSetorId] = useState("");
  const [foto, setFoto] = useState<File | null>(null);
  const [pin, setPin] = useState("");
  const [confirmarPin, setConfirmarPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    const [ops, sets] = await Promise.all([
      apiFetch<Operador[]>("/api/v1/admin/operadores"),
      apiFetch<Setor[]>("/api/v1/admin/setores"),
    ]);
    setOperadores(ops);
    setSetores(sets);
    if (!setorId && sets[0]) setSetorId(String(sets[0].id));
  }

  useEffect(() => {
    void load().catch((e) => setError(e instanceof Error ? e.message : "Erro"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (pin && !/^\d{4,6}$/.test(pin)) throw new Error("O PIN deve conter de 4 a 6 números");
      if (pin !== confirmarPin) throw new Error("A confirmação do PIN não confere");
      const form = new FormData();
      form.set("nome", nome);
      form.set("setor_id", setorId);
      if (pin) form.set("pin", pin);
      if (foto) form.set("foto_perfil", foto);
      await apiFetch("/api/v1/admin/operadores", { method: "POST", body: form });
      setNome("");
      setFoto(null);
      setPin("");
      setConfirmarPin("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar");
    } finally {
      setLoading(false);
    }
  }

  async function onDelete(id: number) {
    if (!confirm("Excluir este operador?")) return;
    await apiFetch(`/api/v1/admin/operadores/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Operadores</h1>
        <p className="text-muted-foreground">Cadastro de atendentes por setor</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Novo operador</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={onCreate}>
            <div className="space-y-2">
              <Label>Nome</Label>
              <Input value={nome} onChange={(e) => setNome(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label>Setor</Label>
              <select
                className="flex h-10 w-full rounded-lg border border-input bg-card px-3 text-sm"
                value={setorId}
                onChange={(e) => setSetorId(e.target.value)}
                required
              >
                {setores.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nome}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2 md:col-span-2">
              <Label>Foto (opcional)</Label>
              <Input type="file" accept="image/*" onChange={(e) => setFoto(e.target.files?.[0] || null)} />
            </div>
            <div className="space-y-2">
              <Label>PIN numérico (4 a 6 dígitos)</Label>
              <Input
                type="password"
                inputMode="numeric"
                autoComplete="new-password"
                value={pin}
                maxLength={6}
                onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))}
              />
            </div>
            <div className="space-y-2">
              <Label>Confirmar PIN</Label>
              <Input
                type="password"
                inputMode="numeric"
                autoComplete="new-password"
                value={confirmarPin}
                maxLength={6}
                onChange={(e) => setConfirmarPin(e.target.value.replace(/\D/g, ""))}
              />
            </div>
            {error && <p className="text-sm text-destructive md:col-span-2">{error}</p>}
            <Button type="submit" disabled={loading} className="md:col-span-2 md:w-fit">
              {loading ? "Salvando..." : "Adicionar"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Lista</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {operadores.map((op) => (
            <div key={op.id} className="flex items-center justify-between gap-3 rounded-lg border p-3">
              <div className="flex items-center gap-3">
                {op.foto_perfil ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={`/uploads/${op.foto_perfil}`} alt="" className="h-10 w-10 rounded-full object-cover" />
                ) : (
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-secondary text-sm font-bold">
                    {op.nome.slice(0, 1)}
                  </div>
                )}
                <div>
                  <p className="font-medium">{op.nome}</p>
                  <p className="text-xs text-muted-foreground">
                    {op.setor_nome || "Sem setor"} · {op.tem_pin ? "PIN configurado" : "Sem PIN"}
                  </p>
                </div>
              </div>
              <div className="flex gap-2">
                <Button asChild variant="outline" size="sm">
                  <Link href={`/admin/operadores/${op.id}`}>Editar</Link>
                </Button>
                <Button variant="destructive" size="sm" onClick={() => onDelete(op.id)}>
                  Excluir
                </Button>
              </div>
            </div>
          ))}
          {!operadores.length && <p className="text-sm text-muted-foreground">Nenhum operador cadastrado.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
