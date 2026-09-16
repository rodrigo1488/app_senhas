"""Registro de TVs (streaming legado + painel de senha) e fila de mídia."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, insert, select

from backend.extensions import db, socketio
from backend.models import (
    Propaganda,
    Setor,
    TvDispositivo,
    dispositivo_propagandas,
    setor_propagandas,
)
from backend.services.tv_config_service import INTERVALO_IMAGEM_MS, serializar_tv_config
from backend.sockets.emitters import emit_tv_config_atualizada

connected_by_chave: dict[str, str] = {}
chave_by_sid: dict[str, str] = {}


def chave_setor(setor_id: int) -> str:
    return f"setor:{setor_id}"


def media_public_path(arquivo: str) -> str:
    nome = (arquivo or "").replace("\\", "/").lstrip("/")
    if nome.startswith("uploads/"):
        nome = nome[len("uploads/") :]
    if nome.startswith("media/"):
        nome = nome[len("media/") :]
    return f"/media/{nome}"


def _tipo_arquivo(arquivo: str) -> str:
    nome = (arquivo or "").lower()
    return "video" if nome.endswith(".mp4") else "image"


def fila_streaming(dispositivo: TvDispositivo) -> list[dict]:
    rows = db.session.execute(
        select(dispositivo_propagandas.c.propaganda_id, dispositivo_propagandas.c.ordem)
        .where(dispositivo_propagandas.c.dispositivo_id == dispositivo.id)
        .order_by(dispositivo_propagandas.c.ordem.asc(), dispositivo_propagandas.c.propaganda_id.asc())
    ).all()
    if not rows:
        return []
    by_id = {
        item.id: item
        for item in Propaganda.query.filter(Propaganda.id.in_([row.propaganda_id for row in rows])).all()
    }
    fila = []
    for row in rows:
        item = by_id.get(row.propaganda_id)
        if not item or not item.ativo:
            continue
        fila.append(
            {
                "path": media_public_path(item.arquivo),
                "type": item.tipo or _tipo_arquivo(item.arquivo),
                "order": row.ordem,
                "duration": INTERVALO_IMAGEM_MS,
            }
        )
    return fila


def propaganda_ids_dispositivo(dispositivo_id: int) -> list[int]:
    rows = db.session.execute(
        select(dispositivo_propagandas.c.propaganda_id)
        .where(dispositivo_propagandas.c.dispositivo_id == dispositivo_id)
        .order_by(dispositivo_propagandas.c.ordem.asc())
    ).all()
    return [row.propaganda_id for row in rows]


def propaganda_ids_setor(setor_id: int) -> list[int]:
    rows = db.session.execute(
        select(setor_propagandas.c.propaganda_id)
        .where(setor_propagandas.c.setor_id == setor_id)
    ).all()
    ids = [row.propaganda_id for row in rows]
    if not ids:
        return []
    itens = (
        Propaganda.query.filter(Propaganda.id.in_(ids))
        .order_by(Propaganda.ordem.asc(), Propaganda.id.asc())
        .all()
    )
    return [item.id for item in itens]


def substituir_fila_dispositivo(dispositivo: TvDispositivo, propaganda_ids: list[int]) -> None:
    db.session.execute(delete(dispositivo_propagandas).where(dispositivo_propagandas.c.dispositivo_id == dispositivo.id))
    for index, propaganda_id in enumerate(propaganda_ids):
        db.session.execute(
            insert(dispositivo_propagandas).values(
                dispositivo_id=dispositivo.id,
                propaganda_id=propaganda_id,
                ordem=index,
            )
        )


def emitir_fila_streaming(dispositivo: TvDispositivo) -> None:
    socketio.emit("queue_updated", {"queue": fila_streaming(dispositivo)}, room=dispositivo.chave)


def marcar_online(chave: str, sid: str | None) -> None:
    if sid:
        antigo = connected_by_chave.get(chave)
        if antigo and antigo != sid:
            chave_by_sid.pop(antigo, None)
        connected_by_chave[chave] = sid
        chave_by_sid[sid] = chave
    dispositivo = TvDispositivo.query.filter_by(chave=chave).first()
    if dispositivo:
        dispositivo.is_online = True
        dispositivo.last_seen = datetime.now()


def marcar_offline_sid(sid: str) -> None:
    chave = chave_by_sid.pop(sid, None)
    if not chave:
        return
    if connected_by_chave.get(chave) == sid:
        connected_by_chave.pop(chave, None)
    dispositivo = TvDispositivo.query.filter_by(chave=chave).first()
    if dispositivo:
        dispositivo.is_online = False
        dispositivo.last_seen = datetime.now()
        db.session.commit()


def esta_online(chave: str) -> bool:
    return chave in connected_by_chave


def registrar_streaming(
    *,
    ip_address: str,
    device_name: str = "Dispositivo",
    user_agent: str = "",
    nome: str | None = None,
    sid: str | None = None,
) -> TvDispositivo:
    nome_final = (nome or device_name or "TV").strip() or "TV"
    existente_por_nome = TvDispositivo.query.filter_by(tipo="streaming", nome=nome_final).first()
    dispositivo = TvDispositivo.query.filter_by(chave=ip_address).first()

    if existente_por_nome and existente_por_nome.chave != ip_address:
        if dispositivo and dispositivo.id != existente_por_nome.id:
            db.session.delete(dispositivo)
        existente_por_nome.chave = ip_address
        dispositivo = existente_por_nome

    if not dispositivo:
        dispositivo = TvDispositivo(
            tipo="streaming",
            chave=ip_address,
            nome=nome_final,
        )
        db.session.add(dispositivo)

    dispositivo.tipo = "streaming"
    dispositivo.nome = nome_final
    dispositivo.device_name = device_name
    dispositivo.user_agent = user_agent
    dispositivo.last_seen = datetime.now()
    dispositivo.is_online = True
    db.session.commit()
    marcar_online(dispositivo.chave, sid)
    return dispositivo


def registrar_setor_tv(setor: Setor, sid: str | None = None) -> TvDispositivo:
    chave = chave_setor(setor.id)
    dispositivo = TvDispositivo.query.filter_by(chave=chave).first()
    if not dispositivo:
        dispositivo = TvDispositivo(
            tipo="setor",
            chave=chave,
            nome=setor.nome,
            setor_id=setor.id,
        )
        db.session.add(dispositivo)
    dispositivo.tipo = "setor"
    dispositivo.nome = setor.nome
    dispositivo.setor_id = setor.id
    dispositivo.last_seen = datetime.now()
    dispositivo.is_online = True
    db.session.commit()
    marcar_online(chave, sid)
    return dispositivo


def atribuir_paths_streaming(ip_address: str, media_list: list[dict]) -> TvDispositivo:
    dispositivo = TvDispositivo.query.filter_by(chave=ip_address).first()
    if not dispositivo:
        dispositivo = registrar_streaming(ip_address=ip_address, nome=ip_address)

    ids: list[int] = []
    for media in media_list:
        path = str(media.get("path") or "")
        arquivo = path_para_arquivo(path)
        propaganda = Propaganda.query.filter_by(arquivo=arquivo).first() if arquivo else None
        if propaganda:
            ids.append(propaganda.id)
            continue
        tipo = media.get("type") or _tipo_arquivo(arquivo)
        if arquivo:
            propaganda = Propaganda(arquivo=arquivo, tipo=tipo, ativo=True, ordem=0)
            db.session.add(propaganda)
            db.session.flush()
            ids.append(propaganda.id)
    substituir_fila_dispositivo(dispositivo, ids)
    db.session.commit()
    emitir_fila_streaming(dispositivo)
    return dispositivo


def path_para_arquivo(path: str) -> str:
    nome = (path or "").replace("\\", "/").lstrip("/")
    for prefix in ("media/", "uploads/"):
        if nome.startswith(prefix):
            nome = nome[len(prefix) :]
    return nome


def listar_tvs_admin() -> list[dict]:
    setores = Setor.query.order_by(Setor.nome.asc()).all()
    streaming = (
        TvDispositivo.query.filter_by(tipo="streaming")
        .order_by(TvDispositivo.last_seen.desc())
        .all()
    )
    tvs: list[dict] = []
    for setor in setores:
        chave = chave_setor(setor.id)
        tvs.append(
            {
                "id": setor.id,
                "tipo": "setor",
                "chave": chave,
                "nome": setor.nome,
                "device_name": "Painel de senhas",
                "is_online": esta_online(chave),
                "setor_id": setor.id,
                "propaganda_ids": propaganda_ids_setor(setor.id),
                "layout_tv_web": setor.layout_tv_web or "propaganda",
            }
        )
    for dispositivo in streaming:
        tvs.append(
            dispositivo.to_admin_dict(
                online=esta_online(dispositivo.chave),
                propaganda_ids=propaganda_ids_dispositivo(dispositivo.id),
            )
        )
    return tvs


def atribuir_midias_tv(*, tipo: str, alvo_id: int, propaganda_ids: list[int]) -> dict:
    itens = Propaganda.query.filter(Propaganda.id.in_(propaganda_ids)).all() if propaganda_ids else []
    if propaganda_ids and len(itens) != len(set(propaganda_ids)):
        raise ValueError("Uma ou mais mídias não foram encontradas")
    ordered = []
    by_id = {item.id: item for item in itens}
    for propaganda_id in propaganda_ids:
        item = by_id.get(propaganda_id)
        if item:
            ordered.append(item)

    if tipo == "setor":
        setor = db.session.get(Setor, alvo_id)
        if not setor:
            raise ValueError("Setor não encontrado")
        setor.propagandas = ordered
        if ordered:
            setor.propagandas_ativas = True
        db.session.commit()
        emit_tv_config_atualizada(setor.id, serializar_tv_config(setor))
        return {"tipo": "setor", "id": setor.id, "propaganda_ids": [item.id for item in ordered]}

    dispositivo = db.session.get(TvDispositivo, alvo_id)
    if not dispositivo or dispositivo.tipo != "streaming":
        raise ValueError("TV de streaming não encontrada")
    substituir_fila_dispositivo(dispositivo, [item.id for item in ordered])
    db.session.commit()
    emitir_fila_streaming(dispositivo)
    return {"tipo": "streaming", "id": dispositivo.id, "propaganda_ids": [item.id for item in ordered]}


def biblioteca_como_media_files() -> dict:
    files = []
    for item in Propaganda.query.filter_by(ativo=True).order_by(Propaganda.ordem.asc()).all():
        files.append(
            {
                "filename": item.arquivo,
                "path": media_public_path(item.arquivo),
                "type": item.tipo or _tipo_arquivo(item.arquivo),
                "folder": "",
            }
        )
    return {"files": files, "folders": [], "current_path": ""}
