"""API JSON do painel administrativo (consumida pelo Next.js em `web/`).

Mantém a mesma autenticação por sessão Flask do admin Jinja legado
(`@api_login_required` / cookie `user_id`), sem JWT. Prefixo:
`/api/v1/admin`.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, jsonify, make_response, request, session
from sqlalchemy import func

from backend.auth import api_login_required
from backend.extensions import db
from backend.models import (
    AtendimentoAtual,
    Finalizado,
    Impressora,
    Operador,
    Propaganda,
    Senha,
    Setor,
    TvDispositivo,
    Usuario,
    normalizar_tipo_setor,
    setor_eh_streaming,
    TIPO_SETOR_ATENDIMENTO,
    TIPO_SETOR_STREAMING,
)
from backend.services.streaming_service import atribuir_midias_tv, listar_tvs_admin
from backend.services.admin_access import (
    AdminAccessError,
    assert_setor_permitido,
    filtrar_setor_id,
    is_admin,
    is_marketing,
    query_setores_visiveis,
    require_admin,
    require_admin_ou_marketing,
    restringir_marketing_se_necessario,
    setor_ids_permitidos,
    usuario_atual,
)
from backend.services.operador_pin_service import OperadorPinError, definir_pin
from backend.services.usuario_service import (
    autenticar,
    atualizar_usuario,
    criar_usuario,
)
from backend.utils import (
    allowed_file,
    delete_old_image,
    get_configuracao,
    get_ngrok_url,
    is_video_filename,
    process_image,
    process_propaganda_image,
    save_propaganda_video,
    set_configuracao,
    set_ngrok_url,
)
from backend.services.tv_config_service import (
    ativar_propagandas_nos_setores,
    atribuir_midias_cliente,
    notificar_clientes,
    notificar_tvs,
    propaganda_ids_cliente,
)

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/v1/admin")


@admin_api_bp.before_request
def _restringir_marketing():
    return restringir_marketing_se_necessario()


def _modo_identificacao(valor) -> str:
    modo = (valor or "foto").strip().lower()
    if modo not in {"foto", "pin"}:
        raise ValueError("Modo de identificação deve ser foto ou pin")
    return modo


def _layout_tv_web(valor) -> str:
    layout = (valor or "propaganda").strip().lower()
    if layout not in {"propaganda", "fila"}:
        raise ValueError("Layout da TV web deve ser propaganda ou fila")
    return layout


def _orientacao_tv(valor) -> str:
    orientacao = (valor or "horizontal").strip().lower()
    if orientacao not in {"horizontal", "vertical"}:
        raise ValueError("Orientação da TV deve ser horizontal ou vertical")
    return orientacao


def _validar_setor_pronto_para_pin(setor: Setor) -> None:
    sem_pin = setor.operadores.filter(
        (Operador.pin_hash.is_(None)) | (Operador.pin_hash == "")
    ).count()
    if sem_pin:
        raise ValueError(
            f"Cadastre o PIN de todos os operadores do setor antes de ativar este modo ({sem_pin} pendente(s))"
        )


def _setor_admin_dict(setor: Setor, *, ocultar_senha: bool = False) -> dict:
    return {
        "id": setor.id,
        "nome": setor.nome,
        "descricao": setor.descricao or "",
        "senha_setor": "" if ocultar_senha else (setor.senha_setor or ""),
        "tipo_setor": setor.tipo_setor or TIPO_SETOR_ATENDIMENTO,
        "modo_identificacao_operador": setor.modo_identificacao_operador or "foto",
        "propagandas_ativas": bool(setor.propagandas_ativas),
        "propagandas_cliente_ativas": bool(setor.propagandas_cliente_ativas),
        "impressao_via_cliente": bool(setor.impressao_via_cliente),
        "propaganda_ids_cliente": propaganda_ids_cliente(setor.id),
        "layout_tv_web": setor.layout_tv_web or "propaganda",
        "orientacao_tv": setor.orientacao_tv or "horizontal",
    }


def _assert_setor_atendimento(setor: Setor, acao: str) -> None:
    if setor_eh_streaming(setor):
        raise ValueError(f"Setor de streaming não permite {acao}")


def _validar_conversao_streaming(setor: Setor) -> None:
    if setor.operadores.count():
        raise ValueError("Remova os operadores antes de converter o setor para streaming")
    if setor.impressoras.count():
        raise ValueError("Remova as impressoras antes de converter o setor para streaming")


def _avaliacao_numerica():
    return func.cast(func.nullif(Finalizado.avaliacao, ""), db.Float)


def _access_error_response(exc: AdminAccessError):
    return jsonify({"error": exc.message}), exc.status


def _user_payload(usuario: Usuario) -> dict:
    data = usuario.to_dict()
    data["nome_empresa"] = usuario.nome_empresa or get_configuracao("nome_empresa", "") or ""
    data["is_admin"] = is_admin(usuario)
    data["is_marketing"] = is_marketing(usuario)
    return data


# --- Auth (sessão Flask — opção B do plano) ---------------------------------


@admin_api_bp.route("/login", methods=["POST"])
def login_json():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    senha = data.get("senha") or ""
    if not email or not senha:
        return jsonify({"error": "Email e senha são obrigatórios"}), 400

    usuario = autenticar(email, senha)
    if not usuario:
        return jsonify({"error": "Email ou senha incorretos"}), 401

    session["user_id"] = usuario.id
    session.permanent = True
    resp = make_response(jsonify({"ok": True, "user": _user_payload(usuario)}))
    resp.set_cookie("user_id", str(usuario.id), max_age=60 * 60 * 24 * 365, httponly=True, samesite="Lax")
    resp.set_cookie(
        "nome_empresa",
        usuario.nome_empresa or "",
        max_age=60 * 60 * 24 * 365,
        httponly=False,
        samesite="Lax",
    )
    return resp


@admin_api_bp.route("/logout", methods=["POST"])
def logout_json():
    session.clear()
    resp = make_response(jsonify({"ok": True}))
    resp.set_cookie("user_id", "", expires=0)
    resp.set_cookie("nome_empresa", "", expires=0)
    return resp


@admin_api_bp.route("/me", methods=["GET"])
@api_login_required
def me():
    usuario = usuario_atual()
    if not usuario:
        return jsonify({"error": "Não autenticado"}), 401
    return jsonify(_user_payload(usuario))


# --- Usuários do painel (somente admin) -------------------------------------


@admin_api_bp.route("/usuarios", methods=["GET"])
@api_login_required
@require_admin
def list_usuarios():
    itens = Usuario.query.order_by(Usuario.email.asc()).all()
    return jsonify([u.to_dict() for u in itens])


@admin_api_bp.route("/usuarios", methods=["POST"])
@api_login_required
@require_admin
def create_usuario():
    data = request.get_json(silent=True) or {}
    try:
        usuario = criar_usuario(
            email=data.get("email") or "",
            senha=data.get("senha") or "",
            papel=data.get("papel") or "admin",
            nome=data.get("nome"),
            setor_ids=data.get("setor_ids") or [],
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(usuario.to_dict()), 201


@admin_api_bp.route("/usuarios/<int:usuario_id>", methods=["PUT"])
@api_login_required
@require_admin
def update_usuario(usuario_id: int):
    usuario = Usuario.query.get_or_404(usuario_id)
    data = request.get_json(silent=True) or {}
    try:
        atualizar_usuario(
            usuario,
            email=data.get("email") if "email" in data else None,
            senha=data.get("senha") if data.get("senha") else None,
            papel=data.get("papel") if "papel" in data else None,
            nome=data.get("nome") if "nome" in data else None,
            setor_ids=data.get("setor_ids") if "setor_ids" in data else None,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(usuario.to_dict())


@admin_api_bp.route("/usuarios/<int:usuario_id>", methods=["DELETE"])
@api_login_required
@require_admin
def delete_usuario(usuario_id: int):
    atual = usuario_atual()
    if atual and atual.id == usuario_id:
        return jsonify({"error": "Não é possível remover o próprio usuário"}), 400
    usuario = Usuario.query.get_or_404(usuario_id)
    if is_admin(usuario):
        outros_admins = (
            Usuario.query.filter(Usuario.id != usuario.id)
            .filter(db.func.lower(Usuario.papel) == "admin")
            .count()
        )
        # papel pode ser NULL legado
        if outros_admins == 0:
            total_admins = Usuario.query.filter(
                (Usuario.papel == "admin") | (Usuario.papel.is_(None)) | (Usuario.papel == "")
            ).count()
            if total_admins <= 1:
                return jsonify({"error": "É necessário manter ao menos um administrador"}), 400
    usuario.setores = []
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({"ok": True})


# --- Dashboard / Analytics --------------------------------------------------


@admin_api_bp.route("/analytics", methods=["GET"])
@api_login_required
def analytics():
    from backend.services.analytics_service import montar_analytics

    setor_raw = request.args.get("setor_id")
    op_raw = request.args.get("operador_id")
    abandono_raw = request.args.get("abandono_minutos")
    try:
        setor_id = int(setor_raw) if setor_raw else None
    except ValueError:
        return jsonify({"error": "setor_id inválido"}), 400
    try:
        operador_id = int(op_raw) if op_raw else None
    except ValueError:
        return jsonify({"error": "operador_id inválido"}), 400
    try:
        abandono_minutos = int(abandono_raw) if abandono_raw else None
    except ValueError:
        return jsonify({"error": "abandono_minutos inválido"}), 400

    try:
        setor_id = filtrar_setor_id(setor_id)
        permitidos = setor_ids_permitidos()
    except AdminAccessError as exc:
        return _access_error_response(exc)

    payload = montar_analytics(
        from_s=request.args.get("from"),
        to_s=request.args.get("to"),
        setor_id=setor_id,
        setor_ids=permitidos,
        operador_id=operador_id,
        abandono_minutos=abandono_minutos,
    )
    return jsonify(payload)


@admin_api_bp.route("/fila-ao-vivo", methods=["GET"])
@api_login_required
def fila_ao_vivo():
    """Snapshot operacional por setor (Fila ao Vivo)."""
    from backend.services.live_fila_service import montar_fila_ao_vivo

    setor_raw = request.args.get("setor_id")
    if not setor_raw:
        return jsonify({"error": "setor_id é obrigatório"}), 400
    try:
        setor_id = int(setor_raw)
    except ValueError:
        return jsonify({"error": "setor_id inválido"}), 400
    try:
        assert_setor_permitido(setor_id)
        return jsonify(montar_fila_ao_vivo(setor_id))
    except AdminAccessError as exc:
        return _access_error_response(exc)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 404


@admin_api_bp.route("/fila-ao-vivo/token", methods=["GET"])
@api_login_required
def fila_ao_vivo_token():
    """JWT role=tv para o admin escutar Socket.IO do setor sem polling."""
    from backend.auth import create_session_token

    setor_raw = request.args.get("setor_id")
    if not setor_raw:
        return jsonify({"error": "setor_id é obrigatório"}), 400
    try:
        setor_id = int(setor_raw)
    except ValueError:
        return jsonify({"error": "setor_id inválido"}), 400
    try:
        assert_setor_permitido(setor_id)
    except AdminAccessError as exc:
        return _access_error_response(exc)
    setor = Setor.query.get(setor_id)
    if not setor:
        return jsonify({"error": "Setor não encontrado"}), 404
    if setor_eh_streaming(setor):
        return jsonify({"error": "Setor de streaming não possui fila de atendimento"}), 400
    token = create_session_token(setor_id, role="tv")
    return jsonify({"session_token": token, "setor_id": setor_id})


@admin_api_bp.route("/setores/<int:setor_id>/limpar-fila", methods=["POST"])
@api_login_required
def limpar_fila_setor_route(setor_id: int):
    """Zera senhas aguardando e em atendimento do setor (admin/gerente)."""
    from backend.services.fila_service import FilaError, limpar_fila_setor
    from backend.sockets.emitters import broadcast_posicao_fila, emit_fila_atualizada

    try:
        assert_setor_permitido(setor_id)
        resultado = limpar_fila_setor(setor_id)
    except AdminAccessError as exc:
        return _access_error_response(exc)
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 400

    emit_fila_atualizada(setor_id)
    broadcast_posicao_fila(setor_id)
    return jsonify({"ok": True, **resultado})


@admin_api_bp.route("/fila-ao-vivo/config", methods=["PUT"])
@api_login_required
@require_admin
def fila_ao_vivo_config():
    data = request.get_json(silent=True) or {}
    if "ignorar_finalizados_automaticos" in data:
        set_configuracao(
            "ignorar_finalizados_automaticos",
            "1" if data.get("ignorar_finalizados_automaticos") else "0",
        )
    return jsonify(
        {
            "ignorar_finalizados_automaticos": (get_configuracao("ignorar_finalizados_automaticos") or "0")
            in ("1", "true", "True", "yes")
        }
    )


@admin_api_bp.route("/dashboard", methods=["GET"])
@api_login_required
def dashboard():
    """Legado — preferir GET /api/v1/admin/analytics."""
    hoje = date.today()
    inicio_dia = datetime(hoje.year, hoje.month, hoje.day)
    fim_dia = inicio_dia + timedelta(days=1)
    inicio_mes = datetime(hoje.year, hoje.month, 1)
    fim_mes = datetime(hoje.year + 1, 1, 1) if hoje.month == 12 else datetime(hoje.year, hoje.month + 1, 1)

    setores = [s for s in query_setores_visiveis().all() if not setor_eh_streaming(s)]
    avaliacao_num = _avaliacao_numerica()
    setor_ids = [s.id for s in setores]

    atendimentos_dia = (
        db.session.query(Setor.nome, func.count(Senha.id))
        .join(Senha, Senha.setor_id == Setor.id)
        .filter(Senha.status == "F", Senha.data_hora >= inicio_dia, Senha.data_hora < fim_dia)
        .group_by(Setor.id, Setor.nome)
        .all()
    )
    if setor_ids:
        atendimentos_dia = [(n, t) for n, t in atendimentos_dia if any(s.nome == n for s in setores)]
    else:
        atendimentos_dia = []
    atendimentos_mes = (
        db.session.query(Setor.nome, func.count(Senha.id))
        .join(Senha, Senha.setor_id == Setor.id)
        .filter(Senha.status == "F", Senha.data_hora >= inicio_mes, Senha.data_hora < fim_mes)
        .group_by(Setor.id, Setor.nome)
        .all()
    )
    medias_operadores = (
        db.session.query(Operador.nome, func.avg(avaliacao_num), Setor.nome)
        .join(Finalizado, Finalizado.operador_id == Operador.id)
        .outerjoin(Setor, Operador.setor_id == Setor.id)
        .group_by(Operador.id, Operador.nome, Setor.nome)
        .order_by(func.avg(avaliacao_num).desc())
        .all()
    )

    medias_por_setor: dict[str, list] = {}
    for setor in setores:
        rows = (
            db.session.query(Operador.nome, func.avg(avaliacao_num))
            .join(Finalizado, Finalizado.operador_id == Operador.id)
            .filter(Operador.setor_id == setor.id)
            .group_by(Operador.id, Operador.nome)
            .order_by(func.avg(avaliacao_num).desc())
            .all()
        )
        medias_por_setor[str(setor.id)] = [
            {"operador": nome, "media": float(media) if media is not None else None}
            for nome, media in rows
        ]

    atendimentos_mes_operador_por_setor: dict[str, list] = {}
    rows_op = (
        db.session.query(Setor.id, Operador.nome, func.count(Senha.id))
        .join(Senha, Senha.setor_id == Setor.id)
        .join(AtendimentoAtual, AtendimentoAtual.senha_id == Senha.id)
        .join(Operador, AtendimentoAtual.operador_id == Operador.id)
        .filter(Senha.status == "F", Senha.data_hora >= inicio_mes, Senha.data_hora < fim_mes)
        .group_by(Setor.id, Operador.id, Operador.nome)
        .order_by(Setor.id, func.count(Senha.id).desc())
        .all()
    )
    for setor_id, operador_nome, total in rows_op:
        atendimentos_mes_operador_por_setor.setdefault(str(setor_id), []).append(
            {"operador": operador_nome, "total": total}
        )

    melhor = medias_operadores[0] if medias_operadores else None
    pior = medias_operadores[-1] if medias_operadores else None

    return jsonify(
        {
            "atendimentos_dia": [{"setor": n, "total": t} for n, t in atendimentos_dia],
            "atendimentos_mes": [{"setor": n, "total": t} for n, t in atendimentos_mes],
            "medias_operadores": [
                {
                    "operador": nome,
                    "media": float(media) if media is not None else None,
                    "setor": setor_nome,
                }
                for nome, media, setor_nome in medias_operadores
            ],
            "melhor_operador": (
                {
                    "operador": melhor[0],
                    "media": float(melhor[1]) if melhor[1] is not None else None,
                    "setor": melhor[2],
                }
                if melhor
                else None
            ),
            "pior_operador": (
                {
                    "operador": pior[0],
                    "media": float(pior[1]) if pior[1] is not None else None,
                    "setor": pior[2],
                }
                if pior
                else None
            ),
            "medias_por_setor": medias_por_setor,
            "atendimentos_mes_operador_por_setor": atendimentos_mes_operador_por_setor,
            "setores": [{"id": s.id, "nome": s.nome} for s in setores],
            "proporcao_normais": get_configuracao("proporcao_normais", "2"),
            "limite_preferenciais_alerta": get_configuracao("limite_preferenciais_alerta", "3"),
            "ngrok_url": get_ngrok_url(),
            "nome_empresa": get_configuracao("nome_empresa", "") or "",
        }
    )


# --- Setores ----------------------------------------------------------------


@admin_api_bp.route("/setores", methods=["GET"])
@api_login_required
def list_setores():
    setores = query_setores_visiveis().all()
    ocultar_senha = is_marketing()
    return jsonify([_setor_admin_dict(s, ocultar_senha=ocultar_senha) for s in setores])


@admin_api_bp.route("/setores", methods=["POST"])
@api_login_required
@require_admin
def create_setor():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Nome é obrigatório"}), 400
    try:
        tipo_setor = normalizar_tipo_setor(data.get("tipo_setor"))
        modo = _modo_identificacao(data.get("modo_identificacao_operador"))
        layout_tv_web = _layout_tv_web(data.get("layout_tv_web"))
        orientacao_tv = _orientacao_tv(data.get("orientacao_tv"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if tipo_setor == TIPO_SETOR_STREAMING:
        modo = "foto"
        layout_tv_web = "propaganda"
        senha_setor = ""
        cliente_ativas = False
    else:
        senha_setor = (data.get("senha_setor") or "").strip()
        cliente_ativas = bool(data.get("propagandas_cliente_ativas", False))
    setor = Setor(
        nome=nome,
        descricao=(data.get("descricao") or "").strip(),
        senha_setor=senha_setor,
        tipo_setor=tipo_setor,
        modo_identificacao_operador=modo,
        propagandas_ativas=bool(data.get("propagandas_ativas", False)),
        propagandas_cliente_ativas=cliente_ativas,
        impressao_via_cliente=False if tipo_setor == TIPO_SETOR_STREAMING else bool(
            data.get("impressao_via_cliente", False)
        ),
        layout_tv_web=layout_tv_web,
        orientacao_tv=orientacao_tv,
    )
    db.session.add(setor)
    db.session.commit()
    return jsonify(_setor_admin_dict(setor)), 201


@admin_api_bp.route("/setores/<int:setor_id>", methods=["PUT"])
@api_login_required
def update_setor(setor_id: int):
    setor = Setor.query.get_or_404(setor_id)
    try:
        assert_setor_permitido(setor_id)
    except AdminAccessError as exc:
        return _access_error_response(exc)
    data = request.get_json(silent=True) or {}
    # Gerente só altera flags operacionais; admin altera tudo.
    admin = is_admin()
    if not admin:
        allowed = {
            "propagandas_ativas",
            "propagandas_cliente_ativas",
            "impressao_via_cliente",
            "layout_tv_web",
            "orientacao_tv",
            "modo_identificacao_operador",
        }
        data = {k: v for k, v in data.items() if k in allowed}
    if "nome" in data:
        nome = (data.get("nome") or "").strip()
        if not nome:
            return jsonify({"error": "Nome é obrigatório"}), 400
        setor.nome = nome
    if "descricao" in data:
        setor.descricao = (data.get("descricao") or "").strip()
    if "senha_setor" in data and not setor_eh_streaming(setor):
        setor.senha_setor = (data.get("senha_setor") or "").strip()
    if "tipo_setor" in data:
        try:
            tipo_setor = normalizar_tipo_setor(data.get("tipo_setor"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        if tipo_setor == TIPO_SETOR_STREAMING and not setor_eh_streaming(setor):
            try:
                _validar_conversao_streaming(setor)
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
            setor.senha_setor = ""
            setor.layout_tv_web = "propaganda"
            setor.modo_identificacao_operador = "foto"
            setor.propagandas_cliente_ativas = False
            setor.impressao_via_cliente = False
        setor.tipo_setor = tipo_setor
    if "modo_identificacao_operador" in data and not setor_eh_streaming(setor):
        try:
            modo = _modo_identificacao(data.get("modo_identificacao_operador"))
            if modo == "pin":
                _validar_setor_pronto_para_pin(setor)
            setor.modo_identificacao_operador = modo
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    if "propagandas_ativas" in data:
        setor.propagandas_ativas = bool(data.get("propagandas_ativas"))
    if "propagandas_cliente_ativas" in data and not setor_eh_streaming(setor):
        setor.propagandas_cliente_ativas = bool(data.get("propagandas_cliente_ativas"))
    if "impressao_via_cliente" in data and not setor_eh_streaming(setor):
        setor.impressao_via_cliente = bool(data.get("impressao_via_cliente"))
    if "layout_tv_web" in data and not setor_eh_streaming(setor):
        try:
            setor.layout_tv_web = _layout_tv_web(data.get("layout_tv_web"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    if "orientacao_tv" in data:
        try:
            setor.orientacao_tv = _orientacao_tv(data.get("orientacao_tv"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    db.session.commit()
    notificar_tvs([setor.id])
    notificar_clientes([setor.id])
    return jsonify(_setor_admin_dict(setor))


@admin_api_bp.route("/setores/<int:setor_id>", methods=["DELETE"])
@api_login_required
@require_admin
def delete_setor(setor_id: int):
    setor = Setor.query.get_or_404(setor_id)
    db.session.delete(setor)
    db.session.commit()
    return jsonify({"ok": True})


# --- Propagandas (galeria global para TV) ------------------------------------


def _parse_setor_ids(raw) -> tuple[list[int] | None, str | None]:
    if raw is None or raw == "":
        return [], None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (TypeError, ValueError):
            return None, "setor_ids inválido"
    if not isinstance(raw, list):
        return None, "setor_ids deve ser uma lista"
    try:
        return sorted({int(setor_id) for setor_id in raw}), None
    except (TypeError, ValueError):
        return None, "IDs de setores inválidos"


def _vincular_propagandas(propagandas: list[Propaganda], setores: list[Setor]) -> list[int]:
    ids_antes: set[int] = set()
    for propaganda in propagandas:
        ids_antes.update(setor.id for setor in propaganda.setores)
        propaganda.setores = setores
    if setores:
        ativar_propagandas_nos_setores(setores)
    return sorted(ids_antes | {setor.id for setor in setores})


def _arquivos_midia_do_request():
    arquivos = []
    for chave in ("arquivos", "arquivo", "imagem"):
        for stored in request.files.getlist(chave):
            if stored and stored.filename:
                arquivos.append(stored)
    vistos: set[int] = set()
    unicos = []
    for stored in arquivos:
        chave = id(stored)
        if chave in vistos:
            continue
        vistos.add(chave)
        unicos.append(stored)
    return unicos


def _processar_arquivo_midia(file, *, prefixo: str = "") -> tuple[str | None, str | None, str | None]:
    nome = file.filename or "arquivo"
    is_video = is_video_filename(nome)
    if not is_video and not allowed_file(nome):
        return None, None, f"{prefixo}Tipo de arquivo não permitido (imagem ou MP4)"

    file.seek(0, 2)
    tamanho = file.tell()
    file.seek(0)
    max_size = current_app.config["MAX_VIDEO_SIZE"] if is_video else current_app.config["MAX_FILE_SIZE"]
    limite_label = "80MB" if is_video else "5MB"
    if tamanho > max_size:
        return None, None, f"{prefixo}Arquivo muito grande (máx. {limite_label})"

    if is_video:
        filename = save_propaganda_video(file)
        if not filename:
            return None, None, f"{prefixo}Não foi possível salvar o vídeo"
        return filename, "video", None

    filename = process_propaganda_image(file)
    if not filename:
        return None, None, f"{prefixo}Não foi possível processar a imagem"
    return filename, "image", None


@admin_api_bp.route("/propagandas", methods=["GET"])
@api_login_required
def list_propagandas():
    itens = Propaganda.query.order_by(Propaganda.ordem.asc(), Propaganda.id.asc()).all()
    return jsonify([p.to_dict() for p in itens])


@admin_api_bp.route("/propagandas", methods=["POST"])
@api_login_required
@require_admin_ou_marketing
def create_propaganda():
    arquivos = _arquivos_midia_do_request()
    if not arquivos:
        return jsonify({"error": "Arquivo é obrigatório"}), 400

    setor_ids, setor_error = _parse_setor_ids(request.form.get("setor_ids"))
    if setor_error:
        return jsonify({"error": setor_error}), 400

    setores = Setor.query.filter(Setor.id.in_(setor_ids)).all() if setor_ids else []
    if setor_ids and len(setores) != len(setor_ids):
        return jsonify({"error": "Um ou mais setores não foram encontrados"}), 404

    lote = len(arquivos) > 1
    processados: list[tuple[str, str]] = []
    for file in arquivos:
        prefixo = f"{file.filename}: " if lote else ""
        filename, tipo, erro = _processar_arquivo_midia(file, prefixo=prefixo)
        if erro or not filename or not tipo:
            return jsonify({"error": erro or "Não foi possível salvar o arquivo"}), 400
        processados.append((filename, tipo))

    max_ordem = db.session.query(func.max(Propaganda.ordem)).scalar() or 0
    itens: list[Propaganda] = []
    for index, (filename, tipo) in enumerate(processados, start=1):
        item = Propaganda(arquivo=filename, tipo=tipo, ordem=max_ordem + index, ativo=True)
        itens.append(item)

    if setores:
        _vincular_propagandas(itens, setores)
    db.session.add_all(itens)
    db.session.commit()
    if setores:
        notificar_tvs([setor.id for setor in setores])

    if len(itens) == 1:
        return jsonify(itens[0].to_dict()), 201
    return jsonify({"itens": [item.to_dict() for item in itens], "criadas": len(itens)}), 201


@admin_api_bp.route("/propagandas/setores", methods=["PUT"])
@api_login_required
@require_admin_ou_marketing
def update_propagandas_setores():
    data = request.get_json(silent=True) or {}
    propaganda_ids = data.get("propaganda_ids")
    setor_ids, setor_error = _parse_setor_ids(data.get("setor_ids"))
    if not isinstance(propaganda_ids, list) or not propaganda_ids:
        return jsonify({"error": "Selecione ao menos uma mídia"}), 400
    if setor_error:
        return jsonify({"error": setor_error}), 400

    try:
        propaganda_ids = sorted({int(item_id) for item_id in propaganda_ids})
    except (TypeError, ValueError):
        return jsonify({"error": "IDs de mídias inválidos"}), 400

    propagandas = Propaganda.query.filter(Propaganda.id.in_(propaganda_ids)).all()
    setores = Setor.query.filter(Setor.id.in_(setor_ids)).all() if setor_ids else []
    if len(propagandas) != len(propaganda_ids):
        return jsonify({"error": "Uma ou mais mídias não foram encontradas"}), 404
    if setor_ids and len(setores) != len(setor_ids):
        return jsonify({"error": "Um ou mais setores não foram encontrados"}), 404

    afetados = _vincular_propagandas(propagandas, setores)
    db.session.commit()
    notificar_tvs(afetados)
    return jsonify(
        {
            "atualizadas": len(propagandas),
            "setor_ids": setor_ids,
        }
    )


@admin_api_bp.route("/propagandas/cliente", methods=["PUT"])
@api_login_required
@require_admin_ou_marketing
def update_propagandas_cliente():
    data = request.get_json(silent=True) or {}
    try:
        setor_id = int(data.get("setor_id"))
        propaganda_ids = [int(item_id) for item_id in (data.get("propaganda_ids") or [])]
    except (TypeError, ValueError):
        return jsonify({"error": "IDs inválidos"}), 400
    ativas = data.get("ativas")
    try:
        assert_setor_permitido(setor_id)
        result = atribuir_midias_cliente(
            setor_id,
            propaganda_ids,
            ativas=bool(ativas) if ativas is not None else None,
        )
    except AdminAccessError as exc:
        return _access_error_response(exc)
    except ValueError as exc:
        status = 404 if "não encontrad" in str(exc) else 400
        return jsonify({"error": str(exc)}), status
    return jsonify(result)


@admin_api_bp.route("/propagandas/<int:propaganda_id>", methods=["PUT"])
@api_login_required
@require_admin_ou_marketing
def update_propaganda(propaganda_id: int):
    item = Propaganda.query.get_or_404(propaganda_id)
    data = request.get_json(silent=True) or {}
    if "ordem" in data:
        try:
            item.ordem = int(data.get("ordem"))
        except (TypeError, ValueError):
            return jsonify({"error": "ordem inválida"}), 400
    if "ativo" in data:
        item.ativo = bool(data.get("ativo"))
    db.session.commit()
    notificar_tvs([setor.id for setor in item.setores])
    notificar_clientes([setor.id for setor in item.setores_cliente])
    return jsonify(item.to_dict())


@admin_api_bp.route("/propagandas/<int:propaganda_id>", methods=["DELETE"])
@api_login_required
@require_admin_ou_marketing
def delete_propaganda(propaganda_id: int):
    item = Propaganda.query.get_or_404(propaganda_id)
    setor_ids = [setor.id for setor in item.setores]
    setor_ids_cliente = [setor.id for setor in item.setores_cliente]
    delete_old_image(item.arquivo)
    db.session.delete(item)
    db.session.commit()
    notificar_tvs(setor_ids)
    notificar_clientes(setor_ids_cliente)
    return jsonify({"ok": True})


@admin_api_bp.route("/tvs", methods=["GET"])
@api_login_required
def list_tvs():
    return jsonify(listar_tvs_admin())


@admin_api_bp.route("/tvs/midias", methods=["PUT"])
@api_login_required
@require_admin_ou_marketing
def update_tv_midias():
    data = request.get_json(silent=True) or {}
    tipo = (data.get("tipo") or "").strip().lower()
    if tipo not in {"setor", "streaming"}:
        return jsonify({"error": "tipo deve ser setor ou streaming"}), 400
    try:
        alvo_id = int(data.get("id"))
        propaganda_ids = [int(item_id) for item_id in (data.get("propaganda_ids") or [])]
    except (TypeError, ValueError):
        return jsonify({"error": "IDs inválidos"}), 400
    try:
        result = atribuir_midias_tv(tipo=tipo, alvo_id=alvo_id, propaganda_ids=propaganda_ids)
    except ValueError as exc:
        status = 404 if "não encontrad" in str(exc) else 400
        return jsonify({"error": str(exc)}), status
    return jsonify(result)


@admin_api_bp.route("/tvs/<int:dispositivo_id>/setor", methods=["PUT"])
@api_login_required
@require_admin
def update_tv_setor(dispositivo_id: int):
    from backend.services.streaming_service import vincular_tv_streaming_ao_setor

    data = request.get_json(silent=True) or {}
    setor_id = data.get("setor_id")
    if setor_id in ("", None):
        setor_id = None
    else:
        try:
            setor_id = int(setor_id)
        except (TypeError, ValueError):
            return jsonify({"error": "setor_id inválido"}), 400
    dispositivo = db.session.get(TvDispositivo, dispositivo_id)
    if not dispositivo or dispositivo.tipo != "streaming":
        return jsonify({"error": "TV de streaming não encontrada"}), 404
    try:
        result = vincular_tv_streaming_ao_setor(dispositivo, setor_id)
    except ValueError as exc:
        status = 404 if "não encontrad" in str(exc) else 400
        return jsonify({"error": str(exc)}), status
    return jsonify(result)


@admin_api_bp.route("/tvs/<int:dispositivo_id>/orientacao", methods=["PUT"])
@admin_api_bp.route("/tvs/<int:dispositivo_id>/rotacao", methods=["PUT"])
@api_login_required
@require_admin_ou_marketing
def update_tv_rotacao(dispositivo_id: int):
    from backend.services.streaming_service import definir_rotacao_tv_streaming

    data = request.get_json(silent=True) or {}
    dispositivo = db.session.get(TvDispositivo, dispositivo_id)
    if not dispositivo or dispositivo.tipo != "streaming":
        return jsonify({"error": "TV de streaming não encontrada"}), 404
    # Preferir rotacao_tv; aceitar orientacao_tv legado (horizontal/vertical).
    valor = data.get("rotacao_tv", data.get("orientacao_tv"))
    try:
        result = definir_rotacao_tv_streaming(dispositivo, valor)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@admin_api_bp.route("/tvs/<int:dispositivo_id>/preview", methods=["POST"])
@api_login_required
@require_admin_ou_marketing
def preview_tv_streaming(dispositivo_id: int):
    from backend.services.streaming_service import emitir_preview_streaming

    data = request.get_json(silent=True) or {}
    dispositivo = db.session.get(TvDispositivo, dispositivo_id)
    if not dispositivo or dispositivo.tipo != "streaming":
        return jsonify({"error": "TV de streaming não encontrada"}), 404
    propaganda_id = data.get("propaganda_id")
    if propaganda_id in ("", None):
        propaganda_id = None
    else:
        try:
            propaganda_id = int(propaganda_id)
        except (TypeError, ValueError):
            return jsonify({"error": "propaganda_id inválido"}), 400
    try:
        payload = emitir_preview_streaming(
            dispositivo,
            propaganda_id=propaganda_id,
            duration_ms=data.get("duration_ms"),
        )
    except ValueError as exc:
        status = 404 if "não encontrad" in str(exc).lower() else 400
        return jsonify({"error": str(exc)}), status
    return jsonify({"ok": True, **payload})


@admin_api_bp.route("/tvs/<int:dispositivo_id>", methods=["DELETE"])
@api_login_required
@require_admin_ou_marketing
def delete_tv_streaming(dispositivo_id: int):
    from backend.services.streaming_service import remover_tv_streaming

    dispositivo = db.session.get(TvDispositivo, dispositivo_id)
    if not dispositivo or dispositivo.tipo != "streaming":
        return jsonify({"error": "TV de streaming não encontrada"}), 404
    try:
        remover_tv_streaming(dispositivo)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"ok": True})


# --- Operadores -------------------------------------------------------------


@admin_api_bp.route("/operadores", methods=["GET"])
@api_login_required
def list_operadores():
    q = (
        db.session.query(Operador, Setor.nome)
        .outerjoin(Setor, Operador.setor_id == Setor.id)
        .order_by(Operador.nome)
    )
    try:
        permitidos = setor_ids_permitidos()
    except AdminAccessError as exc:
        return _access_error_response(exc)
    if permitidos is not None:
        if not permitidos:
            q = q.filter(False)
        else:
            q = q.filter(Operador.setor_id.in_(permitidos))
    rows = q.all()
    avaliacao_num = _avaliacao_numerica()
    medias = {
        oid: (float(media) if media is not None else None, int(n or 0))
        for oid, media, n in (
            db.session.query(
                Finalizado.operador_id,
                func.avg(avaliacao_num),
                func.count(avaliacao_num),
            )
            .filter(Finalizado.avaliacao.isnot(None), Finalizado.avaliacao != "")
            .group_by(Finalizado.operador_id)
            .all()
        )
    }
    return jsonify(
        [
            {
                "id": op.id,
                "nome": op.nome,
                "setor_id": op.setor_id,
                "setor_nome": setor_nome,
                "foto_perfil": op.foto_perfil,
                "tem_pin": bool(op.pin_hash),
                "nota_media": (
                    round(medias[op.id][0], 2)
                    if op.id in medias and medias[op.id][0] is not None
                    else None
                ),
                "n_avaliacoes": medias[op.id][1] if op.id in medias else 0,
            }
            for op, setor_nome in rows
        ]
    )


@admin_api_bp.route("/operadores", methods=["POST"])
@api_login_required
def create_operador():
    nome = (request.form.get("nome") or "").strip()
    setor_id = request.form.get("setor_id")
    if not nome or not setor_id:
        return jsonify({"error": "Nome e setor são obrigatórios"}), 400
    try:
        assert_setor_permitido(int(setor_id))
    except AdminAccessError as exc:
        return _access_error_response(exc)
    setor = Setor.query.get(int(setor_id))
    if not setor:
        return jsonify({"error": "Setor não encontrado"}), 404
    try:
        _assert_setor_atendimento(setor, "cadastro de operadores")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    foto_perfil = None
    file = request.files.get("foto_perfil")
    if file and file.filename:
        if not allowed_file(file.filename):
            return jsonify({"error": "Tipo de arquivo não permitido"}), 400
        file.seek(0, 2)
        tamanho = file.tell()
        file.seek(0)
        if tamanho > current_app.config["MAX_FILE_SIZE"]:
            return jsonify({"error": "Arquivo muito grande (máx. 5MB)"}), 400
        foto_perfil = process_image(file)

    op = Operador(nome=nome, setor_id=int(setor_id), foto_perfil=foto_perfil)
    pin = (request.form.get("pin") or "").strip()
    try:
        if pin:
            definir_pin(op, pin, int(setor_id))
        elif setor.modo_identificacao_operador == "pin":
            return jsonify({"error": "PIN é obrigatório para operadores deste setor"}), 400
        db.session.add(op)
        db.session.commit()
    except OperadorPinError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400
    return jsonify({"id": op.id, "nome": op.nome}), 201


@admin_api_bp.route("/operadores/<int:operador_id>", methods=["PUT"])
@api_login_required
def update_operador(operador_id: int):
    op = Operador.query.get_or_404(operador_id)
    try:
        if op.setor_id:
            assert_setor_permitido(op.setor_id)
    except AdminAccessError as exc:
        return _access_error_response(exc)
    nome = (request.form.get("nome") or "").strip()
    setor_id = request.form.get("setor_id")
    if not nome or not setor_id:
        return jsonify({"error": "Nome e setor são obrigatórios"}), 400
    try:
        assert_setor_permitido(int(setor_id))
    except AdminAccessError as exc:
        return _access_error_response(exc)
    novo_setor = Setor.query.get(int(setor_id))
    if not novo_setor:
        return jsonify({"error": "Setor não encontrado"}), 404
    try:
        _assert_setor_atendimento(novo_setor, "cadastro de operadores")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    setor_anterior_id = op.setor_id
    op.nome = nome
    op.setor_id = int(setor_id)

    pin = (request.form.get("pin") or "").strip()
    try:
        if pin:
            definir_pin(op, pin, int(setor_id))
        elif setor_anterior_id != int(setor_id) and op.pin_hash:
            return jsonify({"error": "Informe um novo PIN ao mover o operador para este setor"}), 400
        elif novo_setor.modo_identificacao_operador == "pin" and not op.pin_hash:
            return jsonify({"error": "PIN é obrigatório para operadores deste setor"}), 400
    except OperadorPinError as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400

    if request.form.get("remover_foto") == "1":
        delete_old_image(op.foto_perfil)
        op.foto_perfil = None

    file = request.files.get("foto_perfil")
    if file and file.filename:
        if not allowed_file(file.filename):
            return jsonify({"error": "Tipo de arquivo não permitido"}), 400
        file.seek(0, 2)
        tamanho = file.tell()
        file.seek(0)
        if tamanho > current_app.config["MAX_FILE_SIZE"]:
            return jsonify({"error": "Arquivo muito grande (máx. 5MB)"}), 400
        delete_old_image(op.foto_perfil)
        op.foto_perfil = process_image(file)

    db.session.commit()
    return jsonify({"id": op.id, "nome": op.nome})


@admin_api_bp.route("/operadores/<int:operador_id>", methods=["DELETE"])
@api_login_required
def delete_operador(operador_id: int):
    op = Operador.query.get_or_404(operador_id)
    try:
        if op.setor_id:
            assert_setor_permitido(op.setor_id)
    except AdminAccessError as exc:
        return _access_error_response(exc)
    delete_old_image(op.foto_perfil)
    db.session.delete(op)
    db.session.commit()
    return jsonify({"ok": True})


# --- Impressoras ------------------------------------------------------------


@admin_api_bp.route("/impressoras", methods=["GET"])
@api_login_required
def list_impressoras():
    q = (
        db.session.query(Impressora, Setor.nome)
        .outerjoin(Setor, Impressora.setor_id == Setor.id)
        .order_by(Impressora.nome)
    )
    try:
        permitidos = setor_ids_permitidos()
    except AdminAccessError as exc:
        return _access_error_response(exc)
    if permitidos is not None:
        if not permitidos:
            q = q.filter(False)
        else:
            q = q.filter(Impressora.setor_id.in_(permitidos))
    rows = q.all()
    return jsonify(
        [
            {
                "id": imp.id,
                "nome": imp.nome,
                "ip": imp.ip,
                "porta": imp.porta,
                "setor_id": imp.setor_id,
                "setor_nome": setor_nome,
            }
            for imp, setor_nome in rows
        ]
    )


@admin_api_bp.route("/impressoras", methods=["POST"])
@api_login_required
def create_impressora():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    ip = (data.get("ip") or "").strip()
    setor_id = data.get("setor_id")
    if not nome or not ip or not setor_id:
        return jsonify({"error": "Nome, IP e setor são obrigatórios"}), 400
    try:
        assert_setor_permitido(int(setor_id))
    except AdminAccessError as exc:
        return _access_error_response(exc)
    setor = Setor.query.get(int(setor_id))
    if not setor:
        return jsonify({"error": "Setor não encontrado"}), 404
    try:
        _assert_setor_atendimento(setor, "cadastro de impressoras")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    porta = int(data.get("porta") or current_app.config["IMPRESSORA_PORTA"])
    imp = Impressora(nome=nome, ip=ip, porta=porta, setor_id=int(setor_id))
    db.session.add(imp)
    db.session.commit()
    return jsonify({"id": imp.id, "nome": imp.nome}), 201


@admin_api_bp.route("/impressoras/<int:impressora_id>", methods=["DELETE"])
@api_login_required
def delete_impressora(impressora_id: int):
    imp = Impressora.query.get_or_404(impressora_id)
    try:
        if imp.setor_id:
            assert_setor_permitido(imp.setor_id)
    except AdminAccessError as exc:
        return _access_error_response(exc)
    db.session.delete(imp)
    db.session.commit()
    return jsonify({"ok": True})


# --- Configurações ----------------------------------------------------------


@admin_api_bp.route("/configuracao", methods=["GET"])
@api_login_required
@require_admin
def get_config():
    return jsonify(
        {
            "nome_empresa": get_configuracao("nome_empresa", "") or "",
            "ngrok_url": get_ngrok_url(),
            "proporcao_normais": get_configuracao("proporcao_normais", "2"),
            "limite_preferenciais_alerta": get_configuracao("limite_preferenciais_alerta", "3"),
        }
    )


@admin_api_bp.route("/configuracao/empresa", methods=["PUT"])
@api_login_required
@require_admin
def put_empresa():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome_empresa") or "").strip()
    set_configuracao("nome_empresa", nome)
    return jsonify({"ok": True, "nome_empresa": nome})


@admin_api_bp.route("/configuracao/ngrok", methods=["PUT"])
@api_login_required
@require_admin
def put_ngrok():
    data = request.get_json(silent=True) or {}
    url = (data.get("ngrok_url") or "").strip()
    set_ngrok_url(url)
    return jsonify({"ok": True, "ngrok_url": url})


@admin_api_bp.route("/configuracao/fila", methods=["PUT"])
@api_login_required
@require_admin
def put_fila():
    data = request.get_json(silent=True) or {}
    proporcao = str(data.get("proporcao_normais", 2))
    limite = str(data.get("limite_preferenciais_alerta", 3))
    set_configuracao("proporcao_normais", proporcao)
    set_configuracao("limite_preferenciais_alerta", limite)
    return jsonify({"ok": True, "proporcao_normais": proporcao, "limite_preferenciais_alerta": limite})
