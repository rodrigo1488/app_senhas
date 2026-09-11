/** Cliente HTTP do painel: chama rotas relativas (proxy Next → Flask). */
export async function apiFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(path, {
    ...init,
    headers,
    credentials: "include",
  });

  if (!res.ok) {
    let message = `Erro ${res.status}`;
    try {
      const data = await res.json();
      if (data?.error) message = data.error;
    } catch {
      /* ignore */
    }
    throw new Error(message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export type AdminUser = {
  id: number;
  email: string;
  nome_empresa: string;
};

export type Setor = {
  id: number;
  nome: string;
  descricao: string;
  senha_setor: string;
};

export type Operador = {
  id: number;
  nome: string;
  setor_id: number | null;
  setor_nome: string | null;
  foto_perfil: string | null;
};

export type Impressora = {
  id: number;
  nome: string;
  ip: string;
  porta: number;
  setor_id: number | null;
  setor_nome: string | null;
};

export type DashboardData = {
  atendimentos_dia: { setor: string; total: number }[];
  atendimentos_mes: { setor: string; total: number }[];
  medias_operadores: { operador: string; media: number | null; setor: string | null }[];
  melhor_operador: { operador: string; media: number | null; setor: string | null } | null;
  pior_operador: { operador: string; media: number | null; setor: string | null } | null;
  medias_por_setor: Record<string, { operador: string; media: number | null }[]>;
  atendimentos_mes_operador_por_setor: Record<string, { operador: string; total: number }[]>;
  setores: { id: number; nome: string }[];
  proporcao_normais: string;
  limite_preferenciais_alerta: string;
  ngrok_url: string;
  nome_empresa: string;
};
