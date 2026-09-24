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

export type PapelPainel = "admin" | "gerente" | "marketing";

export function rotuloPapel(papel: PapelPainel | string): string {
  if (papel === "admin") return "Administrador";
  if (papel === "marketing") return "Marketing";
  if (papel === "gerente") return "Gerente";
  return papel;
}

export function homeDoPapel(papel: PapelPainel | string): string {
  return papel === "marketing" ? "/admin/propagandas" : "/admin";
}

export function rotaAdminPermitida(papel: PapelPainel | string, pathname: string): boolean {
  if (papel !== "marketing") return true;
  return pathname === "/admin/propagandas" || pathname.startsWith("/admin/propagandas/");
}

export type AdminUser = {
  id: number;
  email: string;
  nome?: string;
  nome_empresa: string;
  papel: PapelPainel;
  is_admin?: boolean;
  is_marketing?: boolean;
  setor_ids?: number[];
  setores?: { id: number; nome: string }[];
};

export type PainelUsuario = {
  id: number;
  email: string;
  nome: string;
  papel: PapelPainel;
  setor_ids: number[];
  setores: { id: number; nome: string }[];
  criado_em: string | null;
};

export type Setor = {
  id: number;
  nome: string;
  descricao: string;
  senha_setor: string;
  tipo_setor?: "atendimento" | "streaming";
  modo_identificacao_operador: "foto" | "pin";
  propagandas_ativas: boolean;
  propagandas_cliente_ativas?: boolean;
  impressao_via_cliente?: boolean;
  propaganda_ids_cliente?: number[];
  layout_tv_web: "propaganda" | "fila";
  orientacao_tv: "horizontal" | "vertical";
};

export function setorEhAtendimento(setor: { tipo_setor?: string | null }): boolean {
  return (setor.tipo_setor || "atendimento") !== "streaming";
}

export function setorEhStreaming(setor: { tipo_setor?: string | null }): boolean {
  return (setor.tipo_setor || "atendimento") === "streaming";
}

export type PropagandaTipo = "image" | "video";

export type Propaganda = {
  id: number;
  arquivo: string;
  tipo: PropagandaTipo;
  ordem: number;
  ativo: boolean;
  criado_em: string | null;
  setor_ids: number[];
  setor_ids_cliente?: number[];
};

export type TvAdmin = {
  id: number;
  tipo: "setor" | "streaming";
  chave: string;
  nome: string;
  device_name?: string;
  is_online: boolean;
  setor_id?: number | null;
  setor_nome?: string | null;
  tipo_setor?: "atendimento" | "streaming" | null;
  propaganda_ids: number[];
  layout_tv_web?: "propaganda" | "fila";
  orientacao_tv?: "horizontal" | "vertical";
};

export type Operador = {
  id: number;
  nome: string;
  setor_id: number | null;
  setor_nome: string | null;
  foto_perfil: string | null;
  tem_pin: boolean;
  nota_media?: number | null;
  n_avaliacoes?: number;
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
    qr_escaneados: number;
    pedidos_adiantados: number;
  };
  por_setor: {
    setor_id: number;
    setor: string;
    emitidas: number;
    chamadas: number;
    finalizadas: number;
    atendimentos: number;
    nao_chamadas: number;
    qr_escaneados: number;
    pedidos_adiantados: number;
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
  fluxo_por_setor: {
    granularidade: "hora" | "dia";
    setores: { id: number; nome: string; chave: string }[];
    series: Array<{ t: string; label: string } & Record<string, string | number>>;
  };
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
    n_avaliacoes: number;
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

export type FilaAoVivoKpis = {
  solicitacoes: number;
  atendimentos: number;
  desistencias: number;
  taxa_desistencia: number | null;
  tempo_espera_medio: number | null;
  tempo_atendimento_medio: number | null;
  tempo_total_medio: number | null;
  por_tipo_solicitacoes: { normal: number; preferencial: number; total: number };
};

export type FilaAoVivoData = {
  setor: { id: number; nome: string };
  agora: {
    espera: {
      normal: number;
      preferencial: number;
      total: number;
      pct_normal: number;
      pct_preferencial: number;
    };
    em_atendimento: {
      normal: number;
      preferencial: number;
      total: number;
      pct_normal: number;
      pct_preferencial: number;
    };
  };
  operadores_atendendo: {
    operador_id: number;
    operador_nome: string;
    operador_foto: string | null;
    senha: string;
    tipo: string;
    desde: string | null;
  }[];
  operadores_em_pausa: unknown[];
  ultima_hora: FilaAoVivoKpis;
  hoje: FilaAoVivoKpis;
  fila: {
    setor_id: number;
    pendentes: { id: number; senha: string; tipo: string; status: string }[];
    atendimentos: {
      operador_id: number;
      operador_nome: string;
      senha: string;
      tipo: string;
      senha_id: number;
    }[];
  };
  config: {
    ignorar_finalizados_automaticos: boolean;
    abandono_minutos: number;
  };
  atualizado_em: string;
};
