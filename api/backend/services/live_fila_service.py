"""Snapshot operacional da fila (estilo BixFila /dash) para o admin Next."""
from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean
from typing import Any, Optional

from backend.extensions import db
from backend.models import AtendimentoAtual, Finalizado, Operador, Senha, Setor
from backend.services.fila_service import serializar_fila
from backend.utils import get_configuracao


def _media_minutos(pares: list[tuple[datetime, datetime]]) -> Optional[float]:
    vals = []
    for inicio, fim in pares:
        if not inicio or not fim:
            continue
        delta = (fim - inicio).total_seconds() / 60.0
        if delta >= 0:
            vals.append(delta)
    if not vals:
        return None
    return round(mean(vals), 2)


def _contagens_tipo(senhas: list[Senha]) -> dict[str, int]:
    normal = sum(1 for s in senhas if (s.tipo or "").lower() == "normal")
    preferencial = sum(1 for s in senhas if (s.tipo or "").lower() == "preferencial")
    return {"normal": normal, "preferencial": preferencial, "total": len(senhas)}


def _kpis_janela(
    setor_id: int,
    inicio: datetime,
    fim: datetime,
    *,
    ignorar_auto: bool,
    abandono_minutos: int,
) -> dict[str, Any]:
    emitidas_q = Senha.query.filter(
        Senha.setor_id == setor_id,
        Senha.data_hora >= inicio,
        Senha.data_hora < fim,
    )
    emitidas = emitidas_q.all()
    solicitacoes = len(emitidas)

    fin_q = (
        db.session.query(Finalizado, Senha)
        .join(Senha, Senha.id == Finalizado.senha_id)
        .filter(
            Finalizado.setor_id == setor_id,
            Finalizado.data_hora >= inicio,
            Finalizado.data_hora < fim,
        )
    )
    fins = fin_q.all()
    if ignorar_auto:
        fins = [(f, s) for f, s in fins if f.avaliacao not in (None, "")]

    atendimentos = len(fins)

    esperas = []
    atend_durs = []
    totais = []
    for _f, senha in fins:
        if senha.data_hora and senha.chamada_em:
            esperas.append((senha.data_hora, senha.chamada_em))
        if senha.chamada_em and senha.finalizado_em:
            atend_durs.append((senha.chamada_em, senha.finalizado_em))
        if senha.data_hora and senha.finalizado_em:
            totais.append((senha.data_hora, senha.finalizado_em))
        elif senha.data_hora and _f.data_hora:
            totais.append((senha.data_hora, _f.data_hora))

    limite = fim - timedelta(minutes=abandono_minutos)
    desistencias = sum(
        1
        for s in emitidas
        if s.status == "A" and s.chamada_em is None and s.data_hora and s.data_hora < limite
    )
    taxa = round(100.0 * desistencias / solicitacoes, 1) if solicitacoes else None

    return {
        "solicitacoes": solicitacoes,
        "atendimentos": atendimentos,
        "desistencias": desistencias,
        "taxa_desistencia": taxa,
        "tempo_espera_medio": _media_minutos(esperas),
        "tempo_atendimento_medio": _media_minutos(atend_durs),
        "tempo_total_medio": _media_minutos(totais),
        "por_tipo_solicitacoes": _contagens_tipo(emitidas),
    }


def montar_fila_ao_vivo(setor_id: int) -> dict[str, Any]:
    setor = Setor.query.get(setor_id)
    if not setor:
        raise ValueError("Setor não encontrado")

    agora = datetime.now()
    inicio_hora = agora - timedelta(hours=1)
    inicio_dia = datetime(agora.year, agora.month, agora.day)
    abandono_minutos = int(get_configuracao("abandono_minutos") or 30)
    ignorar_auto = (get_configuracao("ignorar_finalizados_automaticos") or "0") in (
        "1",
        "true",
        "True",
        "yes",
    )

    fila = serializar_fila(setor_id, incluir_pedidos=False)
    pendentes = Senha.query.filter_by(setor_id=setor_id, status="A").all()
    em_atendimento = Senha.query.filter_by(setor_id=setor_id, status="C").all()

    # Operadores com atendimento vivo (status C)
    rows = (
        db.session.query(AtendimentoAtual, Operador, Senha)
        .join(Operador, AtendimentoAtual.operador_id == Operador.id)
        .join(Senha, AtendimentoAtual.senha_id == Senha.id)
        .filter(AtendimentoAtual.setor_id == setor_id, Senha.status == "C")
        .order_by(AtendimentoAtual.id.desc())
        .all()
    )
    visto: set[int] = set()
    operadores_atendendo = []
    for atendimento, operador, senha in rows:
        if operador.id in visto:
            continue
        visto.add(operador.id)
        operadores_atendendo.append(
            {
                "operador_id": operador.id,
                "operador_nome": operador.nome,
                "operador_foto": operador.foto_perfil,
                "senha": senha.senha,
                "tipo": senha.tipo,
                "desde": atendimento.data_hora.isoformat() if atendimento.data_hora else None,
            }
        )

    espera_n = _contagens_tipo(pendentes)
    atend_n = _contagens_tipo(em_atendimento)
    total_agora = max(espera_n["total"] + atend_n["total"], 1)

    return {
        "setor": {"id": setor.id, "nome": setor.nome},
        "agora": {
            "espera": {
                "normal": espera_n["normal"],
                "preferencial": espera_n["preferencial"],
                "total": espera_n["total"],
                "pct_normal": round(100.0 * espera_n["normal"] / total_agora, 1),
                "pct_preferencial": round(100.0 * espera_n["preferencial"] / total_agora, 1),
            },
            "em_atendimento": {
                "normal": atend_n["normal"],
                "preferencial": atend_n["preferencial"],
                "total": atend_n["total"],
                "pct_normal": round(100.0 * atend_n["normal"] / total_agora, 1),
                "pct_preferencial": round(100.0 * atend_n["preferencial"] / total_agora, 1),
            },
        },
        "operadores_atendendo": operadores_atendendo,
        "operadores_em_pausa": [],  # status pausa ainda não modelado
        "ultima_hora": _kpis_janela(
            setor_id, inicio_hora, agora, ignorar_auto=ignorar_auto, abandono_minutos=abandono_minutos
        ),
        "hoje": _kpis_janela(
            setor_id, inicio_dia, agora, ignorar_auto=ignorar_auto, abandono_minutos=abandono_minutos
        ),
        "fila": fila,
        "config": {
            "ignorar_finalizados_automaticos": ignorar_auto,
            "abandono_minutos": abandono_minutos,
        },
        "atualizado_em": agora.isoformat(),
    }
