"""Painel administrativo: dashboard, CRUD de operadores/impressoras/setores e
configurações do sistema. Lógica de negócio inalterada em relação ao
`app.py` legado — apenas reescrita com SQLAlchemy em vez de `sqlite3` puro."""
from datetime import date

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from sqlalchemy import func

from backend.auth import login_required
from backend.extensions import db
from backend.models import AtendimentoAtual, Finalizado, Impressora, Operador, Senha, Setor
from backend.utils import allowed_file, delete_old_image, get_configuracao, get_ngrok_url, process_image, set_configuracao, set_ngrok_url

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("")
@login_required
def admin():
    operadores = (
        db.session.query(Operador, Setor.nome)
        .outerjoin(Setor, Operador.setor_id == Setor.id)
        .order_by(Operador.nome)
        .all()
    )
    impressoras = (
        db.session.query(Impressora, Setor.nome)
        .outerjoin(Setor, Impressora.setor_id == Setor.id)
        .order_by(Impressora.nome)
        .all()
    )
    setores = Setor.query.order_by(Setor.nome).all()
    ngrok_url = get_ngrok_url()

    hoje = date.today()
    atendimentos_dia = (
        db.session.query(Setor.nome, func.count(Senha.id))
        .join(Senha, Senha.setor_id == Setor.id)
        .filter(Senha.status == "F", func.date(Senha.data_hora) == hoje.isoformat())
        .group_by(Setor.id, Setor.nome)
        .all()
    )
    atendimentos_mes = (
        db.session.query(Setor.nome, func.count(Senha.id))
        .join(Senha, Senha.setor_id == Setor.id)
        .filter(Senha.status == "F", func.strftime("%Y-%m", Senha.data_hora) == hoje.strftime("%Y-%m"))
        .group_by(Setor.id, Setor.nome)
        .all()
    )
    medias_operadores = (
        db.session.query(Operador.nome, func.avg(func.cast(Finalizado.avaliacao, db.Float)), Setor.nome)
        .join(Finalizado, Finalizado.operador_id == Operador.id)
        .outerjoin(Setor, Operador.setor_id == Setor.id)
        .group_by(Operador.id, Operador.nome, Setor.nome)
        .order_by(func.avg(func.cast(Finalizado.avaliacao, db.Float)).desc())
        .all()
    )
    melhor_operador = medias_operadores[0] if medias_operadores else None
    pior_operador = medias_operadores[-1] if medias_operadores else None

    medias_por_setor: dict[int, list] = {}
    for setor in setores:
        medias_por_setor[setor.id] = (
            db.session.query(Operador.nome, func.avg(func.cast(Finalizado.avaliacao, db.Float)))
            .join(Finalizado, Finalizado.operador_id == Operador.id)
            .filter(Operador.setor_id == setor.id)
            .group_by(Operador.id, Operador.nome)
            .order_by(func.avg(func.cast(Finalizado.avaliacao, db.Float)).desc())
            .all()
        )

    atendimentos_mes_operador_por_setor: dict[int, list] = {}
    rows = (
        db.session.query(Setor.id, Operador.nome, func.count(Senha.id))
        .join(Senha, Senha.setor_id == Setor.id)
        .join(AtendimentoAtual, AtendimentoAtual.senha_id == Senha.id)
        .join(Operador, AtendimentoAtual.operador_id == Operador.id)
        .filter(Senha.status == "F", func.strftime("%Y-%m", Senha.data_hora) == hoje.strftime("%Y-%m"))
        .group_by(Setor.id, Operador.id, Operador.nome)
        .order_by(Setor.id, func.count(Senha.id).desc())
        .all()
    )
    for setor_id, operador_nome, total in rows:
        atendimentos_mes_operador_por_setor.setdefault(setor_id, []).append((operador_nome, total))

    return render_template(
        "admin/dashboard.html",
        operadores=operadores,
        impressoras=impressoras,
        setores=setores,
        ngrok_url=ngrok_url,
        atendimentos_dia=atendimentos_dia,
        atendimentos_mes=atendimentos_mes,
        medias_operadores=medias_operadores,
        melhor_operador=melhor_operador,
        pior_operador=pior_operador,
        medias_por_setor=medias_por_setor,
        atendimentos_mes_operador_por_setor=atendimentos_mes_operador_por_setor,
        proporcao_normais=get_configuracao("proporcao_normais", "2"),
        limite_preferenciais_alerta=get_configuracao("limite_preferenciais_alerta", "3"),
    )


# --- Operadores -------------------------------------------------------------

@admin_bp.route("/operador/add", methods=["GET", "POST"])
@login_required
def add_operador():
    if request.method == "POST":
        foto_perfil = None
        file = request.files.get("foto_perfil")
        if file and file.filename:
            if not allowed_file(file.filename):
                return "Tipo de arquivo não permitido. Use: PNG, JPG, JPEG, GIF, WEBP", 400
            file.seek(0, 2)
            tamanho = file.tell()
            file.seek(0)
            if tamanho > current_app.config["MAX_FILE_SIZE"]:
                return "Arquivo muito grande. Tamanho máximo: 5MB", 400
            foto_perfil = process_image(file)

        db.session.add(Operador(nome=request.form["nome"], setor_id=request.form["setor_id"], foto_perfil=foto_perfil))
        db.session.commit()
        return redirect(url_for("admin.admin"))

    setores = Setor.query.order_by(Setor.nome).all()
    return render_template("admin/operador_form.html", setores=setores, operador=None)


@admin_bp.route("/operador/edit/<int:operador_id>", methods=["GET", "POST"])
@login_required
def edit_operador(operador_id):
    operador = Operador.query.get_or_404(operador_id)

    if request.method == "POST":
        operador.nome = request.form["nome"]
        operador.setor_id = request.form["setor_id"]

        file = request.files.get("foto_perfil")
        if file and file.filename:
            if not allowed_file(file.filename):
                return "Tipo de arquivo não permitido. Use: PNG, JPG, JPEG, GIF, WEBP", 400
            file.seek(0, 2)
            tamanho = file.tell()
            file.seek(0)
            if tamanho > current_app.config["MAX_FILE_SIZE"]:
                return "Arquivo muito grande. Tamanho máximo: 5MB", 400
            delete_old_image(operador.foto_perfil)
            operador.foto_perfil = process_image(file)
        elif request.form.get("remover_foto") == "1":
            delete_old_image(operador.foto_perfil)
            operador.foto_perfil = None

        db.session.commit()
        return redirect(url_for("admin.admin"))

    setores = Setor.query.order_by(Setor.nome).all()
    return render_template("admin/operador_form.html", setores=setores, operador=operador)


@admin_bp.route("/operador/delete/<int:operador_id>")
@login_required
def delete_operador(operador_id):
    operador = Operador.query.get_or_404(operador_id)
    delete_old_image(operador.foto_perfil)
    db.session.delete(operador)
    db.session.commit()
    return redirect(url_for("admin.admin"))


# --- Impressoras -------------------------------------------------------------

@admin_bp.route("/impressora/add", methods=["GET", "POST"])
@login_required
def add_impressora():
    if request.method == "POST":
        db.session.add(
            Impressora(
                nome=request.form["nome"],
                ip=request.form["ip"],
                porta=request.form["porta"],
                setor_id=request.form["setor_id"],
            )
        )
        db.session.commit()
        return redirect(url_for("admin.admin"))

    setores = Setor.query.order_by(Setor.nome).all()
    return render_template("admin/impressora_form.html", setores=setores)


@admin_bp.route("/impressora/delete/<int:impressora_id>")
@login_required
def delete_impressora(impressora_id):
    impressora = Impressora.query.get_or_404(impressora_id)
    db.session.delete(impressora)
    db.session.commit()
    return redirect(url_for("admin.admin"))


# --- Setores -----------------------------------------------------------------

@admin_bp.route("/setor/add", methods=["GET", "POST"])
@login_required
def add_setor():
    if request.method == "POST":
        db.session.add(
            Setor(
                nome=request.form["nome"],
                descricao=request.form.get("descricao", ""),
                senha_setor=request.form.get("senha_setor", ""),
            )
        )
        db.session.commit()
        return redirect(url_for("admin.admin"))
    return render_template("admin/setor_form.html", setor=None)


@admin_bp.route("/setor/edit/<int:setor_id>", methods=["GET", "POST"])
@login_required
def edit_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    if request.method == "POST":
        setor.nome = request.form["nome"]
        setor.descricao = request.form.get("descricao", "")
        setor.senha_setor = request.form.get("senha_setor", "")
        db.session.commit()
        return redirect(url_for("admin.admin"))
    return render_template("admin/setor_form.html", setor=setor)


@admin_bp.route("/setor/delete/<int:setor_id>")
@login_required
def delete_setor(setor_id):
    setor = Setor.query.get_or_404(setor_id)
    db.session.delete(setor)
    db.session.commit()
    return redirect(url_for("admin.admin"))


# --- Configurações -----------------------------------------------------------

@admin_bp.route("/configuracao", methods=["GET", "POST"])
@login_required
def configuracao_empresa():
    if request.method == "POST":
        set_configuracao("nome_empresa", request.form["nome_empresa"])
        return redirect(url_for("admin.admin"))
    nome_empresa = get_configuracao("nome_empresa", "")
    return render_template("admin/configuracao_empresa.html", nome_empresa=nome_empresa)


@admin_bp.route("/configuracao/ngrok", methods=["GET", "POST"])
@login_required
def configuracao_ngrok():
    if request.method == "POST":
        set_ngrok_url(request.form.get("ngrok_url", "").strip())
        return redirect(url_for("admin.admin"))
    return render_template("admin/configuracao_ngrok.html", ngrok_url=get_ngrok_url())


@admin_bp.route("/configuracao/fila", methods=["POST"])
@login_required
def configuracao_fila():
    """Persiste os parâmetros de proporção normal/preferencial no banco
    (antes ficavam em cookies do navegador do operador — o que não fazia
    sentido em um sistema com vários dispositivos)."""
    data = request.get_json(silent=True) or request.form
    set_configuracao("proporcao_normais", str(data.get("proporcao_normais", 2)))
    set_configuracao("limite_preferenciais_alerta", str(data.get("limite_preferenciais_alerta", 3)))
    return jsonify({"success": True})
