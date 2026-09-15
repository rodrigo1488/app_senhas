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

/** True quando o browser fala com a API pelo mesmo origin HTTPS (rewrite Next). */
function usesHttpsSameOriginProxy(base: string): boolean {
  if (typeof window === "undefined") return false;
  if (window.location.protocol !== "https:") return false;
  return !base || base === window.location.origin;
}

/** Socket da TV: autentica com JWT de sessão e entra na room do setor. */
export function connectTvSocket(sessionToken: string): Socket {
  const base = resolveApiBaseUrl();
  // Rewrite do Next/Cloudflare não faz upgrade WebSocket de forma confiável —
  // polling HTTP passa pelo mesmo proxy que já serve `/api/v1`.
  const viaProxy = usesHttpsSameOriginProxy(base);

  return io(base || "/", {
    path: "/socket.io",
    transports: viaProxy ? ["polling"] : ["websocket", "polling"],
    upgrade: !viaProxy,
    auth: { session_token: sessionToken },
    autoConnect: true,
    reconnection: true,
    reconnectionAttempts: Infinity,
    reconnectionDelay: 1500,
    reconnectionDelayMax: 10000,
  });
}
