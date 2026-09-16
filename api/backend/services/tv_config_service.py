"""Serialização da fila de mídia da TV (imagens + vídeos por setor)."""
from backend.extensions import db
from backend.models import Propaganda, Setor, setor_propagandas
from backend.sockets.emitters import emit_tv_config_atualizada

INTERVALO_IMAGEM_MS = 15_000


def serializar_midia(propaganda: Propaganda) -> dict:
    return {
        "id": propaganda.id,
        "arquivo": propaganda.arquivo,
        "ordem": propaganda.ordem,
        "tipo": propaganda.tipo or "image",
    }


def serializar_tv_config(setor: Setor | None) -> dict:
    ativas = bool(setor.propagandas_ativas) if setor else False
    imagens = []
    if ativas and setor is not None:
        imagens = [
            serializar_midia(item)
            for item in (
                Propaganda.query.filter_by(ativo=True)
                .join(setor_propagandas, setor_propagandas.c.propaganda_id == Propaganda.id)
                .filter(setor_propagandas.c.setor_id == setor.id)
                .order_by(Propaganda.ordem.asc(), Propaganda.id.asc())
                .all()
            )
        ]
    return {
        "propagandas_ativas": ativas,
        "layout_tv_web": (setor.layout_tv_web if setor else None) or "propaganda",
        "setor_nome": setor.nome if setor else None,
        "imagens": imagens,
        "intervalo_ms": INTERVALO_IMAGEM_MS,
    }


def ativar_propagandas_nos_setores(setores: list[Setor]) -> None:
    for setor in setores:
        setor.propagandas_ativas = True


def notificar_tvs(setor_ids: list[int]) -> None:
    seen: set[int] = set()
    for setor_id in setor_ids:
        if setor_id in seen:
            continue
        seen.add(setor_id)
        setor = db.session.get(Setor, setor_id)
        if setor:
            emit_tv_config_atualizada(setor.id, serializar_tv_config(setor))
