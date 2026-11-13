"""Métricas analíticas do painel admin (espera, KPIs, heatmap, alertas)."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, median
from typing import Any, Optional

from sqlalchemy import and_, func, or_

from backend.extensions import db
from backend.models import Finalizado, Operador, QrScan, Senha, Setor, TIPO_SETOR_STREAMING, setor_eh_streaming
from backend.timezone import agora_sp
from backend.utils import get_configuracao


DEFAULT_ABANDONO_MINUTOS = 30
DEFAULT_META_ESPERA_MIN = 10.0
# Fallbacks da grade (sobrescritos pela config em alerta_notify_service).
HORA_INICIO_EXPEDIENTE = 7
HORA_FIM_EXPEDIENTE = 21
HORA_FIM_ALERTA = 20


def _config_monitoramento() -> dict[str, Any]:
    from backend.services.alerta_notify_service import ler_config_monitoramento

    return ler_config_monitoramento()


def _pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo gregoriano anônimo)."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def _eh_feriado_nacional(dia: date) -> bool:
    """Feriados nacionais fixos e móveis usados no comércio."""
    fixos = {
        (1, 1),
        (4, 21),
        (5, 1),
        (9, 7),
        (10, 12),
        (11, 2),
        (11, 15),
        (11, 20),
        (12, 25),
    }
    if (dia.month, dia.day) in fixos:
        return True
    pascoa = _pascoa(dia.year)
    moveis = {
        pascoa - timedelta(days=48),  # Carnaval (segunda)
        pascoa - timedelta(days=47),  # Carnaval (terça)
        pascoa - timedelta(days=2),  # Sexta-feira Santa
        pascoa + timedelta(days=60),  # Corpus Christi
    }
    return dia in moveis


def _faixa_expediente(
    dia: date,
    cfg: dict[str, Any] | None = None,
) -> tuple[int, int, int] | None:
    """Retorna (hora_inicio, hora_fim, hora_alerta_ate) ou None se o dia não é monitorado."""
    cfg = cfg or _config_monitoramento()
    if cfg.get("especial_ativo") and cfg.get("especial_feriados") and _eh_feriado_nacional(dia):
        return (
            int(cfg["especial_hora_inicio"]),
            int(cfg["especial_hora_fim"]),
            int(cfg["especial_hora_alerta_ate"]),
        )
    weekday = dia.weekday()
    if cfg.get("especial_ativo") and weekday in set(cfg.get("especial_dias") or []):
        return (
            int(cfg["especial_hora_inicio"]),
            int(cfg["especial_hora_fim"]),
            int(cfg["especial_hora_alerta_ate"]),
        )
    if weekday in set(cfg.get("dias") or []):
        return (
            int(cfg["hora_inicio"]),
            int(cfg["hora_fim"]),
            int(cfg["hora_alerta_ate"]),
        )
    return None


def _no_expediente(agora: datetime, cfg: dict[str, Any] | None = None) -> bool:
    faixa = _faixa_expediente(agora.date(), cfg)
    if faixa is None:
        return False
    inicio, fim, _ = faixa
    return inicio <= agora.hour < fim


def _parse_dt(value: Optional[str], *, end_of_day: bool = False) -> datetime:
    if not value:
        hoje = agora_sp().date()
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


def _aplicar_escopo_setor(query, column, escopo_ids: Optional[list[int]]):
    if escopo_ids is None:
        return query
    if not escopo_ids:
        return query.filter(False)
    return query.filter(column.in_(escopo_ids))


def _setor_bucket(sid: int, setores: dict[int, Setor]) -> dict[str, Any]:
    return {
        "setor_id": sid,
        "setor": setores[sid].nome if sid in setores else "—",
        "emitidas": 0,
        "chamadas": 0,
        "finalizadas": 0,
        "esperas": [],
        "notas": [],
        "atendimentos": 0,
        "nao_chamadas": 0,
        "qr_escaneados": 0,
        "pedidos_adiantados": 0,
    }


def _qr_scans_periodo(
    inicio: datetime,
    fim: datetime,
    escopo_ids: Optional[list[int]],
) -> list[QrScan]:
    """Scans reais do QR no período (timestamp do scan, não da emissão).

    1 por senha/token — a tabela `qr_scans` já é unique em senha_id.
    Setores `tipo_setor=streaming` ficam de fora do escopo de analytics.
    """
    q = QrScan.query.filter(QrScan.scanned_at >= inicio, QrScan.scanned_at < fim)
    return _aplicar_escopo_setor(q, QrScan.setor_id, escopo_ids).all()


def _pedidos_adiantados_periodo(
    inicio: datetime,
    fim: datetime,
    escopo_ids: Optional[list[int]],
) -> list[Senha]:
    """Senhas que usaram 'adiantar pedido' no período.

    1 por senha (`tem_pedido`). Data = primeiro envio (`pedido_em`),
    com fallback para `data_hora` em registros legados sem timestamp.
    """
    when_ts = func.coalesce(Senha.pedido_em, Senha.data_hora)
    q = Senha.query.filter(Senha.tem_pedido.is_(True), when_ts >= inicio, when_ts < fim)
    return _aplicar_escopo_setor(q, Senha.setor_id, escopo_ids).all()


def _montar_fluxo_por_setor(
    senhas: list[Senha],
    setores: dict[int, Setor],
    inicio: datetime,
    fim: datetime,
) -> dict[str, Any]:
    """Série temporal de volume (senhas emitidas) por setor de atendimento."""
    atendimento = {
        sid: setor
        for sid, setor in setores.items()
        if not setor_eh_streaming(setor)
    }
    span = fim - inicio
    use_hour = span <= timedelta(days=2)
    granularidade = "hora" if use_hour else "dia"

    counts: dict[tuple[datetime, int], int] = defaultdict(int)
    for senha in senhas:
        if not senha.data_hora or senha.setor_id not in atendimento:
            continue
        if use_hour:
            chave_t = datetime(
                senha.data_hora.year,
                senha.data_hora.month,
                senha.data_hora.day,
                senha.data_hora.hour,
            )
        else:
            chave_t = datetime(senha.data_hora.year, senha.data_hora.month, senha.data_hora.day)
        counts[(chave_t, senha.setor_id)] += 1

    horas_com_volume = {t.hour for (t, _sid), total in counts.items() if total > 0}
    mon = _config_monitoramento()
    grade_ini = int(mon.get("hora_inicio", HORA_INICIO_EXPEDIENTE))
    grade_fim = int(mon.get("hora_fim", HORA_FIM_EXPEDIENTE))

    buckets: list[tuple[datetime, str]] = []
    if use_hour:
        cursor = datetime(inicio.year, inicio.month, inicio.day, inicio.hour)
        while cursor < fim:
            dentro = grade_ini <= cursor.hour <= grade_fim
            if dentro or cursor.hour in horas_com_volume:
                label = (
                    cursor.strftime("%d/%m %Hh")
                    if span > timedelta(days=1)
                    else f"{cursor.hour:02d}h"
                )
                buckets.append((cursor, label))
            cursor += timedelta(hours=1)
    else:
        cursor = datetime(inicio.year, inicio.month, inicio.day)
        while cursor < fim:
            buckets.append((cursor, cursor.strftime("%d/%m")))
            cursor += timedelta(days=1)

    setores_serie = [
        {"id": setor.id, "nome": setor.nome, "chave": f"setor_{setor.id}"}
        for setor in sorted(atendimento.values(), key=lambda item: item.nome or "")
    ]
    series = []
    for momento, label in buckets:
        row: dict[str, Any] = {"t": momento.isoformat(), "label": label}
        for item in setores_serie:
            row[item["chave"]] = counts.get((momento, item["id"]), 0)
        series.append(row)

    return {
        "granularidade": granularidade,
        "setores": setores_serie,
        "series": series,
    }


def _formatar_faixas_hora(horas: list[int]) -> str:
    if not horas:
        return ""
    ordered = sorted(set(horas))
    faixas: list[tuple[int, int]] = []
    inicio = fim = ordered[0]
    for hora in ordered[1:]:
        if hora == fim + 1:
            fim = hora
            continue
        faixas.append((inicio, fim))
        inicio = fim = hora
    faixas.append((inicio, fim))

    partes: list[str] = []
    for a, b in faixas:
        if a == b:
            partes.append(f"{a:02d}h")
        else:
            partes.append(f"{a:02d}h–{b:02d}h")
    if len(partes) == 1:
        return partes[0]
    if len(partes) == 2:
        return f"{partes[0]} e {partes[1]}"
    return ", ".join(partes[:-1]) + f" e {partes[-1]}"


def _hora_cheia_no_periodo(
    dia: date,
    hora: int,
    inicio: datetime,
    fim: datetime,
    agora: datetime,
) -> bool:
    """Hora já encerrada, inteira dentro do filtro e não no futuro."""
    ini_hora = datetime(dia.year, dia.month, dia.day, hora)
    fim_hora = ini_hora + timedelta(hours=1)
    limite = agora if agora < fim else fim
    return ini_hora >= inicio and fim_hora <= limite


def _dias_periodo(inicio: datetime, fim: datetime) -> list[date]:
    if fim <= inicio:
        return []
    dia = inicio.date()
    ultimo = (fim - timedelta(microseconds=1)).date()
    dias: list[date] = []
    while dia <= ultimo:
        dias.append(dia)
        dia += timedelta(days=1)
    return dias


def _resumo_lacunas(
    por_dia: list[tuple[date, list[int]]],
    *,
    vazio: str,
    parcial: str,
) -> str:
    varios = len(por_dia) > 1
    partes: list[str] = []
    cfg = _config_monitoramento()
    for dia, horas in por_dia[:6]:
        prefixo = f"{dia:%d/%m}: " if varios else ""
        faixa = _faixa_expediente(dia, cfg)
        if faixa and horas == list(range(faixa[0], faixa[2] + 1)):
            partes.append(f"{prefixo}{vazio}")
        else:
            partes.append(f"{prefixo}{parcial} {_formatar_faixas_hora(horas)}")
    texto = " · ".join(partes)
    extra = len(por_dia) - 6
    if extra > 0:
        texto += f" · e mais {extra} dia(s)"
    return texto


def _alerta_tempo_sem_evento(
    timestamps: list[datetime],
    inicio: datetime,
    fim: datetime,
    agora: datetime,
    *,
    tipo: str,
    acao: str,
    nome_setor: str | None = None,
    setor_id: int | None = None,
    limite_minutos: int = 60,
) -> dict[str, Any] | None:
    """Alerta se passou o tempo configurado do setor sem o evento no expediente."""
    if not (inicio <= agora < fim):
        return None
    cfg = _config_monitoramento()
    if not _no_expediente(agora, cfg):
        return None

    limite = max(1, int(limite_minutos or 60))
    faixa = _faixa_expediente(agora.date(), cfg)
    if faixa is None:
        return None
    hora_abertura = faixa[0]
    abertura = datetime(agora.year, agora.month, agora.day, hora_abertura)
    anteriores = [ts for ts in timestamps if abertura <= ts <= agora]
    referencia = max(anteriores) if anteriores else abertura
    gap = agora - referencia
    if gap < timedelta(minutes=limite):
        return None

    total_min = int(gap.total_seconds() // 60)
    horas_gap, mins = divmod(total_min, 60)
    duracao = f"{horas_gap}h{mins:02d}" if horas_gap else f"{mins} min"
    if anteriores:
        mensagem = (
            f"Há {duracao} sem {acao} senha "
            f"(limite {limite} min; última às {referencia:%H:%M})."
        )
    else:
        mensagem = (
            f"Há {duracao} sem {acao} senha desde as {abertura:%H:%M} "
            f"(limite {limite} min)."
        )
    if nome_setor:
        mensagem = f"{nome_setor}: {mensagem[:1].lower()}{mensagem[1:]}"
    alerta: dict[str, Any] = {
        "tipo": tipo,
        "severidade": "critical" if gap >= timedelta(minutes=limite * 2) else "warning",
        "mensagem": mensagem,
        "valor": total_min,
    }
    if setor_id is not None:
        alerta["setor_id"] = setor_id
    alerta["referencia"] = referencia.isoformat(timespec="minutes")
    alerta["ociosidade_minutos"] = limite
    return alerta


def _alerta_sem_chamada_recente(
    chamadas_em: list[datetime],
    inicio: datetime,
    fim: datetime,
    agora: datetime,
    *,
    nome_setor: str | None = None,
    setor_id: int | None = None,
    ociosidade_minutos: int = 60,
) -> dict[str, Any] | None:
    return _alerta_tempo_sem_evento(
        chamadas_em,
        inicio,
        fim,
        agora,
        tipo="sem_chamada_recente",
        acao="chamar",
        nome_setor=nome_setor,
        setor_id=setor_id,
        limite_minutos=ociosidade_minutos,
    )


def _alerta_sem_retirada_recente(
    retiradas_em: list[datetime],
    inicio: datetime,
    fim: datetime,
    agora: datetime,
    *,
    nome_setor: str | None = None,
    setor_id: int | None = None,
    limite_minutos: int = 60,
) -> dict[str, Any] | None:
    return _alerta_tempo_sem_evento(
        retiradas_em,
        inicio,
        fim,
        agora,
        tipo="sem_retirada_recente",
        acao="emitir",
        nome_setor=nome_setor,
        setor_id=setor_id,
        limite_minutos=limite_minutos,
    )


def _eventos_horas(
    tipo: str,
    dia: date,
    horas: list[int],
    mensagem_de: Any,
    setor_id: int | None = None,
) -> list[dict[str, Any]]:
    eventos = []
    for hora in horas:
        inicio_hora = datetime(dia.year, dia.month, dia.day, hora)
        eventos.append(
            {
                "chave": f"{tipo}:{setor_id or 0}:{dia.isoformat()}:{hora:02d}",
                "tipo": tipo,
                "severidade": "warning",
                "mensagem": mensagem_de(hora),
                "setor_id": setor_id,
                "ocorrido_em": inicio_hora + timedelta(hours=1),
            }
        )
    return eventos


def _evento_tempo_recente(alerta: dict[str, Any] | None) -> dict[str, Any] | None:
    if not alerta or not alerta.get("referencia"):
        return None
    setor_id = alerta.get("setor_id")
    limite = max(1, int(alerta.get("ociosidade_minutos") or 60))
    tipo = alerta["tipo"]
    return {
        "chave": f"{tipo}:{setor_id or 0}:{alerta['referencia']}:{limite}",
        "tipo": tipo,
        "severidade": alerta["severidade"],
        "mensagem": alerta["mensagem"],
        "setor_id": setor_id,
        "ocorrido_em": datetime.fromisoformat(alerta["referencia"]) + timedelta(minutes=limite),
    }


def _evento_chamada_recente(alerta: dict[str, Any] | None) -> dict[str, Any] | None:
    return _evento_tempo_recente(alerta)


def _alertas_horario(
    senhas: list[Senha],
    inicio: datetime,
    fim: datetime,
    agora: datetime,
    setores: dict[int, Setor] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Lacunas de retirada no expediente + ociosidade recente (sem alerta horário de chamada)."""
    setores = setores or {}
    retiradas: set[tuple[date, int]] = set()
    chamadas_em: list[datetime] = []
    chamadas_em_por_setor: dict[int, list[datetime]] = defaultdict(list)
    retiradas_em: list[datetime] = []
    retiradas_em_por_setor: dict[int, list[datetime]] = defaultdict(list)
    for senha in senhas:
        if senha.data_hora and inicio <= senha.data_hora < fim:
            retiradas.add((senha.data_hora.date(), senha.data_hora.hour))
            retiradas_em.append(senha.data_hora)
            if senha.setor_id:
                retiradas_em_por_setor[senha.setor_id].append(senha.data_hora)
        if senha.chamada_em and inicio <= senha.chamada_em < fim:
            chamadas_em.append(senha.chamada_em)
            if senha.setor_id:
                chamadas_em_por_setor[senha.setor_id].append(senha.chamada_em)

    sem_retirada: list[tuple[date, list[int]]] = []
    cfg = _config_monitoramento()

    for dia in _dias_periodo(inicio, fim):
        faixa = _faixa_expediente(dia, cfg)
        if faixa is None:
            continue
        hora_ini, _, hora_alerta = faixa
        horas_retirada: list[int] = []
        for hora in range(hora_ini, hora_alerta + 1):
            if not _hora_cheia_no_periodo(dia, hora, inicio, fim, agora):
                continue
            if (dia, hora) not in retiradas:
                horas_retirada.append(hora)
        if horas_retirada:
            sem_retirada.append((dia, horas_retirada))

    alertas: list[dict[str, Any]] = []
    if sem_retirada:
        alertas.append(
            {
                "tipo": "sem_retirada",
                "severidade": "warning",
                "mensagem": _resumo_lacunas(
                    sem_retirada,
                    vazio="Nenhuma senha retirada no expediente.",
                    parcial="Horários sem retirada de senha:",
                ),
                "valor": sum(len(horas) for _, horas in sem_retirada),
            }
        )

    if not setores:
        recente_emitir = _alerta_sem_retirada_recente(retiradas_em, inicio, fim, agora)
        recente_chamar = _alerta_sem_chamada_recente(chamadas_em, inicio, fim, agora)
        if recente_emitir:
            alertas.append(recente_emitir)
        if recente_chamar:
            alertas.append(recente_chamar)
        eventos: list[dict[str, Any]] = []
        for dia, horas in sem_retirada:
            eventos.extend(
                _eventos_horas(
                    "sem_retirada",
                    dia,
                    horas,
                    lambda hora: f"Horário {hora:02d}h sem retirada de senha.",
                )
            )
        for recente in (recente_emitir, recente_chamar):
            recente_log = _evento_tempo_recente(recente)
            if recente_log:
                eventos.append(recente_log)
            if recente:
                recente.pop("referencia", None)
                recente.pop("ociosidade_minutos", None)
        return alertas, eventos

    eventos = []
    for dia, horas in sem_retirada:
        eventos.extend(
            _eventos_horas(
                "sem_retirada",
                dia,
                horas,
                lambda hora: f"Horário {hora:02d}h sem retirada de senha.",
            )
        )
    for sid, setor in sorted(setores.items(), key=lambda item: ((item[1].nome or "").lower(), item[0])):
        nome = setor.nome or "—"
        recente_emitir = _alerta_sem_retirada_recente(
            retiradas_em_por_setor.get(sid, []),
            inicio,
            fim,
            agora,
            nome_setor=nome,
            setor_id=sid,
            limite_minutos=int(getattr(setor, "alerta_sem_emitir_minutos", None) or 60),
        )
        if recente_emitir:
            evento = _evento_tempo_recente(recente_emitir)
            recente_emitir.pop("referencia", None)
            recente_emitir.pop("ociosidade_minutos", None)
            alertas.append(recente_emitir)
            if evento:
                eventos.append(evento)
        recente = _alerta_sem_chamada_recente(
            chamadas_em_por_setor.get(sid, []),
            inicio,
            fim,
            agora,
            nome_setor=nome,
            setor_id=sid,
            ociosidade_minutos=int(getattr(setor, "alerta_ociosidade_minutos", None) or 60),
        )
        if recente:
            evento = _evento_chamada_recente(recente)
            recente.pop("referencia", None)
            recente.pop("ociosidade_minutos", None)
            alertas.append(recente)
            if evento:
                eventos.append(evento)
    return alertas, eventos


def registrar_logs_alerta(eventos: list[dict[str, Any]]) -> list[int]:
    """Grava cada alerta uma vez. A mesma chave só atualiza a mensagem.

    Retorna os IDs dos alertas recém-criados (para despacho Telegram/WhatsApp).
    """
    from backend.models import AlertaLog

    if not eventos:
        return []
    agora = agora_sp()
    chaves = [evento["chave"] for evento in eventos]
    existentes = {
        row.chave: row
        for row in AlertaLog.query.filter(AlertaLog.chave.in_(chaves)).all()
    }
    novos: list[AlertaLog] = []
    for evento in eventos:
        row = existentes.get(evento["chave"])
        if row is not None:
            row.mensagem = evento["mensagem"]
            row.severidade = evento["severidade"]
            row.atualizado_em = agora
            continue
        row = AlertaLog(
            chave=evento["chave"],
            tipo=evento["tipo"],
            severidade=evento["severidade"],
            mensagem=evento["mensagem"],
            setor_id=evento.get("setor_id"),
            ocorrido_em=evento["ocorrido_em"],
            criado_em=agora,
            atualizado_em=agora,
            enviado_telegram=False,
            enviado_whatsapp=False,
        )
        db.session.add(row)
        existentes[evento["chave"]] = row
        novos.append(row)
    db.session.commit()
    return [row.id for row in novos if row.id is not None]


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
    agora = agora_sp()

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

    atendimento_ids = [
        sid
        for (sid,) in db.session.query(Setor.id)
        .filter(or_(Setor.tipo_setor.is_(None), Setor.tipo_setor != TIPO_SETOR_STREAMING))
        .all()
    ]
    if escopo_ids is None:
        escopo_ids = atendimento_ids
    else:
        permitidos = set(atendimento_ids)
        escopo_ids = [sid for sid in escopo_ids if sid in permitidos]

    q = Senha.query.filter(Senha.data_hora >= inicio, Senha.data_hora < fim)
    streaming_ids = [
        sid for (sid,) in db.session.query(Setor.id).filter(Setor.tipo_setor == TIPO_SETOR_STREAMING).all()
    ]
    if streaming_ids:
        q = q.filter(~Senha.setor_id.in_(streaming_ids))
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
    setores = {s.id: s for s in setores_q.all() if not setor_eh_streaming(s)}
    operadores = {o.id: o for o in Operador.query.all()}
    if escopo_ids is not None:
        operadores = {oid: o for oid, o in operadores.items() if o.setor_id in escopo_ids}

    # Finalizados no período (por data do finalizado ou da senha emitida)
    fq = (
        db.session.query(Finalizado, Senha)
        .join(Senha, Senha.id == Finalizado.senha_id)
        .filter(Senha.data_hora >= inicio, Senha.data_hora < fim)
    )
    if streaming_ids:
        fq = fq.filter(~Senha.setor_id.in_(streaming_ids))
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

    qr_scans = _qr_scans_periodo(inicio, fim, escopo_ids)
    pedidos_adiantados_rows = _pedidos_adiantados_periodo(inicio, fim, escopo_ids)

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
        "qr_escaneados": len(qr_scans),
        "pedidos_adiantados": len(pedidos_adiantados_rows),
    }

    # Por setor
    por_setor_map: dict[int, dict[str, Any]] = {}
    for s in senhas:
        sid = s.setor_id or 0
        bucket = por_setor_map.setdefault(sid, _setor_bucket(sid, setores))
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
        bucket = por_setor_map.setdefault(sid, _setor_bucket(sid, setores))
        bucket["atendimentos"] += 1
        n = _parse_nota(fin.avaliacao)
        if n is not None:
            bucket["notas"].append(n)

    for scan in qr_scans:
        sid = scan.setor_id or 0
        bucket = por_setor_map.setdefault(sid, _setor_bucket(sid, setores))
        bucket["qr_escaneados"] += 1

    for senha in pedidos_adiantados_rows:
        sid = senha.setor_id or 0
        bucket = por_setor_map.setdefault(sid, _setor_bucket(sid, setores))
        bucket["pedidos_adiantados"] += 1

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
                "qr_escaneados": b["qr_escaneados"],
                "pedidos_adiantados": b["pedidos_adiantados"],
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
        if s.data_hora and inicio <= s.data_hora < fim:
            por_hora_map[s.data_hora.hour]["retiradas"] += 1
        if s.chamada_em and inicio <= s.chamada_em < fim:
            hora_chamada = s.chamada_em.hour
            por_hora_map[hora_chamada]["chamadas"] += 1
            em = _espera_minutos(s)
            if em is not None:
                por_hora_map[hora_chamada]["esperas"].append(em)
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
        setor_alerta = setores.get(row["setor_id"])
        if setor_alerta is not None and setor_alerta.alertas_ativos is False:
            continue
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

    setores_alerta = {
        sid: setor
        for sid, setor in setores.items()
        if setor.alertas_ativos is not False
    }
    lacunas, eventos_lacuna = _alertas_horario(senhas, inicio, fim, agora, setores_alerta)
    from backend.services.alerta_notify_service import tipos_alerta_habilitados

    tipos_on = tipos_alerta_habilitados()
    lacunas = [a for a in lacunas if a.get("tipo") in tipos_on]
    eventos_lacuna = [e for e in eventos_lacuna if e.get("tipo") in tipos_on]
    alertas = lacunas + alertas
    novos_ids: list[int] = []
    try:
        novos_ids = registrar_logs_alerta(eventos_lacuna)
    except Exception:
        db.session.rollback()
    if novos_ids:
        try:
            from backend.services.alerta_notify_service import despachar_alertas_pendentes

            despachar_alertas_pendentes(novos_ids)
        except Exception:
            db.session.rollback()

    mon = _config_monitoramento()
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
        "fluxo_por_setor": _montar_fluxo_por_setor(senhas, setores, inicio, fim),
        "heatmap": {
            "hora_inicio": int(mon["hora_inicio"]),
            "hora_fim": int(mon["hora_fim"]),
            "hora_alerta_ate": int(mon["hora_alerta_ate"]),
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
