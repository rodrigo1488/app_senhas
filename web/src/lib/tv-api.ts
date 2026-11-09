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
  atendimento_id?: number | null;
  chamada_em?: string | null;
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

export type TvOrientacao = "horizontal" | "vertical";

export type TvPosicaoSenhas = "superior" | "inferior";

export type TvConfig = {
  propagandas_ativas: boolean;
  layout_tv_web: "propaganda" | "fila";
  orientacao_tv?: TvOrientacao;
  posicao_senhas_tv?: TvPosicaoSenhas;
  setor_nome?: string | null;
  imagens: TvPropagandaImagem[];
  intervalo_ms: number;
  som_chamada?: string | null;
};

export type TvRecentCall = {
  senha_id: number;
  senha: string;
  tipo: string;
  operador_id?: number | null;
  operador_nome?: string | null;
  operador_foto?: string | null;
  chamada_em?: string | null;
  atendimento_id?: number | null;
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

const TV_DEVICE_KEY = "compuflow_tv_device_id";

export function getOrCreateTvDeviceId(): string {
  const existing = localStorage.getItem(TV_DEVICE_KEY);
  if (existing) return existing;
  const created = crypto.randomUUID();
  localStorage.setItem(TV_DEVICE_KEY, created);
  return created;
}

function ipv4NoCandidato(valor: string): string | null {
  const match = valor.match(/\b(\d{1,3}(?:\.\d{1,3}){3})\b/);
  const ip = match?.[1];
  if (!ip || ip === "0.0.0.0" || ip.startsWith("127.")) return null;
  const partes = ip.split(".").map((parte) => Number(parte));
  if (partes.some((parte) => parte > 255)) return null;
  return ip;
}

/** Melhor esforço: alguns navegadores escondem o IP local. O servidor usa o IP da conexão. */
export function descobrirIpv4Local(): Promise<string | null> {
  if (typeof window === "undefined" || typeof RTCPeerConnection === "undefined") {
    return Promise.resolve(null);
  }
  return new Promise((resolve) => {
    let encerrado = false;
    let timer = 0;
    const pc = new RTCPeerConnection({ iceServers: [] });
    const concluir = (ip: string | null) => {
      if (encerrado) return;
      encerrado = true;
      window.clearTimeout(timer);
      try {
        pc.close();
      } catch {
        /* ignore */
      }
      resolve(ip);
    };
    timer = window.setTimeout(() => concluir(null), 800);
    try {
      pc.createDataChannel("ip");
      pc.onicecandidate = (event) => {
        const ip = ipv4NoCandidato(event.candidate?.candidate || "");
        if (ip) concluir(ip);
      };
      void pc
        .createOffer()
        .then((offer) => pc.setLocalDescription(offer))
        .catch(() => concluir(null));
    } catch {
      concluir(null);
    }
  });
}

export async function reportarPresencaTv(token: string) {
  const ip = await descobrirIpv4Local();
  await tvApiFetch("/api/v1/equipamento/presenca", {
    method: "POST",
    token,
    body: JSON.stringify({
      device_id: getOrCreateTvDeviceId(),
      papel: "tv",
      ip,
      nome: "Navegador",
    }),
  });
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
