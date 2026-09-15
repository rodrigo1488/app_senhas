import { io, type Socket } from "socket.io-client";

export type SenhaPosicao = {
  token_unico: string;
  posicao: number;
  senha: string;
  status: string;
  setor_nome: string;
  tem_pedido: boolean;
  pedido: string | null;
  pedido_confirmado: boolean;
  avaliacao_pendente?: boolean;
};

export type SenhaChamada = {
  ticket_token: string;
  senha: string;
  operador_nome?: string;
  operador_foto?: string | null;
  tem_pedido?: boolean;
  pedido?: string | null;
};

export type PedidoStatus = {
  ticket_token: string;
  pedido: string;
  status: string;
  mensagem: string;
};

/**
 * Base da API para o browser.
 *
 * Em HTTPS (ex.: túnel Cloudflare só na :3000) usa o mesmo origin da página.
 * O Next faz rewrite de `/api/v1` e `/socket.io` para o Flask interno — evita
 * Mixed Content e a porta :5000 fora do túnel.
 *
 * Em HTTP local (:3000) ainda aponta para :5000, salvo override explícito.
 */
export function resolveApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_API_URL || "";
  }

  const pageOrigin = window.location.origin;
  const pageHost = window.location.hostname;
  const pageIsSecure = window.location.protocol === "https:";
  const pageIsLoopback = pageHost === "localhost" || pageHost === "127.0.0.1";

  // Túnel / produção HTTPS: same-origin (rewrite do Next → API).
  if (pageIsSecure) {
    return pageOrigin;
  }

  const env = process.env.NEXT_PUBLIC_API_URL;
  if (env) {
    try {
      const u = new URL(env);
      const envIsLoopback = u.hostname === "localhost" || u.hostname === "127.0.0.1";
      // Env com localhost, página em outro host HTTP (LAN): same-origin via rewrite.
      if (envIsLoopback && !pageIsLoopback) {
        return pageOrigin;
      }
      return u.origin;
    } catch {
      /* fallthrough */
    }
  }

  // Dev: Next em :3000 → Flask em :5000 no mesmo host.
  if (window.location.port === "3000") {
    const port = process.env.NEXT_PUBLIC_API_PORT || "5000";
    return `${window.location.protocol}//${pageHost}:${port}`;
  }

  return pageOrigin;
}

/** Socket.IO apontando para a API alcançável a partir do dispositivo do cliente. */
export function connectTicketSocket(token: string): Socket {
  const base = resolveApiBaseUrl();
  return io(base || "/", {
    path: "/socket.io",
    transports: ["websocket", "polling"],
    auth: { ticket_token: token },
    autoConnect: true,
    reconnection: true,
    reconnectionAttempts: 8,
  });
}
