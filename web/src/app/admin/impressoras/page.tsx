"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, setorEhAtendimento, type Impressora, type Setor } from "@/lib/api";

export default function ImpressorasPage() {
  const [impressoras, setImpressoras] = useState<Impressora[]>([]);
  const [setores, setSetores] = useState<Setor[]>([]);
  const [nome, setNome] = useState("");
  const [ip, setIp] = useState("");
  const [porta, setPorta] = useState("9100");
  const [setorId, setSetorId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function load() {
    const [imps, sets] = await Promise.all([
      apiFetch<Impressora[]>("/api/v1/admin/impressoras"),
      apiFetch<Setor[]>("/api/v1/admin/setores"),
    ]);
    setImpressoras(imps);
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
      await apiFetch("/api/v1/admin/impressoras", {
        method: "POST",
        body: JSON.stringify({
          nome,
          ip,
          porta: Number(porta),
          setor_id: Number(setorId),
        }),
      });
      setNome("");
      setIp("");
      setPorta("9100");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao criar");
    } finally {
      setLoading(false);
    }
  }

  async function onDelete(id: number) {
    if (!confirm("Excluir esta impressora?")) return;
    await apiFetch(`/api/v1/admin/impressoras/${id}`, { method: "DELETE" });
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Impressoras</h1>
        <p className="text-muted-foreground">Impressoras térmicas ESC/POS por setor</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Nova impressora</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={onCreate}>
            <div className="space-y-2">
              <Label>Nome</Label>
              <Input value={nome} onChange={(e) => setNome(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label>IP</Label>
              <Input value={ip} onChange={(e) => setIp(e.target.value)} required placeholder="192.168.0.50" />
            </div>
            <div className="space-y-2">
              <Label>Porta</Label>
              <Input value={porta} onChange={(e) => setPorta(e.target.value)} required />
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
          {impressoras.map((imp) => (
            <div key={imp.id} className="flex items-center justify-between rounded-lg border p-3">
              <div>
                <p className="font-medium">{imp.nome}</p>
                <p className="text-xs text-muted-foreground">
                  {imp.ip}:{imp.porta} · {imp.setor_nome || "Sem setor"}
                </p>
              </div>
              <Button variant="destructive" size="sm" onClick={() => onDelete(imp.id)}>
                Excluir
              </Button>
            </div>
          ))}
          {!impressoras.length && <p className="text-sm text-muted-foreground">Nenhuma impressora cadastrada.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
