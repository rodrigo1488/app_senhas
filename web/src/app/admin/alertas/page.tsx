"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

type AlertaLog = {
  id: number;
  tipo: string;
  severidade: string;
  mensagem: string;
  setor_id: number | null;
  setor: string | null;
  ocorrido_em: string | null;
  enviado_telegram?: boolean;
  enviado_whatsapp?: boolean;
};

const ROTULO: Record<string, string> = {
  sem_retirada: "Sem retirada",
  sem_chamada: "Sem chamada",
  sem_chamada_recente: "Hora sem chamada",
};

function horaDe(iso: string | null) {
  if (!iso) return "";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return iso.slice(11, 16);
  return data.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function diaDe(iso: string | null) {
  if (!iso) return "Sem data";
  const data = new Date(iso);
  if (Number.isNaN(data.getTime())) return iso.slice(0, 10);
  return data.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });
}

function chaveDia(iso: string | null) {
  return iso ? iso.slice(0, 10) : "";
}

export default function AlertasPage() {
  const [itens, setItens] = useState<AlertaLog[]>([]);
  const [erro, setErro] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(true);

  const carregar = useCallback(() => {
    setCarregando(true);
    setErro(null);
    apiFetch<{ itens: AlertaLog[] }>("/api/v1/admin/alertas")
      .then((dados) => setItens(dados.itens ?? []))
      .catch((e) => setErro(e instanceof Error ? e.message : "Erro ao carregar alertas"))
      .finally(() => setCarregando(false));
  }, []);

  useEffect(() => {
    carregar();
  }, [carregar]);

  const grupos: { dia: string; itens: AlertaLog[] }[] = [];
  for (const item of itens) {
    const dia = chaveDia(item.ocorrido_em);
    const atual = grupos[grupos.length - 1];
    if (!atual || atual.dia !== dia) {
      grupos.push({ dia, itens: [item] });
    } else {
      atual.itens.push(item);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Alertas</h1>
        <p className="text-muted-foreground">
          Linha do tempo dos horários sem retirada e sem chamada de senha
        </p>
      </div>

      {erro ? <p className="text-destructive">{erro}</p> : null}
      {carregando && !itens.length ? (
        <p className="text-muted-foreground">Carregando alertas...</p>
      ) : null}
      {!carregando && !itens.length ? (
        <p className="text-muted-foreground">Nenhum alerta registrado.</p>
      ) : null}

      <div className="space-y-8">
        {grupos.map((grupo) => (
          <section key={grupo.dia || "sem-data"} className="space-y-3">
            <h2 className="text-sm font-semibold text-muted-foreground">{diaDe(grupo.itens[0]?.ocorrido_em ?? null)}</h2>
            <ol className="relative space-y-4 border-l border-border pl-6">
              {grupo.itens.map((item) => (
                <li key={item.id} className="relative">
                  <span
                    className={cn(
                      "absolute -left-[1.65rem] top-1.5 h-3 w-3 rounded-full border-2 border-background",
                      item.severidade === "critical" ? "bg-destructive" : "bg-primary",
                    )}
                  />
                  <div
                    className={cn(
                      "rounded-lg border px-4 py-3",
                      item.severidade === "critical"
                        ? "border-destructive/40 bg-destructive/10"
                        : "border-primary/30 bg-primary/5",
                    )}
                  >
                    <div className="mb-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                      <time dateTime={item.ocorrido_em ?? undefined}>{horaDe(item.ocorrido_em)}</time>
                      <span>{ROTULO[item.tipo] ?? item.tipo}</span>
                      {item.setor ? <span>{item.setor}</span> : null}
                      {item.enviado_telegram ? <span>Telegram</span> : null}
                      {item.enviado_whatsapp ? <span>WhatsApp</span> : null}
                    </div>
                    <p className="text-sm">{item.mensagem}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>
    </div>
  );
}
