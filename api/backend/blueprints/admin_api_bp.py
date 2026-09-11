"""API JSON do painel administrativo (consumida pelo Next.js em `web/`).

Mantém a mesma autenticação por sessão Flask do admin Jinja legado
(`@api_login_required` / cookie `user_id`), sem JWT. Prefixo:
`/api/v1/admin`.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from flask import Blueprint, current_app, jsonify, make_response, request, session
from sqlalchemy import func

from backend.auth import api_login_required
from backend.extensions import db
from backend.models import AtendimentoAtual, Finalizado, Impressora, Operador, Propaganda, Senha, Setor, Usuario
from backend.services.operador_pin_service import OperadorPinError, definir_pin
from backend.services.usuario_service import autenticar
from backend.utils import (
    allowed_file,
    delete_old_image,
    get_configuracao,
    get_ngrok_url,
    process_image,
    process_propaganda_image,
    set_configuracao,
    set_ngrok_url,
)

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/v1/admin")


def _modo_identificacao(valor) -> str:
    modo = (valor or "foto").strip().lower()
    if modo not in {"foto", "pin"}:
        raise ValueError("Modo de identificação deve ser foto ou pin")
    return modo


def _validar_setor_pronto_para_pin(setor: Setor) -> None:
    sem_pin = setor.operadores.filter(
        (Operador.pin_hash.is_(None)) | (Operador.pin_hash == "")
    ).count()
    if sem_pin:
        raise ValueError(
            f"Cadastre o PIN de todos os operadores do setor antes de ativar este modo ({sem_pin} pendente(s))"
        )


def _avaliacao_numerica():
    return func.cast(func.nullif(Finalizado.avaliacao, ""), db.Float)


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
    resp = make_response(
        jsonify(
            {
                "ok": True,
                "user": {
                    "id": usuario.id,
                    "email": usuario.email,
                    "nome_empresa": usuario.nome_empresa or "",
                },
            }
        )
    )
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
    user_id = session.get("user_id")
    usuario = Usuario.query.get(user_id) if user_id else None
    if not usuario:
        return jsonify({"error": "Não autenticado"}), 401
    return jsonify(
        {
            "id": usuario.id,
            "email": usuario.email,
            "nome_empresa": usuario.nome_empresa or get_configuracao("nome_empresa", "") or "",
        }
    )


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

    payload = montar_analytics(
        from_s=request.args.get("from"),
        to_s=request.args.get("to"),
        setor_id=setor_id,
        operador_id=operador_id,
        abandono_minutos=abandono_minutos,
    )
    return jsonify(payload)


@admin_api_bp.route("/dashboard", methods=["GET"])
@api_login_required
def dashboard():
    """Legado — preferir GET /api/v1/admin/analytics."""
    hoje = date.today()
    inicio_dia = datetime(hoje.year, hoje.month, hoje.day)
    fim_dia = inicio_dia + timedelta(days=1)
    inicio_mes = datetime(hoje.year, hoje.month, 1)
    fim_mes = datetime(hoje.year + 1, 1, 1) if hoje.month == 12 else datetime(hoje.year, hoje.month + 1, 1)

    setores = Setor.query.order_by(Setor.nome).all()
    avaliacao_num = _avaliacao_numerica()

    atendimentos_dia = (
        db.session.query(Setor.nome, func.count(Senha.id))
        .join(Senha, Senha.setor_id == Setor.id)
        .filter(Senha.status == "F", Senha.data_hora >= inicio_dia, Senha.data_hora < fim_dia)
        .group_by(Setor.id, Setor.nome)
        .all()
    )
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
    setores = Setor.query.order_by(Setor.nome).all()
    return jsonify(
        [
            {
                "id": s.id,
                "nome": s.nome,
                "descricao": s.descricao or "",
                "senha_setor": s.senha_setor or "",
                "modo_identificacao_operador": s.modo_identificacao_operador or "foto",
                "propagandas_ativas": bool(s.propagandas_ativas),
            }
            for s in setores
        ]
    )


@admin_api_bp.route("/setores", methods=["POST"])
@api_login_required
def create_setor():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome") or "").strip()
    if not nome:
        return jsonify({"error": "Nome é obrigatório"}), 400
    try:
        modo = _modo_identificacao(data.get("modo_identificacao_operador"))
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    setor = Setor(
        nome=nome,
        descricao=(data.get("descricao") or "").strip(),
        senha_setor=(data.get("senha_setor") or "").strip(),
        modo_identificacao_operador=modo,
        propagandas_ativas=bool(data.get("propagandas_ativas", False)),
    )
    db.session.add(setor)
    db.session.commit()
    return jsonify({"id": setor.id, "nome": setor.nome}), 201


@admin_api_bp.route("/setores/<int:setor_id>", methods=["PUT"])
@api_login_required
def update_setor(setor_id: int):
    setor = Setor.query.get_or_404(setor_id)
    data = request.get_json(silent=True) or {}
    if "nome" in data:
        nome = (data.get("nome") or "").strip()
        if not nome:
            return jsonify({"error": "Nome é obrigatório"}), 400
        setor.nome = nome
    if "descricao" in data:
        setor.descricao = (data.get("descricao") or "").strip()
    if "senha_setor" in data:
        setor.senha_setor = (data.get("senha_setor") or "").strip()
    if "modo_identificacao_operador" in data:
        try:
            modo = _modo_identificacao(data.get("modo_identificacao_operador"))
            if modo == "pin":
                _validar_setor_pronto_para_pin(setor)
            setor.modo_identificacao_operador = modo
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
    if "propagandas_ativas" in data:
        setor.propagandas_ativas = bool(data.get("propagandas_ativas"))
    db.session.commit()
    return jsonify(
        {
            "id": setor.id,
            "nome": setor.nome,
            "descricao": setor.descricao,
            "senha_setor": setor.senha_setor,
            "modo_identificacao_operador": setor.modo_identificacao_operador or "foto",
            "propagandas_ativas": bool(setor.propagandas_ativas),
        }
    )


@admin_api_bp.route("/setores/<int:setor_id>", methods=["DELETE"])
@api_login_required
def delete_setor(setor_id: int):
    setor = Setor.query.get_or_404(setor_id)
    db.session.delete(setor)
    db.session.commit()
    return jsonify({"ok": True})


# --- Propagandas (galeria global para TV) ------------------------------------


@admin_api_bp.route("/propagandas", methods=["GET"])
@api_login_required
def list_propagandas():
    itens = Propaganda.query.order_by(Propaganda.ordem.asc(), Propaganda.id.asc()).all()
    return jsonify([p.to_dict() for p in itens])


@admin_api_bp.route("/propagandas", methods=["POST"])
@api_login_required
def create_propaganda():
    file = request.files.get("arquivo") or request.files.get("imagem")
    if not file or not file.filename:
        return jsonify({"error": "Imagem é obrigatória"}), 400
    if not allowed_file(file.filename):
        return jsonify({"error": "Tipo de arquivo não permitido"}), 400
    file.seek(0, 2)
    tamanho = file.tell()
    file.seek(0)
    if tamanho > current_app.config["MAX_FILE_SIZE"]:
        return jsonify({"error": "Arquivo muito grande (máx. 5MB)"}), 400

    filename = process_propaganda_image(file)
    if not filename:
        return jsonify({"error": "Não foi possível processar a imagem"}), 400

    max_ordem = db.session.query(func.max(Propaganda.ordem)).scalar() or 0
    item = Propaganda(arquivo=filename, ordem=max_ordem + 1, ativo=True)
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@admin_api_bp.route("/propagandas/<int:propaganda_id>", methods=["PUT"])
@api_login_required
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
    return jsonify(item.to_dict())


@admin_api_bp.route("/propagandas/<int:propaganda_id>", methods=["DELETE"])
@api_login_required
def delete_propaganda(propaganda_id: int):
    item = Propaganda.query.get_or_404(propaganda_id)
    delete_old_image(item.arquivo)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


# --- Operadores -------------------------------------------------------------


@admin_api_bp.route("/operadores", methods=["GET"])
@api_login_required
def list_operadores():
    rows = (
        db.session.query(Operador, Setor.nome)
        .outerjoin(Setor, Operador.setor_id == Setor.id)
        .order_by(Operador.nome)
        .all()
    )
    return jsonify(
        [
            {
                "id": op.id,
                "nome": op.nome,
                "setor_id": op.setor_id,
                "setor_nome": setor_nome,
                "foto_perfil": op.foto_perfil,
                "tem_pin": bool(op.pin_hash),
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
    setor = Setor.query.get(int(setor_id))
    if not setor:
        return jsonify({"error": "Setor não encontrado"}), 404

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
    nome = (request.form.get("nome") or "").strip()
    setor_id = request.form.get("setor_id")
    if not nome or not setor_id:
        return jsonify({"error": "Nome e setor são obrigatórios"}), 400
    novo_setor = Setor.query.get(int(setor_id))
    if not novo_setor:
        return jsonify({"error": "Setor não encontrado"}), 404

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
    delete_old_image(op.foto_perfil)
    db.session.delete(op)
    db.session.commit()
    return jsonify({"ok": True})


# --- Impressoras ------------------------------------------------------------


@admin_api_bp.route("/impressoras", methods=["GET"])
@api_login_required
def list_impressoras():
    rows = (
        db.session.query(Impressora, Setor.nome)
        .outerjoin(Setor, Impressora.setor_id == Setor.id)
        .order_by(Impressora.nome)
        .all()
    )
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
    porta = int(data.get("porta") or current_app.config["IMPRESSORA_PORTA"])
    imp = Impressora(nome=nome, ip=ip, porta=porta, setor_id=int(setor_id))
    db.session.add(imp)
    db.session.commit()
    return jsonify({"id": imp.id, "nome": imp.nome}), 201


@admin_api_bp.route("/impressoras/<int:impressora_id>", methods=["DELETE"])
@api_login_required
def delete_impressora(impressora_id: int):
    imp = Impressora.query.get_or_404(impressora_id)
    db.session.delete(imp)
    db.session.commit()
    return jsonify({"ok": True})


# --- Configurações ----------------------------------------------------------


@admin_api_bp.route("/configuracao", methods=["GET"])
@api_login_required
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
def put_empresa():
    data = request.get_json(silent=True) or {}
    nome = (data.get("nome_empresa") or "").strip()
    set_configuracao("nome_empresa", nome)
    return jsonify({"ok": True, "nome_empresa": nome})


@admin_api_bp.route("/configuracao/ngrok", methods=["PUT"])
@api_login_required
def put_ngrok():
    data = request.get_json(silent=True) or {}
    url = (data.get("ngrok_url") or "").strip()
    set_ngrok_url(url)
    return jsonify({"ok": True, "ngrok_url": url})


@admin_api_bp.route("/configuracao/fila", methods=["PUT"])
@api_login_required
def put_fila():
    data = request.get_json(silent=True) or {}
    proporcao = str(data.get("proporcao_normais", 2))
    limite = str(data.get("limite_preferenciais_alerta", 3))
    set_configuracao("proporcao_normais", proporcao)
    set_configuracao("limite_preferenciais_alerta", limite)
    return jsonify({"ok": True, "proporcao_normais": proporcao, "limite_preferenciais_alerta": limite})
