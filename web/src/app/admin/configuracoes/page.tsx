"use client";

import { FormEvent, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api";

type Config = {
  nome_empresa: string;
  ngrok_url: string;
  proporcao_normais: string;
  limite_preferenciais_alerta: string;
};

export default function ConfiguracoesPage() {
  const [config, setConfig] = useState<Config | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Config>("/api/v1/admin/configuracao")
      .then(setConfig)
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);

  async function saveEmpresa(e: FormEvent) {
    e.preventDefault();
    if (!config) return;
    setMessage(null);
    setError(null);
    try {
      await apiFetch("/api/v1/admin/configuracao/empresa", {
        method: "PUT",
        body: JSON.stringify({ nome_empresa: config.nome_empresa }),
      });
      setMessage("Nome da empresa salvo.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    }
  }

  async function saveNgrok(e: FormEvent) {
    e.preventDefault();
    if (!config) return;
    setMessage(null);
    setError(null);
    try {
      await apiFetch("/api/v1/admin/configuracao/ngrok", {
        method: "PUT",
        body: JSON.stringify({ ngrok_url: config.ngrok_url }),
      });
      setMessage("URL ngrok salva.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    }
  }

  async function saveFila(e: FormEvent) {
    e.preventDefault();
    if (!config) return;
    setMessage(null);
    setError(null);
    try {
      await apiFetch("/api/v1/admin/configuracao/fila", {
        method: "PUT",
        body: JSON.stringify({
          proporcao_normais: config.proporcao_normais,
          limite_preferenciais_alerta: config.limite_preferenciais_alerta,
        }),
      });
      setMessage("Parâmetros de fila salvos.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    }
  }

  if (!config && !error) return <p className="text-muted-foreground">Carregando...</p>;
  if (!config) return <p className="text-destructive">{error}</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Configurações</h1>
        <p className="text-muted-foreground">Empresa, notificações externas e fila</p>
      </div>

      {message && <p className="text-sm text-emerald-600">{message}</p>}
      {error && <p className="text-sm text-destructive">{error}</p>}

      <Card>
        <CardHeader>
          <CardTitle>Empresa</CardTitle>
          <CardDescription>Nome impresso nos tickets e no painel</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3 md:flex-row md:items-end" onSubmit={saveEmpresa}>
            <div className="flex-1 space-y-2">
              <Label>Nome da empresa</Label>
              <Input
                value={config.nome_empresa}
                onChange={(e) => setConfig({ ...config, nome_empresa: e.target.value })}
              />
            </div>
            <Button type="submit">Salvar</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Ngrok / URL pública</CardTitle>
          <CardDescription>Base para QR Code de notificação do cliente</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3 md:flex-row md:items-end" onSubmit={saveNgrok}>
            <div className="flex-1 space-y-2">
              <Label>URL</Label>
              <Input
                value={config.ngrok_url}
                onChange={(e) => setConfig({ ...config, ngrok_url: e.target.value })}
                placeholder="https://xxxx.ngrok-free.app"
              />
            </div>
            <Button type="submit">Salvar</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Fila</CardTitle>
          <CardDescription>Proporção normal/preferencial e alerta</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={saveFila}>
            <div className="space-y-2">
              <Label>Proporção de normais</Label>
              <Input
                value={config.proporcao_normais}
                onChange={(e) => setConfig({ ...config, proporcao_normais: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Limite preferenciais (alerta)</Label>
              <Input
                value={config.limite_preferenciais_alerta}
                onChange={(e) =>
                  setConfig({ ...config, limite_preferenciais_alerta: e.target.value })
                }
              />
            </div>
            <Button type="submit" className="md:w-fit">
              Salvar
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
