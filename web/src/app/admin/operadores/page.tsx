"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, setorEhAtendimento, type Operador, type Setor } from "@/lib/api";

const selectClass = "flex h-10 w-full rounded-lg border border-input bg-card px-3 text-sm";

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
  const [filtroNome, setFiltroNome] = useState("");
  const [filtroSetorId, setFiltroSetorId] = useState("");
  const [filtroPin, setFiltroPin] = useState<"todos" | "com" | "sem">("todos");

  async function load() {
    const [ops, sets] = await Promise.all([
      apiFetch<Operador[]>("/api/v1/admin/operadores"),
      apiFetch<Setor[]>("/api/v1/admin/setores"),
    ]);
    setOperadores(ops);
    const atendimento = sets.filter(setorEhAtendimento);
    setSetores(atendimento);
    if (!setorId && atendimento[0]) setSetorId(String(atendimento[0].id));
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
      if (pin && !/^\d{4}$/.test(pin)) throw new Error("O PIN deve conter exatamente 4 números");
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

  const operadoresFiltrados = useMemo(() => {
    const termo = filtroNome.trim().toLowerCase();
    return operadores.filter((op) => {
      if (termo && !op.nome.toLowerCase().includes(termo)) return false;
      if (filtroSetorId && String(op.setor_id ?? "") !== filtroSetorId) return false;
      if (filtroPin === "com" && !op.tem_pin) return false;
      if (filtroPin === "sem" && op.tem_pin) return false;
      return true;
    });
  }, [operadores, filtroNome, filtroSetorId, filtroPin]);

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
              <Label>PIN numérico (4 dígitos)</Label>
              <Input
                type="password"
                inputMode="numeric"
                autoComplete="new-password"
                value={pin}
                maxLength={4}
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
                maxLength={4}
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
        <CardContent className="space-y-4">
          <div className="grid gap-3 md:grid-cols-3">
            <div className="space-y-2">
              <Label htmlFor="filtro-nome">Buscar por nome</Label>
              <Input
                id="filtro-nome"
                value={filtroNome}
                onChange={(e) => setFiltroNome(e.target.value)}
                placeholder="Ex.: Ana"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="filtro-setor">Setor</Label>
              <select
                id="filtro-setor"
                className={selectClass}
                value={filtroSetorId}
                onChange={(e) => setFiltroSetorId(e.target.value)}
              >
                <option value="">Todos</option>
                {setores.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.nome}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="filtro-pin">PIN</Label>
              <select
                id="filtro-pin"
                className={selectClass}
                value={filtroPin}
                onChange={(e) => setFiltroPin(e.target.value as "todos" | "com" | "sem")}
              >
                <option value="todos">Todos</option>
                <option value="com">Com PIN</option>
                <option value="sem">Sem PIN</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="border-b bg-muted/40 text-left text-muted-foreground">
                  <th className="px-3 py-2.5 font-medium">Operador</th>
                  <th className="px-3 py-2.5 font-medium">Setor</th>
                  <th className="px-3 py-2.5 font-medium">PIN</th>
                  <th className="px-3 py-2.5 font-medium">Avaliação</th>
                  <th className="px-3 py-2.5 text-right font-medium">Ações</th>
                </tr>
              </thead>
              <tbody>
                {operadoresFiltrados.map((op) => (
                  <tr key={op.id} className="border-b last:border-0">
                    <td className="px-3 py-2.5">
                      <div className="flex items-center gap-3">
                        {op.foto_perfil ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={`/uploads/${op.foto_perfil}`}
                            alt=""
                            className="h-9 w-9 rounded-full object-cover"
                          />
                        ) : (
                          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary text-sm font-bold">
                            {op.nome.slice(0, 1)}
                          </div>
                        )}
                        <span className="font-medium">{op.nome}</span>
                      </div>
                    </td>
                    <td className="px-3 py-2.5 text-muted-foreground">{op.setor_nome || "Sem setor"}</td>
                    <td className="px-3 py-2.5">{op.tem_pin ? "Configurado" : "Sem PIN"}</td>
                    <td className="px-3 py-2.5 tabular-nums">
                      {op.nota_media != null ? (
                        <>
                          <span className="font-medium">{op.nota_media.toFixed(2)}</span>
                          <span className="ml-1 text-xs text-muted-foreground">
                            ({op.n_avaliacoes ?? 0})
                          </span>
                        </>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex justify-end gap-2">
                        <Button asChild variant="outline" size="sm">
                          <Link href={`/admin/operadores/${op.id}`}>Editar</Link>
                        </Button>
                        <Button variant="destructive" size="sm" onClick={() => onDelete(op.id)}>
                          Excluir
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!operadores.length ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">
                      Nenhum operador cadastrado.
                    </td>
                  </tr>
                ) : !operadoresFiltrados.length ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">
                      Nenhum operador corresponde aos filtros.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
