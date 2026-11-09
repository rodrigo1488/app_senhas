"""Presença de TVs e tablets: o aparelho envia o IP para o administrador."""
from __future__ import annotations

from datetime import timedelta

from backend.extensions import db
from backend.models import PresencaEquipamento, Setor
from backend.timezone import agora_sp

PAPEIS_EQUIPAMENTO = {"tv", "streaming", "cliente", "operador", "avaliacao"}
PAPEIS_TABLET = {"cliente", "operador", "avaliacao"}
JANELA_ONLINE = timedelta(seconds=45)
JANELA_LISTAGEM = timedelta(hours=36)

ROTULO_PAPEL = {
    "cliente": "Cliente",
    "operador": "Operador",
    "avaliacao": "Avaliação",
    "tv": "Painel",
    "streaming": "Streaming",
}


def ipv4_util(valor) -> str | None:
    ip = str(valor or "").strip()
    if not ip or ip.lower() in {"unknown", "localhost"}:
        return None
    if ip.count(":") == 1 and "." in ip:
        ip = ip.split(":", 1)[0]
    partes = ip.split(".")
    if len(partes) != 4:
        return None
    try:
        numeros = [int(parte) for parte in partes]
    except ValueError:
        return None
    if any(numero < 0 or numero > 255 for numero in numeros):
        return None
    if numeros == [127, 0, 0, 1] or numeros[0] == 0:
        return None
    return ".".join(str(numero) for numero in numeros)


def _privado(ip: str) -> bool:
    primeiro, segundo, _, _ = (int(parte) for parte in ip.split("."))
    if primeiro == 10:
        return True
    if primeiro == 192 and segundo == 168:
        return True
    return primeiro == 172 and 16 <= segundo <= 31


def ip_de_equipamento(informado, remoto) -> str | None:
    """Prefere o IP de LAN informado pelo aparelho; senão, o visto pelo servidor."""
    do_aparelho = ipv4_util(informado)
    do_servidor = ipv4_util(remoto)
    if do_aparelho and _privado(do_aparelho):
        return do_aparelho
    if do_servidor:
        return do_servidor
    return do_aparelho


def registrar_presenca(
    *,
    device_id: str,
    papel: str,
    ip_informado,
    ip_remoto,
    nome,
    setor_id: int,
) -> PresencaEquipamento:
    if papel not in PAPEIS_EQUIPAMENTO:
        raise ValueError("Papel do equipamento inválido")
    ip = ip_de_equipamento(ip_informado, ip_remoto)
    nome_final = str(nome or "").strip()[:80] or None
    row = PresencaEquipamento.query.filter_by(device_id=device_id).first()
    if not row:
        row = PresencaEquipamento(device_id=device_id, papel=papel)
        db.session.add(row)
    row.papel = papel
    if ip:
        row.ip = ip
    row.nome = nome_final
    row.setor_id = setor_id
    row.last_seen = agora_sp()
    db.session.commit()
    return row


def _recentes() -> list[PresencaEquipamento]:
    limite = agora_sp() - JANELA_LISTAGEM
    return (
        PresencaEquipamento.query.filter(PresencaEquipamento.last_seen >= limite)
        .order_by(PresencaEquipamento.last_seen.desc())
        .all()
    )


def _online(row: PresencaEquipamento) -> bool:
    if not row.last_seen:
        return False
    return agora_sp() - row.last_seen <= JANELA_ONLINE


def ips_unicos(valores: list[str]) -> list[str]:
    vistos: list[str] = []
    for valor in valores:
        if valor and valor not in vistos:
            vistos.append(valor)
    return vistos


def ips_da_tv(chave: str, setor_id: int | None, tipo: str) -> list[str]:
    recente = _recentes()
    if tipo == "setor":
        return ips_unicos(
            [row.ip for row in recente if row.papel == "tv" and row.setor_id == setor_id and row.ip]
        )
    direto = ipv4_util(chave)
    if direto:
        return [direto]
    device_id = chave[4:] if chave.startswith("apk:") else ""
    if not device_id:
        return []
    return ips_unicos(
        [
            row.ip
            for row in recente
            if row.device_id == device_id and row.papel == "streaming" and row.ip
        ]
    )


def tablets_do_setor(setor_id: int) -> list[dict]:
    return [
        {
            "ip": row.ip,
            "papel": row.papel,
            "nome": row.nome or "",
        }
        for row in _recentes()
        if row.papel in PAPEIS_TABLET and row.setor_id == setor_id and row.ip
    ]


def listar_tablets_simulacao() -> list[dict]:
    """Itens extras do simulador: cada tablet com o IP na descrição."""
    telas: list[dict] = []
    for row in _recentes():
        if row.papel not in PAPEIS_TABLET:
            continue
        setor = db.session.get(Setor, row.setor_id) if row.setor_id else row.setor
        nome_setor = setor.nome if setor else "Sem setor"
        papel = ROTULO_PAPEL.get(row.papel, row.papel)
        telas.append(
            {
                "chave": f"tablet:{row.device_id}",
                "id": row.id,
                "setor_id": row.setor_id,
                "tipo": "tablet",
                "nome": row.nome or "Tablet",
                "subtitulo": f"{papel} · {nome_setor}",
                "is_online": _online(row),
                "formato": "horizontal",
                "rotacao_tv": 0,
                "modo": "fila",
                "intervalo_ms": 15000,
                "propagandas_ativas": False,
                "midias": [],
                "senha_normal": None,
                "senha_preferencial": None,
                "chamada_atual": None,
                "chamada_atual_tipo": None,
                "proximas": [],
                "ips": [row.ip] if row.ip else [],
                "tablets": [],
            }
        )
    return telas
