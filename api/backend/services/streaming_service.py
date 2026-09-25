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
    setor_eh_streaming,
    setor_propagandas,
)
from backend.services.tv_config_service import INTERVALO_IMAGEM_MS, serializar_tv_config
from backend.sockets.emitters import emit_tv_config_atualizada
from backend.utils import (
    normalizar_orientacao_tv,
    normalizar_rotacao_tv,
    orientacao_de_rotacao,
    rotacao_de_orientacao,
)

connected_by_chave: dict[str, str] = {}
chave_by_sid: dict[str, str] = {}


def chave_setor(setor_id: int) -> str:
    return f"setor:{setor_id}"


def media_public_path(arquivo: str, orientacao: str = "horizontal") -> str:
    nome = (arquivo or "").replace("\\", "/").lstrip("/")
    if nome.startswith("uploads/"):
        nome = nome[len("uploads/") :]
    if nome.startswith("media/"):
        nome = nome[len("media/") :]
    # Sem letterbox/rotação no servidor: o APK usa Fit + ForcedDisplayOrientation
    # conforme `rotacao_tv` do dispositivo (evitar imagem "bichada" por dupla rotação).
    _ = normalizar_orientacao_tv(orientacao)
    return f"/media/{nome}"


def _tipo_arquivo(arquivo: str) -> str:
    nome = (arquivo or "").lower()
    return "video" if nome.endswith(".mp4") else "image"


def rotacao_do_dispositivo(dispositivo: TvDispositivo) -> int:
    """Ângulo físico desta TV (campo do dispositivo, não do setor)."""
    try:
        return normalizar_rotacao_tv(getattr(dispositivo, "rotacao_tv", None))
    except ValueError:
        return rotacao_de_orientacao(getattr(dispositivo, "orientacao_tv", None))


def _orientacao_do_dispositivo(dispositivo: TvDispositivo) -> str:
    """Compat binária derivada de rotacao_tv."""
    return orientacao_de_rotacao(rotacao_do_dispositivo(dispositivo))


def _aplicar_rotacao(dispositivo: TvDispositivo, rotacao: int) -> None:
    dispositivo.rotacao_tv = rotacao
    dispositivo.orientacao_tv = orientacao_de_rotacao(rotacao)


def fila_streaming(dispositivo: TvDispositivo) -> list[dict]:
    rows = db.session.execute(
        select(dispositivo_propagandas.c.propaganda_id, dispositivo_propagandas.c.ordem)
        .where(dispositivo_propagandas.c.dispositivo_id == dispositivo.id)
        .order_by(dispositivo_propagandas.c.ordem.asc(), dispositivo_propagandas.c.propaganda_id.asc())
    ).all()
    if not rows:
        return []
    orientacao = _orientacao_do_dispositivo(dispositivo)
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
                "path": media_public_path(item.arquivo, orientacao),
                "type": item.tipo or _tipo_arquivo(item.arquivo),
                "order": row.ordem,
                "duration": INTERVALO_IMAGEM_MS,
                "propaganda_id": item.id,
            }
        )
    return fila


def item_fila_de_propaganda(dispositivo: TvDispositivo, propaganda: Propaganda) -> dict:
    orientacao = _orientacao_do_dispositivo(dispositivo)
    return {
        "path": media_public_path(propaganda.arquivo, orientacao),
        "type": propaganda.tipo or _tipo_arquivo(propaganda.arquivo),
        "order": 0,
        "duration": INTERVALO_IMAGEM_MS,
        "propaganda_id": propaganda.id,
    }


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
    rotacao = rotacao_do_dispositivo(dispositivo)
    socketio.emit(
        "queue_updated",
        {
            "queue": fila_streaming(dispositivo),
            "rotacao_tv": rotacao,
            "orientacao_tv": orientacao_de_rotacao(rotacao),
        },
        room=dispositivo.chave,
    )


PREVIEW_DURATION_MS = 20_000


def emitir_preview_streaming(
    dispositivo: TvDispositivo,
    *,
    propaganda_id: int | None = None,
    duration_ms: int = PREVIEW_DURATION_MS,
) -> dict:
    """Emite `media_preview` na room da TV para fullscreen temporário."""
    if dispositivo.tipo != "streaming":
        raise ValueError("Pré-visualização só está disponível para TVs de streaming")

    item = None
    if propaganda_id is not None:
        propaganda = db.session.get(Propaganda, propaganda_id)
        if not propaganda or not propaganda.ativo:
            raise ValueError("Mídia não encontrada ou inativa")
        item = item_fila_de_propaganda(dispositivo, propaganda)
    else:
        fila = fila_streaming(dispositivo)
        if not fila:
            raise ValueError("Esta TV não tem mídias na fila para pré-visualizar")
        item = fila[0]

    duracao = max(3_000, min(int(duration_ms or PREVIEW_DURATION_MS), 120_000))
    rotacao = rotacao_do_dispositivo(dispositivo)
    payload = {
        "item": item,
        "duration_ms": duracao,
        "rotacao_tv": rotacao,
        "orientacao_tv": orientacao_de_rotacao(rotacao),
    }
    socketio.emit("media_preview", payload, room=dispositivo.chave)
    return payload


def emitir_filas_streaming_do_setor(setor_id: int) -> None:
    dispositivos = TvDispositivo.query.filter_by(tipo="streaming", setor_id=setor_id).all()
    for dispositivo in dispositivos:
        emitir_fila_streaming(dispositivo)


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


def chave_apk(device_id: str) -> str:
    return f"apk:{(device_id or '').strip()}"


def proximo_nome_streaming_setor(setor_nome: str) -> str:
    """Primeira TV = nome do setor; seguintes = '2 Nome', '3 Nome', …"""
    base = (setor_nome or "").strip() or "TV"
    nomes = {
        (d.nome or "").strip()
        for d in TvDispositivo.query.filter_by(tipo="streaming").all()
        if d.nome
    }
    if base not in nomes:
        return base
    n = 2
    while f"{n} {base}" in nomes:
        n += 1
    return f"{n} {base}"


def registrar_streaming_apk(
    *,
    device_id: str,
    setor: Setor,
    device_name: str = "Android",
    user_agent: str = "",
    sid: str | None = None,
) -> TvDispositivo:
    """Registra/reconecta TV de propagandas criada pelo app (sem /smart|/legacy)."""
    chave = chave_apk(device_id)
    if not device_id.strip():
        raise ValueError("device_id é obrigatório")

    dispositivo = TvDispositivo.query.filter_by(chave=chave).first()
    if dispositivo:
        dispositivo.tipo = "streaming"
        dispositivo.setor_id = setor.id
        dispositivo.device_name = device_name
        dispositivo.user_agent = user_agent
        dispositivo.last_seen = datetime.now()
        dispositivo.is_online = True
        if getattr(dispositivo, "rotacao_tv", None) is None:
            _aplicar_rotacao(dispositivo, 0)
        elif not (dispositivo.orientacao_tv or "").strip():
            dispositivo.orientacao_tv = orientacao_de_rotacao(rotacao_do_dispositivo(dispositivo))
        db.session.commit()
        marcar_online(chave, sid)
        return dispositivo

    nome = proximo_nome_streaming_setor(setor.nome)
    # Cria só por chave — sem merge por nome (evita duplicar/roubar TV legada).
    dispositivo = TvDispositivo(
        tipo="streaming",
        chave=chave,
        nome=nome,
        device_name=device_name,
        user_agent=user_agent,
        setor_id=setor.id,
        orientacao_tv="horizontal",
        rotacao_tv=0,
        last_seen=datetime.now(),
        is_online=True,
    )
    db.session.add(dispositivo)
    db.session.commit()
    marcar_online(chave, sid)
    return dispositivo


def registrar_streaming(
    *,
    ip_address: str,
    device_name: str = "Dispositivo",
    user_agent: str = "",
    nome: str | None = None,
    sid: str | None = None,
) -> TvDispositivo:
    nome_desejado = (nome or device_name or "TV").strip() or "TV"
    dispositivo = TvDispositivo.query.filter_by(chave=ip_address).first()

    if not dispositivo:
        # Colisão de nome: gera sufixo em vez de sequestrar outra TV.
        nome_final = nome_desejado
        nomes = {
            (d.nome or "").strip()
            for d in TvDispositivo.query.filter_by(tipo="streaming").all()
            if d.nome
        }
        if nome_final in nomes:
            n = 2
            while f"{n} {nome_desejado}" in nomes:
                n += 1
            nome_final = f"{n} {nome_desejado}"
        dispositivo = TvDispositivo(
            tipo="streaming",
            chave=ip_address,
            nome=nome_final,
            orientacao_tv="horizontal",
            rotacao_tv=0,
        )
        db.session.add(dispositivo)
    else:
        # Reconexão pela mesma chave: mantém o nome já cadastrado.
        nome_final = dispositivo.nome or nome_desejado

    dispositivo.tipo = "streaming"
    dispositivo.nome = nome_final
    dispositivo.device_name = device_name
    dispositivo.user_agent = user_agent
    dispositivo.last_seen = datetime.now()
    dispositivo.is_online = True
    if getattr(dispositivo, "rotacao_tv", None) is None:
        _aplicar_rotacao(dispositivo, 0)
    elif not (dispositivo.orientacao_tv or "").strip():
        dispositivo.orientacao_tv = orientacao_de_rotacao(rotacao_do_dispositivo(dispositivo))
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
    nome = (path or "").replace("\\", "/").split("?", 1)[0].split("#", 1)[0].lstrip("/")
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
        if setor_eh_streaming(setor):
            continue
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
                "setor_nome": setor.nome,
                "tipo_setor": setor.tipo_setor or "atendimento",
                "propaganda_ids": propaganda_ids_setor(setor.id),
                "layout_tv_web": setor.layout_tv_web or "propaganda",
                "orientacao_tv": setor.orientacao_tv or "horizontal",
            }
        )
    for dispositivo in streaming:
        payload = dispositivo.to_admin_dict(
            online=esta_online(dispositivo.chave),
            propaganda_ids=propaganda_ids_dispositivo(dispositivo.id),
        )
        tvs.append(payload)
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


def vincular_tv_streaming_ao_setor(dispositivo: TvDispositivo, setor_id: int | None) -> dict:
    """Associa (ou desassocia) uma TV de streaming a um setor, sem quebrar TVs avulsas."""
    if dispositivo.tipo != "streaming":
        raise ValueError("Apenas TVs de streaming podem ser vinculadas a um setor")
    setor = None
    if setor_id is not None:
        setor = db.session.get(Setor, setor_id)
        if not setor:
            raise ValueError("Setor não encontrado")
        dispositivo.setor_id = setor.id
        if not propaganda_ids_dispositivo(dispositivo.id):
            herdados = propaganda_ids_setor(setor.id)
            if herdados:
                substituir_fila_dispositivo(dispositivo, herdados)
                emitir_fila_streaming(dispositivo)
    else:
        dispositivo.setor_id = None
    db.session.commit()
    return dispositivo.to_admin_dict(
        online=esta_online(dispositivo.chave),
        propaganda_ids=propaganda_ids_dispositivo(dispositivo.id),
    )


def definir_rotacao_tv_streaming(dispositivo: TvDispositivo, rotacao) -> dict:
    if dispositivo.tipo != "streaming":
        raise ValueError("Apenas TVs de streaming têm rotação própria")
    # Aceita rotacao_tv numérico ou legado orientacao_tv ("horizontal"/"vertical").
    valor = normalizar_rotacao_tv(rotacao)
    _aplicar_rotacao(dispositivo, valor)
    db.session.commit()
    emitir_fila_streaming(dispositivo)
    return dispositivo.to_admin_dict(
        online=esta_online(dispositivo.chave),
        propaganda_ids=propaganda_ids_dispositivo(dispositivo.id),
    )


def definir_orientacao_tv_streaming(dispositivo: TvDispositivo, orientacao: str) -> dict:
    """Compat: mapeia horizontal→0 / vertical→90."""
    valor = (orientacao or "").strip().lower()
    if valor not in {"horizontal", "vertical"}:
        raise ValueError("orientacao_tv deve ser 'horizontal' ou 'vertical'")
    return definir_rotacao_tv_streaming(dispositivo, rotacao_de_orientacao(valor))


def remover_tv_streaming(dispositivo: TvDispositivo) -> None:
    if dispositivo.tipo != "streaming":
        raise ValueError("Apenas TVs de streaming podem ser removidas por aqui")
    chave = dispositivo.chave
    connected_by_chave.pop(chave, None)
    db.session.execute(
        delete(dispositivo_propagandas).where(dispositivo_propagandas.c.dispositivo_id == dispositivo.id)
    )
    db.session.delete(dispositivo)
    db.session.commit()


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
