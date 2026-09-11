"use client";

import { FormEvent, useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, type Operador, type Setor } from "@/lib/api";

export default function EditOperadorPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [operador, setOperador] = useState<Operador | null>(null);
  const [setores, setSetores] = useState<Setor[]>([]);
  const [nome, setNome] = useState("");
  const [setorId, setSetorId] = useState("");
  const [foto, setFoto] = useState<File | null>(null);
  const [removerFoto, setRemoverFoto] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    Promise.all([
      apiFetch<Operador[]>("/api/v1/admin/operadores"),
      apiFetch<Setor[]>("/api/v1/admin/setores"),
    ])
      .then(([ops, sets]) => {
        const op = ops.find((o) => String(o.id) === params.id) || null;
        setOperador(op);
        setSetores(sets);
        if (op) {
          setNome(op.nome);
          setSetorId(String(op.setor_id || ""));
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, [params.id]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!operador) return;
    setLoading(true);
    setError(null);
    try {
      const form = new FormData();
      form.set("nome", nome);
      form.set("setor_id", setorId);
      if (removerFoto) form.set("remover_foto", "1");
      if (foto) form.set("foto_perfil", foto);
      await apiFetch(`/api/v1/admin/operadores/${operador.id}`, { method: "PUT", body: form });
      router.push("/admin/operadores");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao salvar");
    } finally {
      setLoading(false);
    }
  }

  if (!operador && !error) return <p className="text-muted-foreground">Carregando...</p>;
  if (!operador) return <p className="text-destructive">{error}</p>;

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-2xl font-bold">Editar operador</h1>
      <Card>
        <CardHeader>
          <CardTitle>{operador.nome}</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
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
            {operador.foto_perfil && !removerFoto && (
              <div className="flex items-center gap-3">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={`/uploads/${operador.foto_perfil}`} alt="" className="h-16 w-16 rounded-full object-cover" />
                <Button type="button" variant="outline" size="sm" onClick={() => setRemoverFoto(true)}>
                  Remover foto
                </Button>
              </div>
            )}
            <div className="space-y-2">
              <Label>Nova foto</Label>
              <Input type="file" accept="image/*" onChange={(e) => setFoto(e.target.files?.[0] || null)} />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="flex gap-2">
              <Button type="submit" disabled={loading}>
                {loading ? "Salvando..." : "Salvar"}
              </Button>
              <Button type="button" variant="outline" onClick={() => router.push("/admin/operadores")}>
                Cancelar
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
