import { resolveApiBaseUrl } from "@/lib/cliente-socket";

const TV_TOKEN_KEY = "compuflow_tv_session";

export type TvSetor = {
  id: number;
  nome: string;
  descricao?: string | null;
  propagandas_ativas?: boolean;
};

export type TvSenha = {
  id: number;
  senha: string;
  tipo: string;
  setor_id?: number;
  status?: string;
};

export type TvAtendimento = {
  operador_id: number;
  operador_nome: string;
  operador_foto?: string | null;
  senha: string;
  tipo: string;
  senha_id?: number | null;
};

export type TvFila = {
  setor_id: number;
  pendentes: TvSenha[];
  atendimentos: TvAtendimento[];
};

export type TvPropagandaImagem = {
  id: number;
  arquivo: string;
  ordem?: number;
  tipo?: "image" | "video";
};

export type TvConfig = {
  propagandas_ativas: boolean;
  layout_tv_web: "propaganda" | "fila";
  setor_nome?: string | null;
  imagens: TvPropagandaImagem[];
  intervalo_ms: number;
};

export type TvRecentCall = {
  senha_id: number;
  senha: string;
  tipo: string;
  operador_id?: number | null;
  operador_nome?: string | null;
  operador_foto?: string | null;
  chamada_em?: string | null;
  status: "atual" | "finalizada";
};

export type TvRecentCallsResponse = {
  chamadas: TvRecentCall[];
};

export function getStoredTvToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TV_TOKEN_KEY);
}

export function storeTvToken(token: string) {
  localStorage.setItem(TV_TOKEN_KEY, token);
}

export function clearTvToken() {
  localStorage.removeItem(TV_TOKEN_KEY);
}

export function uploadsUrl(path: string | null | undefined): string | null {
  const value = path?.trim();
  if (!value) return null;
  if (value.startsWith("http://") || value.startsWith("https://")) return value;
  const normalized = value.replace(/^\//, "").replace(/^uploads\//, "");
  // Prefer same-origin (HTTPS / túnel) — rewrite `/uploads` no Next.
  if (typeof window !== "undefined" && window.location.protocol === "https:") {
    return `${window.location.origin}/uploads/${normalized}`;
  }
  const base = resolveApiBaseUrl().replace(/\/$/, "");
  return `${base}/uploads/${normalized}`;
}

export async function tvApiFetch<T>(
  path: string,
  init: RequestInit & { token?: string | null } = {},
): Promise<T> {
  const { token, ...rest } = init;
  const headers = new Headers(rest.headers);
  if (rest.body && !(rest.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const base = resolveApiBaseUrl().replace(/\/$/, "");
  const url = path.startsWith("http") ? path : `${base}${path.startsWith("/") ? "" : "/"}${path}`;

  const res = await fetch(url, { ...rest, headers });
  if (!res.ok) {
    let message = `Erro ${res.status}`;
    try {
      const data = await res.json();
      if (data?.error) message = data.error;
    } catch {
      /* ignore */
    }
    const err = new Error(message) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function loginTv(codigoSetor: string): Promise<{ token: string; setor: TvSetor }> {
  const login = await tvApiFetch<{ session_token: string; setor: TvSetor }>("/api/v1/setor/login", {
    method: "POST",
    body: JSON.stringify({ codigo_setor: codigoSetor.trim() }),
  });
  const papel = await tvApiFetch<{ session_token: string }>("/api/v1/sessao/papel", {
    method: "POST",
    token: login.session_token,
    body: JSON.stringify({ role: "tv" }),
  });
  storeTvToken(papel.session_token);
  return { token: papel.session_token, setor: login.setor };
}
