"use client";

import { type ReactNode } from "react";
import { UserRound } from "lucide-react";
import { cn } from "@/lib/utils";
import { uploadsUrl, type TvRecentCall, type TvSenha } from "@/lib/tv-api";

type Props = {
  chamadas: TvRecentCall[];
  pendentes: TvSenha[];
  currentImage: string | null;
};

export function TvFlowLayout({ chamadas, pendentes, currentImage }: Props) {
  const atual = chamadas[0] ?? null;
  const anteriores = chamadas.slice(1, 4);
  const proximas = pendentes.slice(0, 5);
  const animationKey = atual?.senha_id ?? atual?.senha ?? "empty";

  return (
    <div className="grid h-full w-full grid-cols-[minmax(0,2.15fr)_minmax(22rem,1fr)] gap-[clamp(0.75rem,1.25vw,1.25rem)] bg-[#e7e3dc] p-[clamp(0.75rem,1.25vw,1.25rem)] text-[#1b1b1b]">
      <section className="relative min-h-0 overflow-hidden rounded-[clamp(1.5rem,2.5vw,2.75rem)] bg-[#d9d6cf]">
        {currentImage ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={currentImage} alt="Propaganda" className="h-full w-full object-cover" />
        ) : (
          <div className="flex h-full flex-col items-center justify-center bg-[#d8d5ce] px-12 text-center">
            <div className="mb-6 h-px w-24 bg-black/25" />
            <p className="text-[clamp(1.4rem,2.5vw,2.6rem)] font-medium tracking-[-0.03em] text-black/45">
              Espaço de mídia
            </p>
            <p className="mt-2 text-[clamp(0.75rem,1vw,1rem)] text-black/35">
              Ative e cadastre propagandas no painel administrativo
            </p>
          </div>
        )}
        <div className="pointer-events-none absolute inset-0 ring-1 ring-inset ring-black/10" />
      </section>

      <aside className="flex min-h-0 flex-col overflow-hidden rounded-[clamp(1.5rem,2.5vw,2.75rem)] bg-[#f4f1ea] shadow-[0_12px_35px_rgba(36,30,20,0.10)]">
        <div className="min-h-0 flex-1 overflow-hidden px-[clamp(1rem,1.6vw,1.6rem)] py-[clamp(1.1rem,1.8vw,1.8rem)]">
          <GroupLabel>Chamadas anteriores</GroupLabel>
          <div
            key={`previous-${animationKey}`}
            className="grid gap-[clamp(0.35rem,0.6vw,0.6rem)]"
          >
            {anteriores.length ? (
              anteriores.map((call, index) => (
                <PreviousCard key={`${call.senha_id}-${call.chamada_em}`} call={call} index={index} />
              ))
            ) : (
              <EmptyLine>Nenhuma chamada anterior</EmptyLine>
            )}
          </div>

          <div
            key={`current-${animationKey}`}
            className="tv-current-enter my-[clamp(0.8rem,1.3vw,1.3rem)] rounded-[clamp(1.25rem,2vw,2rem)] bg-[#e85d04] px-[clamp(1rem,1.5vw,1.5rem)] py-[clamp(1rem,1.8vw,1.8rem)] text-white shadow-[0_12px_26px_rgba(232,93,4,0.24)]"
          >
            <p className="text-[clamp(0.62rem,0.76vw,0.76rem)] font-bold uppercase tracking-[0.2em] text-white/70">
              Chamando agora
            </p>
            {atual ? (
              <>
                <div className="mt-1 flex items-end justify-between gap-3">
                  <p className="text-[clamp(4rem,7.8vw,8rem)] font-black leading-none tracking-[-0.075em] tabular-nums">
                    {atual.senha}
                  </p>
                  <span className="mb-2 text-[clamp(0.68rem,0.85vw,0.85rem)] font-bold uppercase tracking-[0.08em]">
                    {atual.tipo === "preferencial" ? "Preferencial" : "Normal"}
                  </span>
                </div>
                <Operator call={atual} />
              </>
            ) : (
              <p className="py-[clamp(1.1rem,2vw,2rem)] text-[clamp(1.5rem,2.4vw,2.4rem)] font-bold tracking-[-0.04em]">
                Aguardando chamada
              </p>
            )}
          </div>

          <GroupLabel>Próximas senhas</GroupLabel>
          <div
            key={`next-${proximas.map((senha) => senha.id).join("-")}`}
            className="grid gap-[clamp(0.35rem,0.6vw,0.6rem)]"
          >
            {proximas.length ? (
              proximas.map((senha, index) => <NextCard key={senha.id} senha={senha} position={index + 1} />)
            ) : (
              <EmptyLine>Não há senhas aguardando</EmptyLine>
            )}
          </div>
        </div>
      </aside>

      <style jsx global>{`
        @keyframes tv-current-enter {
          from {
            opacity: 0.35;
            transform: translateY(42%);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes tv-row-rise {
          from {
            opacity: 0.25;
            transform: translateY(38px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .tv-current-enter {
          animation: tv-current-enter 620ms cubic-bezier(0.22, 1, 0.36, 1);
        }
        .tv-row-rise {
          animation: tv-row-rise 540ms cubic-bezier(0.22, 1, 0.36, 1) both;
        }
        @media (prefers-reduced-motion: reduce) {
          .tv-current-enter,
          .tv-row-rise {
            animation: none;
          }
        }
      `}</style>
    </div>
  );
}

function GroupLabel({ children }: { children: ReactNode }) {
  return (
    <p className="mb-[clamp(0.4rem,0.65vw,0.65rem)] text-[clamp(0.6rem,0.72vw,0.72rem)] font-bold uppercase tracking-[0.18em] text-black/45">
      {children}
    </p>
  );
}

function PreviousCard({ call, index }: { call: TvRecentCall; index: number }) {
  return (
    <div style={{ opacity: 0.72 - index * 0.16 }}>
      <div
        className="tv-row-rise grid grid-cols-[1fr_auto] items-center rounded-[clamp(0.85rem,1.2vw,1.2rem)] bg-black/[0.045] px-[clamp(0.85rem,1.2vw,1.2rem)] py-[clamp(0.5rem,0.75vw,0.75rem)]"
        style={{ animationDelay: `${index * 45}ms` }}
      >
        <div className="flex min-w-0 items-center gap-3">
          <OperatorPhoto photo={call.operador_foto} />
          <strong className="text-[clamp(1.3rem,2vw,2rem)] tracking-[-0.04em]">{call.senha}</strong>
          <span className="truncate text-[clamp(0.65rem,0.76vw,0.76rem)] text-black/55">
            {call.operador_nome}
          </span>
        </div>
        <TicketType tipo={call.tipo} />
      </div>
    </div>
  );
}

function NextCard({ senha, position }: { senha: TvSenha; position: number }) {
  return (
    <div
      className="tv-row-rise grid grid-cols-[2rem_1fr_auto] items-center gap-2 rounded-[clamp(0.85rem,1.2vw,1.2rem)] bg-white/70 px-[clamp(0.8rem,1.15vw,1.15rem)] py-[clamp(0.48rem,0.72vw,0.72rem)] shadow-[0_2px_8px_rgba(36,30,20,0.06)]"
      style={{ animationDelay: `${position * 40}ms` }}
    >
      <span className="text-[clamp(0.62rem,0.72vw,0.72rem)] font-semibold tabular-nums text-black/35">
        {String(position).padStart(2, "0")}
      </span>
      <strong className="text-[clamp(1.35rem,2vw,2rem)] tracking-[-0.04em]">{senha.senha}</strong>
      <TicketType tipo={senha.tipo} />
    </div>
  );
}

function TicketType({ tipo }: { tipo?: string | null }) {
  const preferencial = tipo === "preferencial";
  return (
    <span
      className={cn(
        "text-[clamp(0.56rem,0.66vw,0.66rem)] font-bold uppercase tracking-[0.1em]",
        preferencial ? "text-[#59388a]" : "text-black/45",
      )}
    >
      {preferencial ? "Pref." : "Normal"}
    </span>
  );
}

function Operator({ call }: { call: TvRecentCall }) {
  const photo = uploadsUrl(call.operador_foto);
  return (
    <div className="mt-[clamp(0.7rem,1vw,1rem)] flex items-center gap-3 border-t border-white/25 pt-[clamp(0.65rem,1vw,1rem)]">
      <div className="flex h-[clamp(2.2rem,3.2vw,3.2rem)] w-[clamp(2.2rem,3.2vw,3.2rem)] shrink-0 items-center justify-center overflow-hidden rounded-xl bg-white/15">
        {photo ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={photo} alt="" className="h-full w-full object-cover" />
        ) : (
          <UserRound className="h-1/2 w-1/2 text-white/75" />
        )}
      </div>
      <div>
        <p className="text-[clamp(0.55rem,0.64vw,0.64rem)] font-semibold uppercase tracking-[0.13em] text-white/65">
          Dirija-se ao atendimento
        </p>
        <p className="text-[clamp(0.9rem,1.25vw,1.25rem)] font-bold">{call.operador_nome || "Operador"}</p>
      </div>
    </div>
  );
}

function OperatorPhoto({ photo }: { photo?: string | null }) {
  const url = uploadsUrl(photo);
  return (
    <div className="flex h-[clamp(2rem,2.7vw,2.7rem)] w-[clamp(2rem,2.7vw,2.7rem)] shrink-0 items-center justify-center overflow-hidden rounded-full bg-black/10">
      {url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={url} alt="" className="h-full w-full object-cover" />
      ) : (
        <UserRound className="h-1/2 w-1/2 text-black/35" />
      )}
    </div>
  );
}

function EmptyLine({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-xl border border-dashed border-black/15 px-4 py-3 text-center text-[clamp(0.68rem,0.8vw,0.8rem)] text-black/35">
      {children}
    </div>
  );
}
