"""Página pública de acompanhamento de senha (QR Code) + Web Push.

A UI do cliente vive no Next (`/acompanhar/<token>`). Este blueprint mantém
as APIs públicas e redireciona a rota legada `/notificacao/<token>`.
"""
import json

from flask import Blueprint, jsonify, redirect, request

from backend.extensions import db
from backend.models import Senha
from backend.services.avaliacao_service import AvaliacaoError, registrar_avaliacao_por_token
from backend.services.fila_service import FilaError, salvar_pedido, verificar_senha
from backend.services.push_service import enviar_web_push, get_vapid_public_key
from backend.utils import get_notification_url

notificacao_bp = Blueprint("notificacao", __name__)


@notificacao_bp.route("/notificacao/<token>")
def notificacao(token):
    if not Senha.query.filter_by(token_unico=token).first():
        return "Senha não encontrada", 404
    return redirect(get_notification_url(token), code=302)


@notificacao_bp.route("/api/vapid-public-key", methods=["GET"])
def api_vapid_public_key():
    key = get_vapid_public_key()
    if not key:
        return jsonify({"error": "VAPID não configurado"}), 503
    return jsonify({"publicKey": key})


@notificacao_bp.route("/api/registrar_token/<token>", methods=["POST"])
def registrar_token(token):
    senha = Senha.query.filter_by(token_unico=token).first()
    if not senha:
        return jsonify({"error": "Token não encontrado"}), 404
    return jsonify({"success": True})


@notificacao_bp.route("/api/verificar_senha/<token>", methods=["GET"])
def api_verificar_senha(token):
    try:
        return jsonify(verificar_senha(token))
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 404


@notificacao_bp.route("/api/salvar_pedido/<token>", methods=["POST"])
def api_salvar_pedido(token):
    data = request.get_json(silent=True) or {}
    pedido = (data.get("pedido") or "").strip()
    if not pedido:
        return jsonify({"error": "Pedido não pode ser vazio"}), 400
    try:
        senha = salvar_pedido(token, pedido)
    except FilaError as exc:
        return jsonify({"error": str(exc)}), 404

    if senha.setor_id:
        from backend.sockets.emitters import emit_fila_atualizada

        emit_fila_atualizada(senha.setor_id)

    return jsonify({"success": True})


@notificacao_bp.route("/api/registrar_push/<token>", methods=["POST"])
def api_registrar_push(token):
    senha = Senha.query.filter_by(token_unico=token).first()
    if not senha:
        return jsonify({"error": "Token não encontrado"}), 404
    data = request.get_json(silent=True) or {}
    subscription = data.get("subscription")
    if subscription:
        senha.push_subscription = json.dumps(subscription)
        db.session.commit()
    return jsonify({"success": True})


@notificacao_bp.route("/api/avaliar/<token>", methods=["POST"])
def api_avaliar(token):
    data = request.get_json(silent=True) or {}
    try:
        nota = int(data.get("nota"))
    except (TypeError, ValueError):
        return jsonify({"error": "Nota inválida"}), 400
    try:
        result = registrar_avaliacao_por_token(token, nota)
    except AvaliacaoError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify(result)


@notificacao_bp.route("/api/notificar/<int:senha_id>", methods=["POST"])
def api_notificar(senha_id):
    """Envia notificação Web Push manual (fallback / teste)."""
    senha = Senha.query.get(senha_id)
    if not senha:
        return jsonify({"error": "Senha não encontrada"}), 404
    if not senha.push_subscription:
        return jsonify({"error": "Nenhuma subscription encontrada para esta senha"}), 404

    ok = enviar_web_push(
        senha,
        title=f"Sua senha {senha.senha} foi chamada!",
        body="Dirija-se ao atendimento.",
        tag="senha-chamada",
        require_interaction=True,
    )
    if not ok:
        return jsonify({"error": "Falha ao enviar notificação"}), 500
    return jsonify({"success": True, "message": f"Notificação enviada para senha {senha.senha}"})
