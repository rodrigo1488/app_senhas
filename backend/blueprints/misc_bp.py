"""Rotas utilitárias/diagnóstico que não pertencem a nenhum domínio específico."""
from flask import Blueprint, current_app, jsonify, request, send_from_directory

from backend.utils import get_ngrok_url, set_ngrok_url

misc_bp = Blueprint("misc", __name__)


@misc_bp.route("/check_helth", methods=["GET"])
def check_helth():
    return jsonify({"status": "ok"})


@misc_bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@misc_bp.route("/api/configuracao/ngrok", methods=["GET", "POST"])
def api_configuracao_ngrok():
    """Mantido no path público antigo (sem prefixo /admin) para compatibilidade
    com integrações existentes."""
    if request.method == "GET":
        return jsonify({"ngrok_url": get_ngrok_url()})
    data = request.get_json(silent=True) or {}
    set_ngrok_url(data.get("ngrok_url", "").strip())
    return jsonify({"success": True, "message": "URL do ngrok atualizada com sucesso!"})
