"use client";

import { FormEvent, type ReactNode, useEffect, useState } from "react";
import { GalleryHorizontalEnd, ListStart, MonitorPlay, RectangleHorizontal, RectangleVertical, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { apiFetch, setorEhStreaming, type Setor } from "@/lib/api";

export default function SetoresPage() {
  const [setores, setSetores] = useState<Setor[]>([]);
  const [editing, setEditing] = useState<Setor | null>(null);
  const [nome, setNome] = useState("");
  const [descricao, setDescricao] = useState("");
  const [senhaSetor, setSenhaSetor] = useState("");
  const [modoIdentificacao, setModoIdentificacao] = useState<"foto" | "pin">("foto");
  const [propagandasAtivas, setPropagandasAtivas] = useState(false);
  const [propagandasClienteAtivas, setPropagandasClienteAtivas] = useState(false);
  const [impressaoViaCliente, setImpressaoViaCliente] = useState(false);
  const [layoutTvWeb, setLayoutTvWeb] = useState<"propaganda" | "fila">("propaganda");
  const [orientacaoTv, setOrientacaoTv] = useState<"horizontal" | "vertical">("horizontal");
  const [tipoSetor, setTipoSetor] = useState<"atendimento" | "streaming">("atendimento");
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
    setPropagandasClienteAtivas(Boolean(setor.propagandas_cliente_ativas));
    setImpressaoViaCliente(Boolean(setor.impressao_via_cliente));
    setLayoutTvWeb(setor.layout_tv_web || "propaganda");
    setOrientacaoTv(setor.orientacao_tv || "horizontal");
    setTipoSetor(setor.tipo_setor === "streaming" ? "streaming" : "atendimento");
  }

  function resetForm() {
    setEditing(null);
    setNome("");
    setDescricao("");
    setSenhaSetor("");
    setModoIdentificacao("foto");
    setPropagandasAtivas(false);
    setPropagandasClienteAtivas(false);
    setImpressaoViaCliente(false);
    setLayoutTvWeb("propaganda");
    setOrientacaoTv("horizontal");
    setTipoSetor("atendimento");
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const body = JSON.stringify({
        nome,
        descricao,
        tipo_setor: tipoSetor,
        senha_setor: tipoSetor === "streaming" ? "" : senhaSetor,
        modo_identificacao_operador: tipoSetor === "streaming" ? "foto" : modoIdentificacao,
        propagandas_ativas: propagandasAtivas,
        propagandas_cliente_ativas: tipoSetor === "streaming" ? false : propagandasClienteAtivas,
        impressao_via_cliente: tipoSetor === "streaming" ? false : impressaoViaCliente,
        layout_tv_web: tipoSetor === "streaming" ? "propaganda" : layoutTvWeb,
        orientacao_tv: orientacaoTv,
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

  async function togglePropagandasCliente(setor: Setor) {
    await apiFetch(`/api/v1/admin/setores/${setor.id}`, {
      method: "PUT",
      body: JSON.stringify({ propagandas_cliente_ativas: !setor.propagandas_cliente_ativas }),
    });
    await load();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Setores</h1>
        <p className="text-muted-foreground">
          Áreas de atendimento (fila e operadores) ou de streaming (apenas TVs de mídia)
        </p>
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
            <fieldset className="space-y-3 md:col-span-2">
              <div>
                <Label>Tipo do setor</Label>
                <p className="mt-1 text-sm text-muted-foreground">
                  Atendimento usa fila e operadores. Streaming é só digital signage.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <LayoutOption
                  active={tipoSetor === "atendimento"}
                  icon={<Users className="h-5 w-5" />}
                  title="Atendimento"
                  description="Fila, senhas, operadores e painel de chamadas."
                  onClick={() => setTipoSetor("atendimento")}
                />
                <LayoutOption
                  active={tipoSetor === "streaming"}
                  icon={<MonitorPlay className="h-5 w-5" />}
                  title="Streaming"
                  description="Apenas TVs de mídia, sem operadores nem senhas."
                  onClick={() => setTipoSetor("streaming")}
                />
              </div>
            </fieldset>
            {tipoSetor === "atendimento" ? (
              <>
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
              </>
            ) : null}
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
            {tipoSetor === "atendimento" ? (
            <>
            <div className="flex items-center gap-3 space-y-0 pt-8">
              <input
                id="propagandas_cliente_ativas"
                type="checkbox"
                className="h-4 w-4 rounded border"
                checked={propagandasClienteAtivas}
                onChange={(e) => setPropagandasClienteAtivas(e.target.checked)}
              />
              <Label htmlFor="propagandas_cliente_ativas">Propagandas na espera do cliente</Label>
            </div>
            <div className="flex items-center gap-3 space-y-0 pt-8 md:col-span-2">
              <input
                id="impressao_via_cliente"
                type="checkbox"
                className="h-4 w-4 rounded border"
                checked={impressaoViaCliente}
                onChange={(e) => setImpressaoViaCliente(e.target.checked)}
              />
              <div>
                <Label htmlFor="impressao_via_cliente">Imprimir senhas pelo tablet do cliente</Label>
                <p className="text-sm text-muted-foreground">
                  Use quando a API está atrás de um túnel e não enxerga a impressora. O APK
                  envia o cupom pela rede local do tablet (cadastre a impressora do setor).
                </p>
              </div>
            </div>
            </>
            ) : null}
            {tipoSetor === "atendimento" ? (
            <fieldset className="space-y-3 md:col-span-2">
              <div>
                <Label>Layout da TV web</Label>
                <p className="mt-1 text-sm text-muted-foreground">
                  Escolha como este setor será exibido ao abrir o painel pelo navegador.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <LayoutOption
                  active={layoutTvWeb === "propaganda"}
                  icon={<GalleryHorizontalEnd className="h-5 w-5" />}
                  title="Propagandas"
                  description="Mídia em destaque com as chamadas em uma faixa inferior."
                  onClick={() => setLayoutTvWeb("propaganda")}
                />
                <LayoutOption
                  active={layoutTvWeb === "fila"}
                  icon={<ListStart className="h-5 w-5" />}
                  title="Fluxo de chamadas"
                  description="Senha atual em destaque, histórico e próximas da fila."
                  onClick={() => setLayoutTvWeb("fila")}
                />
              </div>
            </fieldset>
            ) : null}
            <fieldset className="space-y-3 md:col-span-2">
              <div>
                <Label>Orientação da tela</Label>
                <p className="mt-1 text-sm text-muted-foreground">
                  Use horizontal para TVs deitadas e vertical para telas em pé.
                </p>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <LayoutOption
                  active={orientacaoTv === "horizontal"}
                  icon={<RectangleHorizontal className="h-5 w-5" />}
                  title="Horizontal"
                  description="Layout em paisagem, com a fila ao lado da mídia."
                  onClick={() => setOrientacaoTv("horizontal")}
                />
                <LayoutOption
                  active={orientacaoTv === "vertical"}
                  icon={<RectangleVertical className="h-5 w-5" />}
                  title="Vertical"
                  description="Layout em retrato, com a fila abaixo da mídia."
                  onClick={() => setOrientacaoTv("vertical")}
                />
              </div>
            </fieldset>
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
                <p className="font-medium">
                  {s.nome}
                  {setorEhStreaming(s) ? (
                    <span className="ml-2 rounded-full bg-muted px-2 py-0.5 text-xs font-normal text-muted-foreground">
                      Streaming
                    </span>
                  ) : null}
                </p>
                <p className="text-xs text-muted-foreground">
                  {setorEhStreaming(s)
                    ? s.descricao || "Setor de mídia, sem fila de atendimento"
                    : `Código: ${s.senha_setor || "—"} · ${s.descricao || "Sem descrição"}`}
                </p>
                <p className="text-xs text-muted-foreground">
                  {setorEhStreaming(s) ? (
                    <>
                      TVs de streaming
                      {" · "}
                      Tela: {s.orientacao_tv === "vertical" ? "Vertical" : "Horizontal"}
                      {!s.propagandas_ativas ? " (sem imagens ativas)" : ""}
                    </>
                  ) : (
                    <>
                      Operadores: {s.modo_identificacao_operador === "pin" ? "PIN numérico" : "Clique na foto"}
                      {" · "}
                      TV web: {s.layout_tv_web === "fila" ? "Fluxo de chamadas" : "Propagandas"}
                      {" · "}
                      Tela: {s.orientacao_tv === "vertical" ? "Vertical" : "Horizontal"}
                      {s.layout_tv_web !== "fila" && !s.propagandas_ativas ? " (sem imagens ativas)" : ""}
                      {s.propagandas_cliente_ativas ? " · Espera do cliente: ligada" : " · Espera do cliente: desligada"}
                    </>
                  )}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Button variant="outline" size="sm" onClick={() => togglePropagandas(s)}>
                  {s.propagandas_ativas ? "Desligar TV ads" : "Ligar TV ads"}
                </Button>
                {!setorEhStreaming(s) ? (
                <Button variant="outline" size="sm" onClick={() => togglePropagandasCliente(s)}>
                  {s.propagandas_cliente_ativas ? "Desligar espera" : "Ligar espera"}
                </Button>
                ) : null}
                {!setorEhStreaming(s) ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={async () => {
                    if (
                      !confirm(
                        `Limpar a fila de "${s.nome}"?\n\nTodas as senhas aguardando e em atendimento serão finalizadas.`,
                      )
                    ) {
                      return;
                    }
                    try {
                      await apiFetch(`/api/v1/admin/setores/${s.id}/limpar-fila`, { method: "POST" });
                      setError(null);
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "Erro ao limpar a fila");
                    }
                  }}
                >
                  Limpar fila
                </Button>
                ) : null}
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

function LayoutOption({
  active,
  icon,
  title,
  description,
  onClick,
}: {
  active: boolean;
  icon: ReactNode;
  title: string;
  description: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={active}
      onClick={onClick}
      className={`flex items-start gap-3 rounded-xl border p-4 text-left transition ${
        active
          ? "border-primary bg-primary/5 ring-1 ring-primary"
          : "border-border bg-card hover:border-primary/40 hover:bg-muted/40"
      }`}
    >
      <span
        className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
          active ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground"
        }`}
      >
        {icon}
      </span>
      <span>
        <span className="block font-semibold">{title}</span>
        <span className="mt-1 block text-sm leading-snug text-muted-foreground">{description}</span>
      </span>
    </button>
  );
}
