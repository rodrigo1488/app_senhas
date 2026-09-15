import { io, type Socket } from "socket.io-client";
import { resolveApiBaseUrl } from "@/lib/cliente-socket";
import type { TvAtendimento, TvSenha } from "@/lib/tv-api";

export type FilaAtualizadaPayload = {
  setor_id: number;
  pendentes: TvSenha[];
  atendimentos: TvAtendimento[];
};

export type SenhaChamadaTv = {
  setor_id?: number;
  senha_id?: number | null;
  senha: string;
  tipo?: string | null;
  operador_id?: number | null;
  operador_nome?: string | null;
  operador_foto?: string | null;
};

/** Socket da TV: autentica com JWT de sessão e entra na room do setor. */
export function connectTvSocket(sessionToken: string): Socket {
  const base = resolveApiBaseUrl();
  return io(base || "/", {
    path: "/socket.io",
    transports: ["websocket", "polling"],
    auth: { session_token: sessionToken },
    autoConnect: true,
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1500,
    reconnectionDelayMax: 10000,
  });
}
