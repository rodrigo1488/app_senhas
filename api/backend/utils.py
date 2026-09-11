"""Utilitários diversos: imagens, QR Code, IP local, nome da empresa/ngrok."""
import io
import os
import uuid

import qrcode
from flask import current_app, request
from PIL import Image, ImageDraw, ImageFont

from backend.extensions import db
from backend.models import Configuracao


def allowed_file(filename: str) -> bool:
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


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
    """Host do painel Next (página pública /acompanhar).

    Usa `ADMIN_WEB_URL` (ex.: http://localhost:3000 ou um túnel apontando
    para o Next). Não reutiliza o ngrok da API Flask — esse túnel costuma
    apontar para a porta 5000, onde `/acompanhar` não existe.
    """
    import os

    admin = (os.getenv("ADMIN_WEB_URL") or "").rstrip("/")
    if admin:
        return admin
    ip_local = obter_ip_rede_local()
    return f"http://{ip_local}:3000"


def get_notification_url(token: str) -> str:
    return f"{get_cliente_web_base()}/acompanhar/{token}"


def gerar_qr_code_bytes(data: str) -> bytes:
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=2)
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
        data = gerar_qr_code_bytes(url)
        return io.BytesIO(data)
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f"Erro ao gerar QR Code: {exc}")
        return None


def gerar_imagem_senha(senha: str, largura_maxima: int = 384):
    """Gera uma imagem bitmap da senha para impressão térmica."""
    try:
        altura = 80
        imagem = Image.new("L", (largura_maxima, altura), 255)
        draw = ImageDraw.Draw(imagem)

        fontes_possiveis = [
            "arial.ttf", "Arial.ttf", "arialbd.ttf", "Arial-Bold.ttf",
            "calibri.ttf", "Calibri.ttf", "calibrib.ttf", "Calibri-Bold.ttf",
            "verdana.ttf", "Verdana.ttf", "verdanab.ttf", "Verdana-Bold.ttf",
            "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
        ]
        fonte = None
        tamanho_fonte = 72
        fonte_nome_usada = None
        for fonte_nome in fontes_possiveis:
            try:
                fonte = ImageFont.truetype(fonte_nome, tamanho_fonte)
                fonte_nome_usada = fonte_nome
                break
            except Exception:
                continue
        if fonte is None:
            # Nenhuma fonte TrueType encontrada no sistema (ex.: imagem Docker
            # sem fonts-dejavu-core instalado). `load_default()` sem `size`
            # retorna um bitmap fixo de ~8px — praticamente ilegível impresso.
            # Passar `size=` (Pillow >= 10.1) mantém o número grande mesmo
            # nesse fallback.
            fonte = ImageFont.load_default(size=tamanho_fonte)

        bbox = draw.textbbox((0, 0), senha, font=fonte)
        largura_texto = bbox[2] - bbox[0]
        while largura_texto > largura_maxima - 20 and tamanho_fonte > 18:
            tamanho_fonte -= 5
            try:
                fonte = ImageFont.truetype(fonte_nome_usada, tamanho_fonte) if fonte_nome_usada else ImageFont.load_default(size=tamanho_fonte)
            except Exception:
                fonte = ImageFont.load_default(size=tamanho_fonte)
            bbox = draw.textbbox((0, 0), senha, font=fonte)
            largura_texto = bbox[2] - bbox[0]

        altura_texto = bbox[3] - bbox[1]
        x = (largura_maxima - largura_texto) // 2
        y = (altura - altura_texto) // 2
        draw.text((x, y), senha, fill=0, font=fonte)
        return imagem.convert("1")
    except Exception as exc:  # pragma: no cover
        current_app.logger.error(f"Erro ao gerar imagem da senha '{senha}': {exc}")
        return None
