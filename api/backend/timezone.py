"""Relógio oficial do CompuFlow: sempre América/São Paulo.

Datas gravadas no banco são naive, mas representam horário de São Paulo
(não UTC). Toda regra de “hoje” / virada do dia deve passar por aqui.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

FUSO_SP = ZoneInfo("America/Sao_Paulo")


def agora_sp() -> datetime:
    """Agora em São Paulo, sem tzinfo, pronto para persistir no banco."""
    return datetime.now(FUSO_SP).replace(tzinfo=None)


def inicio_fim_dia_sp(agora: datetime | None = None) -> tuple[datetime, datetime]:
    """Intervalo [00:00, 00:00 do dia seguinte) no fuso de São Paulo."""
    atual = agora or agora_sp()
    if atual.tzinfo is not None:
        atual = atual.astimezone(FUSO_SP).replace(tzinfo=None)
    inicio = atual.replace(hour=0, minute=0, second=0, microsecond=0)
    return inicio, inicio + timedelta(days=1)


def segundos_ate_proxima_meia_noite(agora: datetime | None = None) -> float:
    atual = agora or agora_sp()
    _, fim = inicio_fim_dia_sp(atual)
    return max(1.0, (fim - atual).total_seconds())
