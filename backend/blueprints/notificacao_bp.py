"""Página pública de acompanhamento de senha (QR Code) + Web Push.

Autenticação de socket aqui é feita por `ticket_token` (o próprio
`token_unico` da senha), não por login de setor — ver
`documentacao/REALTIME_PROTOCOL.md`, seção 1.
"""
import json

from flask import Blueprint, jsonify, render_template, request

from backend.extensions import db
from backend.models import Senha
from backend.services.fila_service import FilaError, posicao_na_fila, salvar_pedido, verificar_senha
from backend.sockets.emitters import emit_senha_posicao

notificacao_bp = Blueprint("notificacao", __name__)


@notificacao_bp.route("/notificacao/<token>")
def notificacao(token):
    if not Senha.query.filter_by(token_unico=token).first():
        return "Senha não encontrada", 404
    return render_template("notificacao.html", token=token)


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


@notificacao_bp.route("/api/notificar/<int:senha_id>", methods=["POST"])
def api_notificar(senha_id):
    """Envia notificação Web Push para uma senha específica (fallback para
    quando o cliente não está com a página aberta / socket conectado)."""
    from flask import current_app

    senha = Senha.query.get(senha_id)
    if not senha:
        return jsonify({"error": "Senha não encontrada"}), 404
    if not senha.push_subscription:
        return jsonify({"error": "Nenhuma subscription encontrada para esta senha"}), 404

    try:
        from pywebpush import webpush

        notification_data = {
            "title": f"Sua senha {senha.senha} foi chamada!",
            "body": "Dirija-se ao atendimento.",
            "icon": "/static/icon-192x192.png",
            "tag": "senha-chamada",
            "requireInteraction": True,
        }
        webpush(
            subscription_info=json.loads(senha.push_subscription),
            data=json.dumps(notification_data),
            vapid_private_key=current_app.config["VAPID_PRIVATE_KEY"],
            vapid_claims={"sub": current_app.config["VAPID_EMAIL"], "aud": "https://fcm.googleapis.com"},
        )
    except ImportError:
        current_app.logger.warning("pywebpush não instalado.")
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f"Erro ao enviar notificação push: {exc}")

    return jsonify({"success": True, "message": f"Notificação enviada para senha {senha.senha}"})
