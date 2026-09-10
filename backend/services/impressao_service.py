"""Serviço de impressão térmica (ESC/POS) — inalterado em relação ao
comportamento do `app.py` legado, apenas isolado como serviço reutilizável."""
import datetime
import io

from flask import current_app

from backend.utils import gerar_imagem_senha, gerar_qr_code_notificacao, obter_nome_empresa


def imprimir_senha_com_ip(
    senha: str,
    impressora_ip: str,
    nome_setor: str = "Setor",
    descricao_setor: str = "",
    token_unico: str | None = None,
) -> bool:
    """Envia a senha para a impressora térmica usando ESC/POS com imagem
    bitmap da senha e QR Code de notificação (quando `token_unico` é dado)."""
    try:
        from escpos.printer import Network
    except ImportError:  # pragma: no cover - ambiente sem escpos instalado
        current_app.logger.warning("python-escpos não instalado; impressão ignorada.")
        return False

    p = None
    try:
        p = Network(impressora_ip, current_app.config["IMPRESSORA_PORTA"])
        p.set(align="center")
        p.text("\x1b\x21\x00")
        p.text("\n")
        p.text("=" * 32 + "\n")
        p.text("\n")

        p.text("\x1b\x21\x10")
        p.text(f"{obter_nome_empresa()}\n")
        p.text("\x1b\x21\x00")
        p.text("\n")

        imagem_senha = gerar_imagem_senha(senha)
        if imagem_senha:
            try:
                buffer = io.BytesIO()
                imagem_senha.save(buffer, format="PNG")
                buffer.seek(0)
                p.image(buffer, impl="bitImageRaster", center=True)
            except Exception as exc:
                current_app.logger.error(f"Erro ao imprimir imagem da senha: {exc}")
                p.text("\x1b\x21\x30")
                p.text(f"{senha}\n")
                p.text("\x1b\x21\x00")
        else:
            p.text("\x1b\x21\x30")
            p.text(f"{senha}\n")
            p.text("\x1b\x21\x00")

        p.text("\n")
        p.text("=" * 32 + "\n")
        p.text(f"Data: {datetime.datetime.now().strftime('%d/%m/%Y')}\n")
        p.text(f"Hora: {datetime.datetime.now().strftime('%H:%M')}\n")
        p.text(f"{nome_setor}\n")
        if descricao_setor:
            p.text(f"{descricao_setor}\n")
        p.text("=" * 32 + "\n")

        if token_unico:
            p.text("\n")
            p.text("Escaneie para receber\n")
            p.text("notificação quando\n")
            p.text("for sua vez\n")
            p.text("\n")
            qr_buffer = gerar_qr_code_notificacao(token_unico)
            if qr_buffer:
                try:
                    p.image(qr_buffer, impl="bitImageRaster", center=True)
                except Exception as exc:
                    current_app.logger.error(f"Erro ao imprimir QR Code: {exc}")
            p.text("\n")

        p.text("Aguarde ser chamada\n")
        p.text("na tela de atendimento\n")
        p.text("=" * 32 + "\n")
        p.cut()
        return True
    except Exception as exc:
        current_app.logger.error(f"Erro ao imprimir senha '{senha}': {exc}")
        return False
    finally:
        if p:
            try:
                p.close()
            except Exception:
                pass
