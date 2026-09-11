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
  modo_identificacao_operador: "foto" | "pin";
  propagandas_ativas: boolean;
};

export type Propaganda = {
  id: number;
  arquivo: string;
  ordem: number;
  ativo: boolean;
  criado_em: string | null;
};

export type Operador = {
  id: number;
  nome: string;
  setor_id: number | null;
  setor_nome: string | null;
  foto_perfil: string | null;
  tem_pin: boolean;
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

export type EsperaStats = {
  media: number | null;
  mediana: number | null;
  p90: number | null;
  p95: number | null;
  max: number | null;
  amostras: number;
};

export type AnalyticsData = {
  periodo: {
    from: string;
    to: string;
    setor_id: number | null;
    operador_id: number | null;
  };
  meta_espera_minutos: number;
  kpis: {
    emitidas: number;
    chamadas: number;
    finalizadas: number;
    atendimentos: number;
    espera: EsperaStats;
    nota_media: number | null;
    pct_avaliacoes: number | null;
    nao_chamadas: number;
    abandono: number;
    abandono_minutos: number;
    taxa_abandono: number | null;
  };
  por_setor: {
    setor_id: number;
    setor: string;
    emitidas: number;
    chamadas: number;
    finalizadas: number;
    atendimentos: number;
    nao_chamadas: number;
    espera: EsperaStats;
    nota_media: number | null;
  }[];
  por_hora: {
    hora: number;
    label: string;
    retiradas: number;
    chamadas: number;
    espera_media: number | null;
    nota_media: number | null;
  }[];
  heatmap: {
    setores: { id: number; nome: string }[];
    celulas: {
      setor_id: number;
      setor: string;
      hora: number;
      volume: number;
      espera_media: number | null;
      carga: number;
    }[];
  };
  atendentes: {
    operador_id: number;
    operador: string;
    setor_id: number | null;
    setor: string | null;
    atendimentos: number;
    espera: EsperaStats;
    tempo_atendimento_medio: number | null;
    nota_media: number | null;
  }[];
  distribuicao_notas: { nota: string; total: number; pct: number }[];
  espera_x_satisfacao: { faixa: string; nota_media: number | null; amostras: number }[];
  alertas: {
    tipo: string;
    severidade: string;
    mensagem: string;
    valor?: number;
    valor_anterior?: number;
    setor_id?: number;
  }[];
  filtros: {
    setores: { id: number; nome: string }[];
    operadores: { id: number; nome: string; setor_id: number | null }[];
  };
};
