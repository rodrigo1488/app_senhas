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
  modo_chamada: string;
  proporcao_normais: string;
  limite_preferenciais_alerta: string;
  posicao_senhas_tv: string;
};

export default function ConfiguracoesPage() {
  const [config, setConfig] = useState<Config | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    apiFetch<Config>("/api/v1/admin/configuracao")
      .then((c) =>
        setConfig({
          ...c,
          modo_chamada:
            c.modo_chamada === "preferencial_primeiro" ? "preferencial_primeiro" : "proporcao",
          posicao_senhas_tv: c.posicao_senhas_tv === "inferior" ? "inferior" : "superior",
        }),
      )
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

  async function saveTv(e: FormEvent) {
    e.preventDefault();
    if (!config) return;
    setMessage(null);
    setError(null);
    try {
      await apiFetch("/api/v1/admin/configuracao/tv", {
        method: "PUT",
        body: JSON.stringify({ posicao_senhas_tv: config.posicao_senhas_tv }),
      });
      setMessage("Posição das senhas salva.");
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
          modo_chamada: config.modo_chamada,
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
        <p className="text-muted-foreground">Empresa, painel da TV, notificações externas e fila</p>
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
          <CardTitle>URL pública do painel (QR)</CardTitle>
          <CardDescription>
            Domínio usado no QR impresso para o cliente abrir `/acompanhar`. Ex.:{" "}
            <code>https://seu-dominio.com</code> ou o túnel do Next — não use a URL da API (:5000).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-3 md:flex-row md:items-end" onSubmit={saveNgrok}>
            <div className="flex-1 space-y-2">
              <Label>URL do painel web</Label>
              <Input
                value={config.ngrok_url}
                onChange={(e) => setConfig({ ...config, ngrok_url: e.target.value })}
                placeholder="https://app.seudominio.com"
              />
            </div>
            <Button type="submit">Salvar</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Painel da TV</CardTitle>
          <CardDescription>
            Onde a faixa de senhas aparece no layout de propagandas, no formato horizontal e no
            vertical.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4" onSubmit={saveTv}>
            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">Posição das senhas</legend>
              <label
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 ${
                  config.posicao_senhas_tv === "superior"
                    ? "border-primary bg-accent/40"
                    : "border-input"
                }`}
              >
                <input
                  type="radio"
                  name="posicao_senhas_tv"
                  className="mt-1"
                  checked={config.posicao_senhas_tv === "superior"}
                  onChange={() => setConfig({ ...config, posicao_senhas_tv: "superior" })}
                />
                <span>
                  <span className="block font-medium">Parte superior</span>
                  <span className="text-sm text-muted-foreground">
                    Preferencial e Normal ficam acima da mídia.
                  </span>
                </span>
              </label>
              <label
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 ${
                  config.posicao_senhas_tv === "inferior"
                    ? "border-primary bg-accent/40"
                    : "border-input"
                }`}
              >
                <input
                  type="radio"
                  name="posicao_senhas_tv"
                  className="mt-1"
                  checked={config.posicao_senhas_tv === "inferior"}
                  onChange={() => setConfig({ ...config, posicao_senhas_tv: "inferior" })}
                />
                <span>
                  <span className="block font-medium">Parte inferior</span>
                  <span className="text-sm text-muted-foreground">
                    Preferencial e Normal ficam abaixo da mídia.
                  </span>
                </span>
              </label>
            </fieldset>
            <Button type="submit" className="md:w-fit">
              Salvar
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Fila</CardTitle>
          <CardDescription>Como o operador chama a próxima senha</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4" onSubmit={saveFila}>
            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">Forma da fila</legend>
              <label
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 ${
                  config.modo_chamada === "proporcao" ? "border-primary bg-accent/40" : "border-input"
                }`}
              >
                <input
                  type="radio"
                  name="modo_chamada"
                  className="mt-1"
                  checked={config.modo_chamada === "proporcao"}
                  onChange={() => setConfig({ ...config, modo_chamada: "proporcao" })}
                />
                <span>
                  <span className="block font-medium">Proporção (intercalada)</span>
                  <span className="text-sm text-muted-foreground">
                    Chama senhas normais e preferenciais intercaladas. Exemplo: 2 normais, depois 1
                    preferencial.
                  </span>
                </span>
              </label>
              <label
                className={`flex cursor-pointer items-start gap-3 rounded-lg border p-3 ${
                  config.modo_chamada === "preferencial_primeiro"
                    ? "border-primary bg-accent/40"
                    : "border-input"
                }`}
              >
                <input
                  type="radio"
                  name="modo_chamada"
                  className="mt-1"
                  checked={config.modo_chamada === "preferencial_primeiro"}
                  onChange={() => setConfig({ ...config, modo_chamada: "preferencial_primeiro" })}
                />
                <span>
                  <span className="block font-medium">Preferenciais primeiro</span>
                  <span className="text-sm text-muted-foreground">
                    Esgota todas as senhas preferenciais na ordem de chegada e só depois chama as
                    normais.
                  </span>
                </span>
              </label>
            </fieldset>
            {config.modo_chamada === "proporcao" && (
              <div className="grid gap-4 md:grid-cols-2">
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
              </div>
            )}
            <Button type="submit" className="md:w-fit">
              Salvar
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
