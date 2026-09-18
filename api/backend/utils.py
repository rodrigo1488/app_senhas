"""Utilitários diversos: imagens, QR Code, IP local, nome da empresa/ngrok."""
import io
import os
import threading
import uuid

import qrcode
from flask import current_app, request
from PIL import Image, ImageDraw, ImageFont, ImageOps

from backend.extensions import db
from backend.models import Configuracao


def _file_extension(filename: str) -> str | None:
    if not filename or "." not in filename:
        return None
    return filename.rsplit(".", 1)[1].lower()


def allowed_file(filename: str) -> bool:
    ext = _file_extension(filename)
    return bool(ext) and ext in current_app.config["ALLOWED_EXTENSIONS"]


def is_video_filename(filename: str) -> bool:
    ext = _file_extension(filename)
    return bool(ext) and ext in current_app.config.get("ALLOWED_VIDEO_EXTENSIONS", set())


def process_image(file, max_size: tuple[int, int] = (500, 500), quality: int = 85) -> str | None:
    """Processa e salva a imagem com UUID único, retorna o nome do arquivo."""
    try:
        file_uuid = str(uuid.uuid4())
        image = Image.open(file)
        if image.mode in ("RGBA", "LA", "P"):
            image = image.convert("RGB")
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        filename = f"{file_uuid}.jpg"
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        image.save(filepath, "JPEG", quality=quality, optimize=True)
        return filename
    except Exception as exc:  # pragma: no cover - defensivo, igual ao código legado
        current_app.logger.error(f"Erro ao processar imagem: {exc}")
        return None


def process_propaganda_image(file) -> str | None:
    """Salva imagem de propaganda em resolução adequada para TV (~1920px)."""
    return process_image(file, max_size=(1920, 1920), quality=88)


# Tela horizontal típica. O APK de propaganda usa recorte (crop); a imagem
# já sai 16:9 para as laterais pretas aparecerem e o conteúdo vertical inteiro.
_TV_HORIZONTAL_RATIO = 16 / 9
_enquadre_cache: dict[tuple, bytes] = {}
_enquadre_lock = threading.Lock()


def bytes_imagem_enquadrada_tv(filepath: str) -> bytes | None:
    """JPEG 16:9 com a imagem vertical centralizada e laterais pretas.

    Retorna None se o arquivo já é horizontal/quadrado ou não for uma imagem.
    O original em disco não é alterado.
    """
    try:
        stat = os.stat(filepath)
    except OSError:
        return None
    key = (os.path.abspath(filepath), stat.st_mtime_ns, stat.st_size)
    with _enquadre_lock:
        cached = _enquadre_cache.get(key)
    if cached is not None:
        return cached

    try:
        image = ImageOps.exif_transpose(Image.open(filepath))
    except Exception as exc:
        current_app.logger.error(f"Erro ao abrir imagem de propaganda: {exc}")
        return None

    try:
        if image.width >= image.height:
            return None
        rgb, mask = _rgb_com_mascara(image)
        canvas_h = rgb.height
        canvas_w = max(rgb.width, round(canvas_h * _TV_HORIZONTAL_RATIO))
        canvas = Image.new("RGB", (canvas_w, canvas_h), (0, 0, 0))
        x = (canvas_w - rgb.width) // 2
        y = (canvas_h - rgb.height) // 2
        if mask is not None:
            canvas.paste(rgb, (x, y), mask)
        else:
            canvas.paste(rgb, (x, y))
        buffer = io.BytesIO()
        canvas.save(buffer, format="JPEG", quality=88, optimize=True)
        data = buffer.getvalue()
    except Exception as exc:
        current_app.logger.error(f"Erro ao enquadrar imagem de propaganda: {exc}")
        return None
    finally:
        image.close()

    with _enquadre_lock:
        if len(_enquadre_cache) > 32:
            _enquadre_cache.clear()
        _enquadre_cache[key] = data
    return data


def _rgb_com_mascara(image: Image.Image) -> tuple[Image.Image, Image.Image | None]:
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        return rgba.convert("RGB"), rgba.getchannel("A")
    return image.convert("RGB"), None


def save_propaganda_video(file) -> str | None:
    """Grava o MP4 como está (sem transcode) para reprodução na TV."""
    try:
        filename = f"{uuid.uuid4()}.mp4"
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        return filename
    except Exception as exc:  # pragma: no cover - defensivo
        current_app.logger.error(f"Erro ao salvar vídeo de propaganda: {exc}")
        return None


def delete_old_image(filename: str | None) -> None:
    if not filename:
        return
    try:
        filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f"Erro ao deletar imagem: {exc}")


def gerar_token_unico() -> str:
    return str(uuid.uuid4())


def obter_ip_rede_local() -> str:
    try:
        import socket

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_local = s.getsockname()[0]
        s.close()
        return ip_local
    except Exception:
        return "localhost"


def get_configuracao(chave: str, default: str | None = None) -> str | None:
    config = Configuracao.query.filter_by(chave=chave).first()
    return config.valor if config else default


def set_configuracao(chave: str, valor: str, descricao: str | None = None) -> None:
    config = Configuracao.query.filter_by(chave=chave).first()
    if config:
        config.valor = valor
    else:
        config = Configuracao(chave=chave, valor=valor, descricao=descricao)
        db.session.add(config)
    db.session.commit()


def get_ngrok_url() -> str:
    return get_configuracao("ngrok_url", "") or ""


def set_ngrok_url(url: str) -> None:
    set_configuracao("ngrok_url", url)


def obter_nome_empresa() -> str:
    """Retorna o nome da empresa, priorizando o cookie do navegador (compatível
    com o comportamento legado), com fallback para configuração no banco."""
    try:
        nome_cookie = request.cookies.get("nome_empresa")
        if nome_cookie:
            return nome_cookie
    except Exception:
        pass
    return get_configuracao("nome_empresa", current_app.config["NOME_EMPRESA_PADRAO"])


def get_cliente_web_base() -> str:
    """Host público do painel Next (página `/acompanhar`).

    Prioridade:
    1. URL salva no admin (`ngrok_url` / URL pública)
    2. Variável de ambiente `ADMIN_WEB_URL`
    3. IP local na porta 3000 (fallback de desenvolvimento)
    """
    configurada = (get_ngrok_url() or "").strip().rstrip("/")
    if configurada:
        return configurada

    admin = (os.getenv("ADMIN_WEB_URL") or "").strip().rstrip("/")
    if admin:
        return admin

    ip_local = obter_ip_rede_local()
    return f"http://{ip_local}:3000"


def get_notification_url(token: str) -> str:
    return f"{get_cliente_web_base()}/acompanhar/{token}"


def gerar_qr_code_bytes(data: str) -> bytes:
    # box_size menor: QR legível sem consumir metade do cupom.
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def gerar_qr_code_notificacao(token_unico: str) -> io.BytesIO | None:
    try:
        url = get_notification_url(token_unico)
        current_app.logger.info("QR de acompanhamento: %s", url)
        data = gerar_qr_code_bytes(url)
        return io.BytesIO(data)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f"Erro ao gerar QR Code: {exc}")
        return None


def gerar_imagem_senha(senha: str, largura_maxima: int = 384):
    """Gera bitmap alto contraste da senha, com altura justa ao texto."""
    try:
        # Canvas alto só para medir; depois recorta o padding vertical.
        canvas_h = 140
        imagem = Image.new("RGB", (largura_maxima, canvas_h), "white")
        draw = ImageDraw.Draw(imagem)

        fontes_possiveis = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf",
            "DejaVuSans.ttf",
            "arialbd.ttf",
            "Arial-Bold.ttf",
            "arial.ttf",
            "Arial.ttf",
            "calibrib.ttf",
            "Calibri-Bold.ttf",
            "verdanab.ttf",
            "Verdana-Bold.ttf",
        ]
        fonte = None
        tamanho_fonte = 84
        fonte_nome_usada = None
        for fonte_nome in fontes_possiveis:
            try:
                fonte = ImageFont.truetype(fonte_nome, tamanho_fonte)
                fonte_nome_usada = fonte_nome
                break
            except Exception:
                continue
        if fonte is None:
            fonte = ImageFont.load_default(size=tamanho_fonte)

        bbox = draw.textbbox((0, 0), senha, font=fonte)
        largura_texto = bbox[2] - bbox[0]
        while largura_texto > largura_maxima - 16 and tamanho_fonte > 28:
            tamanho_fonte -= 4
            try:
                fonte = (
                    ImageFont.truetype(fonte_nome_usada, tamanho_fonte)
                    if fonte_nome_usada
                    else ImageFont.load_default(size=tamanho_fonte)
                )
            except Exception:
                fonte = ImageFont.load_default(size=tamanho_fonte)
            bbox = draw.textbbox((0, 0), senha, font=fonte)
            largura_texto = bbox[2] - bbox[0]

        altura_texto = bbox[3] - bbox[1]
        pad_y = 4
        x = (largura_maxima - largura_texto) // 2
        y = pad_y - bbox[1]
        for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1), (2, 0), (0, 2)):
            draw.text((x + dx, y + dy), senha, fill="black", font=fonte)

        # Recorte justo: remove faixa branca acima/abaixo da senha.
        crop_bottom = min(canvas_h, pad_y + altura_texto + 4)
        imagem = imagem.crop((0, 0, largura_maxima, crop_bottom))
        cinza = imagem.convert("L")
        return cinza.point(lambda p: 0 if p < 200 else 255, mode="1")
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f"Erro ao gerar imagem da senha '{senha}': {exc}")
        return None
