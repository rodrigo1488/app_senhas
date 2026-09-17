"""Serialização da fila de mídia da TV e da espera do cliente."""
from backend.extensions import db
from backend.models import Propaganda, Setor, setor_eh_streaming, setor_propagandas, setor_propagandas_cliente
from backend.sockets.emitters import emit_cliente_config_atualizada, emit_tv_config_atualizada

INTERVALO_IMAGEM_MS = 15_000


def serializar_midia(propaganda: Propaganda) -> dict:
    return {
        "id": propaganda.id,
        "arquivo": propaganda.arquivo,
        "ordem": propaganda.ordem,
        "tipo": propaganda.tipo or "image",
    }


def _listar_midias_ativas(setor_id: int, associacao) -> list[dict]:
    return [
        serializar_midia(item)
        for item in (
            Propaganda.query.filter_by(ativo=True)
            .join(associacao, associacao.c.propaganda_id == Propaganda.id)
            .filter(associacao.c.setor_id == setor_id)
            .order_by(Propaganda.ordem.asc(), Propaganda.id.asc())
            .all()
        )
    ]


def propaganda_ids_cliente(setor_id: int) -> list[int]:
    itens = (
        Propaganda.query.join(
            setor_propagandas_cliente,
            setor_propagandas_cliente.c.propaganda_id == Propaganda.id,
        )
        .filter(setor_propagandas_cliente.c.setor_id == setor_id)
        .order_by(Propaganda.ordem.asc(), Propaganda.id.asc())
        .all()
    )
    return [item.id for item in itens]


def serializar_tv_config(setor: Setor | None) -> dict:
    ativas = bool(setor.propagandas_ativas) if setor else False
    imagens = _listar_midias_ativas(setor.id, setor_propagandas) if ativas and setor is not None else []
    return {
        "propagandas_ativas": ativas,
        "layout_tv_web": (setor.layout_tv_web if setor else None) or "propaganda",
        "orientacao_tv": (setor.orientacao_tv if setor else None) or "horizontal",
        "setor_nome": setor.nome if setor else None,
        "imagens": imagens,
        "intervalo_ms": INTERVALO_IMAGEM_MS,
    }


def serializar_cliente_config(setor: Setor | None) -> dict:
    """Fila da tela de espera do cliente — sem layout/orientação da TV."""
    ativas = bool(setor.propagandas_cliente_ativas) if setor else False
    imagens = (
        _listar_midias_ativas(setor.id, setor_propagandas_cliente) if ativas and setor is not None else []
    )
    return {
        "propagandas_ativas": ativas,
        "imagens": imagens,
        "intervalo_ms": INTERVALO_IMAGEM_MS,
    }


def ativar_propagandas_nos_setores(setores: list[Setor]) -> None:
    for setor in setores:
        setor.propagandas_ativas = True


def ativar_propagandas_cliente_nos_setores(setores: list[Setor]) -> None:
    for setor in setores:
        setor.propagandas_cliente_ativas = True


def notificar_tvs(setor_ids: list[int]) -> None:
    seen: set[int] = set()
    for setor_id in setor_ids:
        if setor_id in seen:
            continue
        seen.add(setor_id)
        setor = db.session.get(Setor, setor_id)
        if setor:
            emit_tv_config_atualizada(setor.id, serializar_tv_config(setor))


def notificar_clientes(setor_ids: list[int]) -> None:
    seen: set[int] = set()
    for setor_id in setor_ids:
        if setor_id in seen:
            continue
        seen.add(setor_id)
        setor = db.session.get(Setor, setor_id)
        if setor:
            emit_cliente_config_atualizada(setor.id, serializar_cliente_config(setor))


def atribuir_midias_cliente(
    setor_id: int,
    propaganda_ids: list[int],
    *,
    ativas: bool | None = None,
) -> dict:
    setor = db.session.get(Setor, setor_id)
    if not setor:
        raise ValueError("Setor não encontrado")
    if setor_eh_streaming(setor):
        raise ValueError("Setor de streaming não possui tela de espera de cliente")
    itens = Propaganda.query.filter(Propaganda.id.in_(propaganda_ids)).all() if propaganda_ids else []
    if propaganda_ids and len(itens) != len(set(propaganda_ids)):
        raise ValueError("Uma ou mais mídias não foram encontradas")
    by_id = {item.id: item for item in itens}
    ordered = [by_id[item_id] for item_id in propaganda_ids if item_id in by_id]
    setor.propagandas_cliente = ordered
    if ativas is not None:
        setor.propagandas_cliente_ativas = bool(ativas)
    elif ordered:
        setor.propagandas_cliente_ativas = True
    db.session.commit()
    emit_cliente_config_atualizada(setor.id, serializar_cliente_config(setor))
    return {
        "setor_id": setor.id,
        "propaganda_ids": [item.id for item in ordered],
        "propagandas_cliente_ativas": bool(setor.propagandas_cliente_ativas),
    }
