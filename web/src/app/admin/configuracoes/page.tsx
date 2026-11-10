"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch } from "@/lib/api";

type WhatsappStatus = {
  status?: string;
  connected?: boolean;
  jid?: string | null;
  qr_data_url?: string | null;
  error?: string;
};

type AlertasConfig = {
  telegram_ativo: boolean;
  telegram_bot_token: string;
  telegram_chat_id: string;
  whatsapp_ativo: boolean;
  whatsapp_destino: string;
  tipos: string[];
  whatsapp?: WhatsappStatus;
};

type Config = {
  nome_empresa: string;
  ngrok_url: string;
  modo_chamada: string;
  proporcao_normais: string;
  limite_preferenciais_alerta: string;
  posicao_senhas_tv: string;
  alertas?: AlertasConfig;
};

const TIPOS_ALERTA = [
  { id: "sem_retirada", label: "Hora sem retirada de senha" },
  { id: "sem_chamada", label: "Hora sem chamada (por setor)" },
  { id: "sem_chamada_recente", label: "Mais de 1h sem chamar" },
];

function alertasPadrao(): AlertasConfig {
  return {
    telegram_ativo: false,
    telegram_bot_token: "",
    telegram_chat_id: "",
    whatsapp_ativo: false,
    whatsapp_destino: "",
    tipos: TIPOS_ALERTA.map((t) => t.id),
    whatsapp: { status: "unknown", connected: false },
  };
}

export default function ConfiguracoesPage() {
  const [config, setConfig] = useState<Config | null>(null);
  const [alertas, setAlertas] = useState<AlertasConfig>(alertasPadrao());
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [testando, setTestando] = useState<"telegram" | "whatsapp" | null>(null);

  const carregarWhatsapp = useCallback(() => {
    apiFetch<WhatsappStatus>("/api/v1/admin/alertas/whatsapp/status")
      .then((status) => setAlertas((atual) => ({ ...atual, whatsapp: status })))
      .catch(() => {
        /* serviço pode estar subindo */
      });
  }, []);

  useEffect(() => {
    apiFetch<Config>("/api/v1/admin/configuracao")
      .then((c) => {
        setConfig({
          ...c,
          modo_chamada:
            c.modo_chamada === "preferencial_primeiro" ? "preferencial_primeiro" : "proporcao",
          posicao_senhas_tv: c.posicao_senhas_tv === "inferior" ? "inferior" : "superior",
        });
        if (c.alertas) {
          setAlertas({
            ...alertasPadrao(),
            ...c.alertas,
            tipos: c.alertas.tipos?.length ? c.alertas.tipos : alertasPadrao().tipos,
          });
        }
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erro"));
  }, []);

  useEffect(() => {
    carregarWhatsapp();
    const timer = window.setInterval(carregarWhatsapp, 4000);
    return () => window.clearInterval(timer);
  }, [carregarWhatsapp]);

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

  async function saveAlertas(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    setError(null);
    try {
      const salvo = await apiFetch<AlertasConfig>("/api/v1/admin/alertas/notificacoes", {
        method: "PUT",
        body: JSON.stringify({
          telegram_ativo: alertas.telegram_ativo,
          telegram_bot_token: alertas.telegram_bot_token,
          telegram_chat_id: alertas.telegram_chat_id,
          whatsapp_ativo: alertas.whatsapp_ativo,
          whatsapp_destino: alertas.whatsapp_destino,
          tipos: alertas.tipos,
        }),
      });
      setAlertas({
        ...alertasPadrao(),
        ...salvo,
        tipos: salvo.tipos?.length ? salvo.tipos : alertasPadrao().tipos,
      });
      setMessage("Notificações de alerta salvas.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro");
    }
  }

  async function testarCanal(canal: "telegram" | "whatsapp") {
    setTestando(canal);
    setMessage(null);
    setError(null);
    try {
      await apiFetch("/api/v1/admin/alertas/notificacoes/teste", {
        method: "POST",
        body: JSON.stringify({ canal, mensagem: `Teste CompuFlow (${canal})` }),
      });
      setMessage(`Mensagem de teste enviada para ${canal}.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro no teste");
    } finally {
      setTestando(null);
    }
  }

  async function logoutWhatsapp() {
    setMessage(null);
    setError(null);
    try {
      const status = await apiFetch<WhatsappStatus>("/api/v1/admin/alertas/whatsapp/logout", {
        method: "POST",
      });
      setAlertas((atual) => ({ ...atual, whatsapp: status }));
      setMessage("Sessão WhatsApp encerrada. Escaneie o novo QR.");
      window.setTimeout(carregarWhatsapp, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao desconectar");
    }
  }

  async function gerarQrWhatsapp() {
    setMessage(null);
    setError(null);
    try {
      const status = await apiFetch<WhatsappStatus>("/api/v1/admin/alertas/whatsapp/reconnect", {
        method: "POST",
      });
      setAlertas((atual) => ({ ...atual, whatsapp: status }));
      setMessage("Gerando novo QR do WhatsApp...");
      window.setTimeout(carregarWhatsapp, 1500);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erro ao gerar QR");
    }
  }

  function toggleTipo(id: string) {
    setAlertas((atual) => {
      const tem = atual.tipos.includes(id);
      return {
        ...atual,
        tipos: tem ? atual.tipos.filter((t) => t !== id) : [...atual.tipos, id],
      };
    });
  }

  if (!config && !error) return <p className="text-muted-foreground">Carregando...</p>;
  if (!config) return <p className="text-destructive">{error}</p>;

  const wa = alertas.whatsapp || {};
  const waLabel = wa.connected
    ? `Conectado${wa.jid ? ` · ${wa.jid}` : ""}`
    : wa.status === "qr"
      ? "Aguardando leitura do QR"
      : wa.status === "unreachable"
        ? "Serviço WhatsApp indisponível"
        : wa.status || "Desconectado";

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
          <CardTitle>Alertas · Telegram e WhatsApp</CardTitle>
          <CardDescription>
            O CompuFlow envia o texto do alerta direto. WhatsApp usa Baileys (escaneie o QR com o
            celular).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-6" onSubmit={saveAlertas}>
            <div className="space-y-3">
              <p className="text-sm font-medium">Tipos enviados</p>
              <div className="grid gap-2 sm:grid-cols-3">
                {TIPOS_ALERTA.map((tipo) => (
                  <label key={tipo.id} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={alertas.tipos.includes(tipo.id)}
                      onChange={() => toggleTipo(tipo.id)}
                    />
                    {tipo.label}
                  </label>
                ))}
              </div>
            </div>

            <div className="grid gap-6 lg:grid-cols-2">
              <div className="space-y-3 rounded-lg border p-4">
                <label className="flex items-center gap-2 text-sm font-medium">
                  <input
                    type="checkbox"
                    checked={alertas.telegram_ativo}
                    onChange={(e) =>
                      setAlertas({ ...alertas, telegram_ativo: e.target.checked })
                    }
                  />
                  Telegram ativo
                </label>
                <div className="space-y-2">
                  <Label>Bot token</Label>
                  <Input
                    value={alertas.telegram_bot_token}
                    onChange={(e) =>
                      setAlertas({ ...alertas, telegram_bot_token: e.target.value })
                    }
                    placeholder="123456:ABC..."
                  />
                </div>
                <div className="space-y-2">
                  <Label>Chat ID</Label>
                  <Input
                    value={alertas.telegram_chat_id}
                    onChange={(e) =>
                      setAlertas({ ...alertas, telegram_chat_id: e.target.value })
                    }
                    placeholder="-100123... ou ID do usuário"
                  />
                </div>
                <Button
                  type="button"
                  variant="outline"
                  disabled={testando !== null}
                  onClick={() => testarCanal("telegram")}
                >
                  {testando === "telegram" ? "Enviando..." : "Testar Telegram"}
                </Button>
              </div>

              <div className="space-y-3 rounded-lg border p-4">
                <label className="flex items-center gap-2 text-sm font-medium">
                  <input
                    type="checkbox"
                    checked={alertas.whatsapp_ativo}
                    onChange={(e) =>
                      setAlertas({ ...alertas, whatsapp_ativo: e.target.checked })
                    }
                  />
                  WhatsApp ativo (Baileys)
                </label>
                <div className="space-y-2">
                  <Label>Destino (DDI + número)</Label>
                  <Input
                    value={alertas.whatsapp_destino}
                    onChange={(e) =>
                      setAlertas({ ...alertas, whatsapp_destino: e.target.value })
                    }
                    placeholder="5511999999999"
                  />
                </div>
                <p className="text-xs text-muted-foreground">Status: {waLabel}</p>
                {wa.qr_data_url ? (
                  <div className="space-y-2">
                    <p className="text-sm">Escaneie no WhatsApp → Aparelhos conectados</p>
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={wa.qr_data_url}
                      alt="QR WhatsApp"
                      className="h-56 w-56 rounded-md border bg-white p-2"
                    />
                  </div>
                ) : wa.status === "logged_out" || wa.status === "starting" || wa.status === "reconnecting" ? (
                  <p className="text-sm text-muted-foreground">
                    Aguardando novo QR... se não aparecer, clique em Gerar novo QR.
                  </p>
                ) : null}
                <div className="flex flex-wrap gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    disabled={testando !== null}
                    onClick={() => testarCanal("whatsapp")}
                  >
                    {testando === "whatsapp" ? "Enviando..." : "Testar WhatsApp"}
                  </Button>
                  <Button type="button" variant="outline" onClick={gerarQrWhatsapp}>
                    Gerar novo QR
                  </Button>
                  <Button type="button" variant="outline" onClick={logoutWhatsapp}>
                    Desconectar WhatsApp
                  </Button>
                </div>
              </div>
            </div>

            <Button type="submit">Salvar notificações</Button>
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
