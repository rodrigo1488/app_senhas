"""Métricas analíticas do painel admin (espera, KPIs, heatmap, alertas)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, median
from typing import Any, Optional

from sqlalchemy import and_

from backend.extensions import db
from backend.models import Finalizado, Operador, Senha, Setor
from backend.utils import get_configuracao


DEFAULT_ABANDONO_MINUTOS = 30
DEFAULT_META_ESPERA_MIN = 10.0


def _parse_dt(value: Optional[str], *, end_of_day: bool = False) -> datetime:
    if not value:
        hoje = date.today()
        if end_of_day:
            return datetime(hoje.year, hoje.month, hoje.day) + timedelta(days=1)
        return datetime(hoje.year, hoje.month, hoje.day)
    raw = value.strip()
    if "T" in raw:
        dt = datetime.fromisoformat(raw.replace("Z", ""))
    else:
        d = date.fromisoformat(raw[:10])
        dt = datetime(d.year, d.month, d.day)
    if end_of_day and len(raw) <= 10:
        dt = dt + timedelta(days=1)
    return dt


def _percentile(sorted_vals: list[float], p: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


def _espera_stats(esperas_min: list[float]) -> dict[str, Optional[float]]:
    if not esperas_min:
        return {
            "media": None,
            "mediana": None,
            "p90": None,
            "p95": None,
            "max": None,
            "amostras": 0,
        }
    ordered = sorted(esperas_min)
    return {
        "media": round(mean(ordered), 2),
        "mediana": round(median(ordered), 2),
        "p90": round(_percentile(ordered, 90) or 0, 2),
        "p95": round(_percentile(ordered, 95) or 0, 2),
        "max": round(ordered[-1], 2),
        "amostras": len(ordered),
    }


def _espera_minutos(senha: Senha) -> Optional[float]:
    if not senha.data_hora or not senha.chamada_em:
        return None
    delta = (senha.chamada_em - senha.data_hora).total_seconds() / 60.0
    return max(0.0, delta)


def _parse_nota(avaliacao: Optional[str]) -> Optional[float]:
    if avaliacao is None or str(avaliacao).strip() == "":
        return None
    try:
        return float(avaliacao)
    except (TypeError, ValueError):
        return None


def _faixa_espera(minutos: float) -> str:
    if minutos < 5:
        return "0-5"
    if minutos < 10:
        return "5-10"
    if minutos < 15:
        return "10-15"
    if minutos < 20:
        return "15-20"
    return ">20"


def montar_analytics(
    *,
    from_s: Optional[str] = None,
    to_s: Optional[str] = None,
    setor_id: Optional[int] = None,
    setor_ids: Optional[list[int]] = None,
    operador_id: Optional[int] = None,
    abandono_minutos: Optional[int] = None,
) -> dict[str, Any]:
    inicio = _parse_dt(from_s, end_of_day=False)
    fim = _parse_dt(to_s, end_of_day=True)
    agora = datetime.now()

    if abandono_minutos is None:
        abandono_minutos = int(
            get_configuracao("abandono_minutos") or DEFAULT_ABANDONO_MINUTOS
        )
    meta_espera = float(get_configuracao("meta_espera_minutos") or DEFAULT_META_ESPERA_MIN)

    escopo_ids = list(setor_ids) if setor_ids is not None else None
    if escopo_ids is not None and setor_id is not None and setor_id not in escopo_ids:
        escopo_ids = []
    elif escopo_ids is not None and setor_id is not None:
        escopo_ids = [setor_id]
    elif setor_id is not None:
        escopo_ids = [setor_id]

    q = Senha.query.filter(Senha.data_hora >= inicio, Senha.data_hora < fim)
    if escopo_ids is not None:
        if not escopo_ids:
            q = q.filter(False)
        else:
            q = q.filter(Senha.setor_id.in_(escopo_ids))

    senha_ids_operador: Optional[set[int]] = None
    if operador_id:
        rows_f = (
            db.session.query(Finalizado.senha_id)
            .filter(Finalizado.operador_id == operador_id)
            .all()
        )
        senha_ids_operador = {r[0] for r in rows_f}
        if not senha_ids_operador:
            senhas: list[Senha] = []
        else:
            q = q.filter(Senha.id.in_(senha_ids_operador))
            senhas = q.all()
    else:
        senhas = q.all()

    setores_q = Setor.query.order_by(Setor.nome)
    operadores_q = Operador.query.order_by(Operador.nome)
    if escopo_ids is not None:
        if not escopo_ids:
            setores_q = setores_q.filter(False)
            operadores_q = operadores_q.filter(False)
        else:
            setores_q = setores_q.filter(Setor.id.in_(escopo_ids))
            operadores_q = operadores_q.filter(Operador.setor_id.in_(escopo_ids))
    setores = {s.id: s for s in setores_q.all()}
    operadores = {o.id: o for o in Operador.query.all()}
    if escopo_ids is not None:
        operadores = {oid: o for oid, o in operadores.items() if o.setor_id in escopo_ids}

    # Finalizados no período (por data do finalizado ou da senha emitida)
    fq = (
        db.session.query(Finalizado, Senha)
        .join(Senha, Senha.id == Finalizado.senha_id)
        .filter(Senha.data_hora >= inicio, Senha.data_hora < fim)
    )
    if escopo_ids is not None:
        if not escopo_ids:
            fq = fq.filter(False)
        else:
            fq = fq.filter(Senha.setor_id.in_(escopo_ids))
    if operador_id:
        fq = fq.filter(Finalizado.operador_id == operador_id)
    finalizados_rows = fq.all()

    emitidas = len(senhas)
    chamadas = sum(1 for s in senhas if s.chamada_em is not None or s.status in ("C", "F"))
    finalizadas = sum(1 for s in senhas if s.status == "F" or s.finalizado_em is not None)

    # Não chamadas / abandono operacional
    limite_abandono = agora - timedelta(minutes=abandono_minutos)
    nao_chamadas = [
        s
        for s in senhas
        if s.status == "A" and s.chamada_em is None and (s.data_hora is None or s.data_hora < limite_abandono)
    ]
    # Também conta emitidas no período ainda em A (KPI "não chamadas" do período)
    ainda_aguardando = [s for s in senhas if s.status == "A" and s.chamada_em is None]
    abandono_count = len(nao_chamadas)

    esperas = []
    for s in senhas:
        em = _espera_minutos(s)
        if em is not None:
            esperas.append(em)
    espera = _espera_stats(esperas)

    notas = []
    for fin, _senha in finalizados_rows:
        n = _parse_nota(fin.avaliacao)
        if n is not None:
            notas.append(n)
    atendimentos = len(finalizados_rows)
    nota_media = round(mean(notas), 2) if notas else None
    pct_avaliacoes = round(100.0 * len(notas) / atendimentos, 1) if atendimentos else None

    kpis = {
        "emitidas": emitidas,
        "chamadas": chamadas,
        "finalizadas": finalizadas,
        "atendimentos": atendimentos,
        "espera": espera,
        "nota_media": nota_media,
        "pct_avaliacoes": pct_avaliacoes,
        "nao_chamadas": len(ainda_aguardando),
        "abandono": abandono_count,
        "abandono_minutos": abandono_minutos,
        "taxa_abandono": round(100.0 * abandono_count / emitidas, 1) if emitidas else None,
    }

    # Por setor
    por_setor_map: dict[int, dict[str, Any]] = {}
    for s in senhas:
        sid = s.setor_id or 0
        bucket = por_setor_map.setdefault(
            sid,
            {
                "setor_id": sid,
                "setor": setores[sid].nome if sid in setores else "—",
                "emitidas": 0,
                "chamadas": 0,
                "finalizadas": 0,
                "esperas": [],
                "notas": [],
                "atendimentos": 0,
                "nao_chamadas": 0,
            },
        )
        bucket["emitidas"] += 1
        if s.chamada_em is not None or s.status in ("C", "F"):
            bucket["chamadas"] += 1
        if s.status == "F" or s.finalizado_em is not None:
            bucket["finalizadas"] += 1
        if s.status == "A" and s.chamada_em is None:
            bucket["nao_chamadas"] += 1
        em = _espera_minutos(s)
        if em is not None:
            bucket["esperas"].append(em)

    for fin, senha in finalizados_rows:
        sid = fin.setor_id or senha.setor_id or 0
        bucket = por_setor_map.setdefault(
            sid,
            {
                "setor_id": sid,
                "setor": setores[sid].nome if sid in setores else "—",
                "emitidas": 0,
                "chamadas": 0,
                "finalizadas": 0,
                "esperas": [],
                "notas": [],
                "atendimentos": 0,
                "nao_chamadas": 0,
            },
        )
        bucket["atendimentos"] += 1
        n = _parse_nota(fin.avaliacao)
        if n is not None:
            bucket["notas"].append(n)

    por_setor = []
    for sid, b in sorted(por_setor_map.items(), key=lambda x: x[1]["setor"]):
        por_setor.append(
            {
                "setor_id": b["setor_id"],
                "setor": b["setor"],
                "emitidas": b["emitidas"],
                "chamadas": b["chamadas"],
                "finalizadas": b["finalizadas"],
                "atendimentos": b["atendimentos"],
                "nao_chamadas": b["nao_chamadas"],
                "espera": _espera_stats(b["esperas"]),
                "nota_media": round(mean(b["notas"]), 2) if b["notas"] else None,
            }
        )

    # Por hora (0–23)
    por_hora_map: dict[int, dict[str, Any]] = {
        h: {"hora": h, "retiradas": 0, "chamadas": 0, "esperas": [], "notas": []}
        for h in range(24)
    }
    for s in senhas:
        if not s.data_hora:
            continue
        h = s.data_hora.hour
        por_hora_map[h]["retiradas"] += 1
        if s.chamada_em is not None:
            por_hora_map[h]["chamadas"] += 1
            em = _espera_minutos(s)
            if em is not None:
                por_hora_map[h]["esperas"].append(em)
    for fin, senha in finalizados_rows:
        ref = senha.data_hora or fin.data_hora
        if not ref:
            continue
        n = _parse_nota(fin.avaliacao)
        if n is not None:
            por_hora_map[ref.hour]["notas"].append(n)

    por_hora = []
    for h in range(24):
        b = por_hora_map[h]
        por_hora.append(
            {
                "hora": h,
                "label": f"{h:02d}h",
                "retiradas": b["retiradas"],
                "chamadas": b["chamadas"],
                "espera_media": round(mean(b["esperas"]), 2) if b["esperas"] else None,
                "nota_media": round(mean(b["notas"]), 2) if b["notas"] else None,
            }
        )

    # Heatmap setor × hora (carga = volume + espera média normalizada)
    heatmap_raw: dict[tuple[int, int], dict[str, Any]] = defaultdict(
        lambda: {"volume": 0, "esperas": []}
    )
    for s in senhas:
        if not s.data_hora:
            continue
        key = (s.setor_id or 0, s.data_hora.hour)
        heatmap_raw[key]["volume"] += 1
        em = _espera_minutos(s)
        if em is not None:
            heatmap_raw[key]["esperas"].append(em)

    max_vol = max((v["volume"] for v in heatmap_raw.values()), default=1) or 1
    max_esp = max(
        (mean(v["esperas"]) for v in heatmap_raw.values() if v["esperas"]),
        default=1.0,
    ) or 1.0

    heatmap_cells = []
    setor_ids_hm = sorted({s.setor_id or 0 for s in senhas}) or list(setores.keys())
    for sid in setor_ids_hm:
        for h in range(24):
            cell = heatmap_raw.get((sid, h), {"volume": 0, "esperas": []})
            vol = cell["volume"]
            esp = mean(cell["esperas"]) if cell["esperas"] else 0.0
            # Carga 0–1: 60% volume + 40% espera
            carga = 0.6 * (vol / max_vol) + 0.4 * (esp / max_esp if max_esp else 0)
            heatmap_cells.append(
                {
                    "setor_id": sid,
                    "setor": setores[sid].nome if sid in setores else "—",
                    "hora": h,
                    "volume": vol,
                    "espera_media": round(esp, 2) if cell["esperas"] else None,
                    "carga": round(carga, 3),
                }
            )

    # Atendentes
    atendentes_map: dict[int, dict[str, Any]] = {}
    for fin, senha in finalizados_rows:
        oid = fin.operador_id
        b = atendentes_map.setdefault(
            oid,
            {
                "operador_id": oid,
                "operador": operadores[oid].nome if oid in operadores else "—",
                "setor_id": fin.setor_id,
                "setor": setores[fin.setor_id].nome if fin.setor_id in setores else None,
                "atendimentos": 0,
                "esperas": [],
                "atendimento_min": [],
                "notas": [],
            },
        )
        b["atendimentos"] += 1
        em = _espera_minutos(senha)
        if em is not None:
            b["esperas"].append(em)
        if senha.chamada_em and senha.finalizado_em:
            dur = (senha.finalizado_em - senha.chamada_em).total_seconds() / 60.0
            if dur >= 0:
                b["atendimento_min"].append(dur)
        n = _parse_nota(fin.avaliacao)
        if n is not None:
            b["notas"].append(n)

    atendentes = []
    for oid, b in sorted(atendentes_map.items(), key=lambda x: -x[1]["atendimentos"]):
        atendentes.append(
            {
                "operador_id": b["operador_id"],
                "operador": b["operador"],
                "setor_id": b["setor_id"],
                "setor": b["setor"],
                "atendimentos": b["atendimentos"],
                "espera": _espera_stats(b["esperas"]),
                "tempo_atendimento_medio": (
                    round(mean(b["atendimento_min"]), 2) if b["atendimento_min"] else None
                ),
                "nota_media": round(mean(b["notas"]), 2) if b["notas"] else None,
                "n_avaliacoes": len(b["notas"]),
            }
        )

    # Distribuição de notas (1–5 típico; aceita qualquer float arredondado)
    dist: dict[str, int] = defaultdict(int)
    for n in notas:
        key = str(int(round(n)))
        dist[key] += 1
    distribuicao_notas = [
        {"nota": k, "total": dist[k], "pct": round(100.0 * dist[k] / len(notas), 1) if notas else 0}
        for k in sorted(dist.keys(), key=lambda x: int(x))
    ]

    # Espera × satisfação
    faixa_order = ["0-5", "5-10", "10-15", "15-20", ">20"]
    faixa_map: dict[str, list[float]] = {f: [] for f in faixa_order}
    for fin, senha in finalizados_rows:
        em = _espera_minutos(senha)
        n = _parse_nota(fin.avaliacao)
        if em is None or n is None:
            continue
        faixa_map[_faixa_espera(em)].append(n)

    espera_x_satisfacao = [
        {
            "faixa": f,
            "nota_media": round(mean(faixa_map[f]), 2) if faixa_map[f] else None,
            "amostras": len(faixa_map[f]),
        }
        for f in faixa_order
    ]

    # Alertas
    alertas: list[dict[str, Any]] = []
    for row in por_setor:
        media = (row.get("espera") or {}).get("media")
        if media is not None and media > meta_espera:
            alertas.append(
                {
                    "tipo": "espera_acima_meta",
                    "severidade": "warning" if media < meta_espera * 1.5 else "critical",
                    "mensagem": (
                        f"{row['setor']}: espera média {media:.1f} min "
                        f"(meta {meta_espera:.0f} min)"
                    ),
                    "setor_id": row["setor_id"],
                    "valor": media,
                }
            )

    # Pico de fila A (agora, opcionalmente no setor filtrado)
    qa = Senha.query.filter(Senha.status == "A")
    if escopo_ids is not None:
        if not escopo_ids:
            qa = qa.filter(False)
        else:
            qa = qa.filter(Senha.setor_id.in_(escopo_ids))
    fila_a = qa.count()
    if fila_a >= 10:
        alertas.append(
            {
                "tipo": "pico_fila",
                "severidade": "warning" if fila_a < 20 else "critical",
                "mensagem": f"Fila atual com {fila_a} senhas aguardando",
                "valor": fila_a,
            }
        )

    # Queda de nota vs dia anterior
    ontem_ini = datetime(agora.year, agora.month, agora.day) - timedelta(days=1)
    ontem_fim = datetime(agora.year, agora.month, agora.day)
    hoje_ini = ontem_fim
    hoje_fim = hoje_ini + timedelta(days=1)

    def _media_notas_periodo(a: datetime, b: datetime) -> Optional[float]:
        qn = (
            db.session.query(Finalizado.avaliacao)
            .join(Senha, Senha.id == Finalizado.senha_id)
            .filter(Finalizado.data_hora >= a, Finalizado.data_hora < b)
            .filter(and_(Finalizado.avaliacao.isnot(None), Finalizado.avaliacao != ""))
        )
        if escopo_ids is not None:
            if not escopo_ids:
                qn = qn.filter(False)
            else:
                qn = qn.filter(Finalizado.setor_id.in_(escopo_ids))
        if operador_id:
            qn = qn.filter(Finalizado.operador_id == operador_id)
        vals = []
        for (av,) in qn.all():
            n = _parse_nota(av)
            if n is not None:
                vals.append(n)
        return round(mean(vals), 2) if vals else None

    media_hoje = _media_notas_periodo(hoje_ini, hoje_fim)
    media_ontem = _media_notas_periodo(ontem_ini, ontem_fim)
    if media_hoje is not None and media_ontem is not None and media_hoje < media_ontem - 0.3:
        alertas.append(
            {
                "tipo": "queda_nota",
                "severidade": "warning",
                "mensagem": (
                    f"Nota média caiu de {media_ontem:.1f} (ontem) "
                    f"para {media_hoje:.1f} (hoje)"
                ),
                "valor": media_hoje,
                "valor_anterior": media_ontem,
            }
        )

    return {
        "periodo": {
            "from": inicio.isoformat(),
            "to": (fim - timedelta(microseconds=1)).isoformat(),
            "setor_id": setor_id,
            "operador_id": operador_id,
        },
        "meta_espera_minutos": meta_espera,
        "kpis": kpis,
        "por_setor": por_setor,
        "por_hora": por_hora,
        "heatmap": {
            "setores": [
                {"id": sid, "nome": setores[sid].nome if sid in setores else "—"}
                for sid in setor_ids_hm
            ],
            "celulas": heatmap_cells,
        },
        "atendentes": atendentes,
        "distribuicao_notas": distribuicao_notas,
        "espera_x_satisfacao": espera_x_satisfacao,
        "alertas": alertas,
        "filtros": {
            "setores": [{"id": s.id, "nome": s.nome} for s in sorted(setores.values(), key=lambda x: x.nome or "")],
            "operadores": [
                {"id": o.id, "nome": o.nome, "setor_id": o.setor_id}
                for o in sorted(operadores.values(), key=lambda x: x.nome or "")
            ],
        },
    }
