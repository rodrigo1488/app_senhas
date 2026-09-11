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
 * `NEXT_PUBLIC_API_URL=http://localhost:5000` quebra no celular (localhost = o
 * próprio aparelho). Troca o host pelo da página quando necessário.
 */
export function resolveApiBaseUrl(): string {
  if (typeof window === "undefined") {
    return process.env.NEXT_PUBLIC_API_URL || "";
  }

  const pageHost = window.location.hostname;
  const env = process.env.NEXT_PUBLIC_API_URL;

  if (env) {
    try {
      const u = new URL(env);
      const envIsLoopback = u.hostname === "localhost" || u.hostname === "127.0.0.1";
      const pageIsLoopback = pageHost === "localhost" || pageHost === "127.0.0.1";
      if (envIsLoopback && !pageIsLoopback) {
        u.hostname = pageHost;
      }
      return u.origin;
    } catch {
      /* fallthrough */
    }
  }

  const protocol = window.location.protocol;
  // Página no Next (:3000) → API no mesmo host :5000
  if (window.location.port === "3000" || window.location.port === "") {
    const port = process.env.NEXT_PUBLIC_API_PORT || "5000";
    return `${protocol}//${pageHost}:${port}`;
  }
  return window.location.origin;
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
