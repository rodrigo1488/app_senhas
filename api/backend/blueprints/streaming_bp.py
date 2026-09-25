"""Compatibilidade com o APP_STREAMING: TVs antigas continuam em :5000/smart e /legacy."""
import io
import os
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request, send_file, send_from_directory
from werkzeug.utils import safe_join

from backend.utils import bytes_imagem_enquadrada_tv, normalizar_orientacao_tv, video_enquadrado_tv

from backend.extensions import db
from backend.models import TvDispositivo
from backend.services.tv_config_service import INTERVALO_IMAGEM_MS
from backend.services.streaming_service import (
    atribuir_paths_streaming,
    biblioteca_como_media_files,
    connected_by_chave,
    esta_online,
    fila_streaming,
    marcar_online,
    registrar_streaming,
    vincular_tv_streaming_ao_setor,
)

streaming_bp = Blueprint("streaming", __name__)


@streaming_bp.route("/stream")
def streaming_home():
    return render_template("streaming/tela_inicial.html")


@streaming_bp.route("/smart")
def streaming_smart():
    return render_template("streaming/client.html")


@streaming_bp.route("/legacy")
def streaming_legacy():
    return render_template("streaming/client_legacy.html")


_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
_VIDEO_EXT = {".mp4"}


@streaming_bp.route("/media/<path:filename>")
def serve_media(filename):
    ext = os.path.splitext(filename)[1].lower()
    filepath = safe_join(current_app.config["UPLOAD_FOLDER"], filename)
    # Letterbox/rotação só com `enquadre` explícito (legado). Sem parâmetro = original.
    bruto = request.args.get("enquadre")
    if bruto is not None and filepath and os.path.isfile(filepath):
        valor = bruto.strip().lower()
        if valor not in {"0", "false", "off", "none", ""}:
            orientacao = normalizar_orientacao_tv(valor)
            if ext in _IMAGE_EXT:
                data = bytes_imagem_enquadrada_tv(filepath, orientacao=orientacao)
                if data is not None:
                    return send_file(io.BytesIO(data), mimetype="image/jpeg", max_age=86400)
            elif ext in _VIDEO_EXT:
                transcoded = video_enquadrado_tv(filepath, orientacao=orientacao)
                if transcoded:
                    return send_file(transcoded, mimetype="video/mp4", max_age=86400, conditional=True)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


@streaming_bp.route("/check_health")
def check_health():
    return jsonify({"status": "ok", "connected_clients": len(connected_by_chave)})


@streaming_bp.route("/device_info")
def device_info():
    return jsonify(
        {
            "ip_address": request.remote_addr or "",
            "user_agent": request.headers.get("User-Agent", ""),
        }
    )


@streaming_bp.route("/api/global_settings")
def global_settings():
    return jsonify(
        {
            "settings": {
                "imageDuration": INTERVALO_IMAGEM_MS,
                "transitionDuration": 1000,
            }
        }
    )


@streaming_bp.route("/api/media")
@streaming_bp.route("/api/media/<path:folder_path>")
def list_media(folder_path=""):
    return jsonify(biblioteca_como_media_files())


@streaming_bp.route("/api/folders")
def list_folders():
    return jsonify([])


@streaming_bp.route("/api/clients")
def list_clients():
    dispositivos = TvDispositivo.query.filter_by(tipo="streaming").order_by(TvDispositivo.last_seen.desc()).all()
    return jsonify(
        [
            {
                "ip_address": dispositivo.chave,
                "last_seen": dispositivo.last_seen.isoformat() if dispositivo.last_seen else None,
                "is_online": esta_online(dispositivo.chave),
                "device_name": dispositivo.device_name or "Dispositivo",
                "user_agent": dispositivo.user_agent or "",
                "nome": dispositivo.nome,
                "queue": fila_streaming(dispositivo),
            }
            for dispositivo in dispositivos
        ]
    )


@streaming_bp.route("/api/assign", methods=["POST"])
def assign_media():
    data = request.get_json(silent=True) or {}
    ip_address = data.get("ip_address")
    media_list = data.get("media_list") or []
    if not ip_address:
        return jsonify({"error": "IP address é obrigatório"}), 400
    atribuir_paths_streaming(ip_address, media_list)
    return jsonify({"success": True})


@streaming_bp.route("/api/sync/<ip_address>")
def sync_queue(ip_address):
    dispositivo = TvDispositivo.query.filter_by(chave=ip_address).first()
    if not dispositivo:
        return jsonify({"queue": []})
    return jsonify({"queue": fila_streaming(dispositivo)})


@streaming_bp.route("/api/poll/<ip_address>")
def poll_client(ip_address):
    dispositivo = TvDispositivo.query.filter_by(chave=ip_address).first()
    if not dispositivo:
        return jsonify({"status": "not_found"}), 404
    dispositivo.last_seen = datetime.now()
    marcar_online(dispositivo.chave, f"poll_{ip_address}")
    db.session.commit()
    return jsonify(
        {
            "status": "ok",
            "client": {
                "ip_address": dispositivo.chave,
                "device_name": dispositivo.device_name or "Dispositivo",
                "nome": dispositivo.nome,
                "is_online": esta_online(dispositivo.chave),
            },
            "queue": fila_streaming(dispositivo),
            "global_settings": {},
        }
    )


@streaming_bp.route("/api/register_poll", methods=["POST"])
def register_poll():
    data = request.get_json(silent=True) or {}
    ip_address = data.get("ip_address")
    if not ip_address:
        return jsonify({"status": "error", "message": "IP address é obrigatório"}), 400
    dispositivo = registrar_streaming(
        ip_address=ip_address,
        device_name=data.get("device_name") or "Dispositivo",
        user_agent=data.get("user_agent") or request.headers.get("User-Agent", ""),
        nome=data.get("nome"),
        sid=f"poll_{ip_address}",
    )
    setor_raw = data.get("setor_id")
    if setor_raw not in (None, ""):
        try:
            setor_id = int(setor_raw)
        except (TypeError, ValueError):
            return jsonify({"status": "error", "message": "setor_id inválido"}), 400
        try:
            vincular_tv_streaming_ao_setor(dispositivo, setor_id)
        except ValueError as exc:
            status = 404 if "não encontrad" in str(exc) else 400
            return jsonify({"status": "error", "message": str(exc)}), status
    return jsonify(
        {
            "status": "ok",
            "message": "Cliente registrado com sucesso",
            "ip_address": ip_address,
            "setor_id": dispositivo.setor_id,
        }
    )


@streaming_bp.route("/api/remove_client", methods=["POST"])
def remove_client():
    data = request.get_json(silent=True) or {}
    ip_address = data.get("ip_address")
    if not ip_address:
        return jsonify({"error": "IP address é obrigatório"}), 400
    dispositivo = TvDispositivo.query.filter_by(chave=ip_address, tipo="streaming").first()
    if dispositivo:
        db.session.delete(dispositivo)
        db.session.commit()
    return jsonify({"success": True})


@streaming_bp.route("/api/update_device_name", methods=["POST"])
def update_device_name():
    data = request.get_json(silent=True) or {}
    ip_address = data.get("ip_address")
    new_name = (data.get("new_name") or "").strip()
    if not ip_address or not new_name:
        return jsonify({"error": "IP address e novo nome são obrigatórios"}), 400
    dispositivo = TvDispositivo.query.filter_by(chave=ip_address, tipo="streaming").first()
    if not dispositivo:
        return jsonify({"error": "Dispositivo não encontrado"}), 404
    conflito = TvDispositivo.query.filter(
        TvDispositivo.tipo == "streaming",
        TvDispositivo.nome == new_name,
        TvDispositivo.id != dispositivo.id,
    ).first()
    if conflito:
        return jsonify({"error": f'Nome "{new_name}" já está sendo usado por outro dispositivo'}), 409
    dispositivo.nome = new_name
    db.session.commit()
    return jsonify({"success": True, "message": f'Nome atualizado para "{new_name}"'})
