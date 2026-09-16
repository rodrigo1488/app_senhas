"""Serviço de impressão térmica (ESC/POS) — cupom compacto."""
import datetime
import io

from flask import current_app

from backend.timezone import agora_sp
from backend.utils import gerar_imagem_senha, gerar_qr_code_notificacao, obter_nome_empresa


def imprimir_senha_em_background(*args, **kwargs) -> None:
    """Despacha a impressão sem bloquear a resposta do totem."""
    app = current_app._get_current_object()

    def executar():
        with app.app_context():
            imprimir_senha_com_ip(*args, **kwargs)

    from backend.extensions import socketio

    socketio.start_background_task(executar)


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
        agora = agora_sp()

        p.set(align="center", bold=True)
        p.text("=" * 32 + "\n")

        # Nome da empresa: único bloco double (destaque sem alongar o cupom).
        p.set(align="center", bold=True, double_height=True, double_width=True)
        p.text(f"{obter_nome_empresa()}\n")

        imagem_senha = gerar_imagem_senha(senha)
        if imagem_senha:
            try:
                buffer = io.BytesIO()
                imagem_senha.save(buffer, format="PNG")
                buffer.seek(0)
                p.image(buffer, impl="bitImageRaster", center=True)
            except Exception as exc:
                current_app.logger.error(f"Erro ao imprimir imagem da senha: {exc}")
                p.set(align="center", bold=True, double_height=True, double_width=True)
                p.text(f"{senha}\n")
        else:
            p.set(align="center", bold=True, double_height=True, double_width=True)
            p.text(f"{senha}\n")

        p.set(align="center", bold=True)
        p.text("=" * 32 + "\n")
        # Altura normal: double_height em data/setor dobrava o papel.
        p.text(f"{agora.strftime('%d/%m/%Y')}  {agora.strftime('%H:%M')}\n")
        p.text(f"{nome_setor}\n")
        if descricao_setor:
            p.text(f"{descricao_setor}\n")
        p.text("=" * 32 + "\n")

        if token_unico:
            p.text("Escaneie para notificar\n")
            qr_buffer = gerar_qr_code_notificacao(token_unico)
            if qr_buffer:
                try:
                    p.image(qr_buffer, impl="bitImageRaster", center=True)
                except Exception as exc:
                    current_app.logger.error(f"Erro ao imprimir QR Code: {exc}")
            p.text("=" * 32 + "\n")

        p.text("Aguarde ser chamada\n")
        p.text("=" * 32 + "\n")
        # cut(feed=True) avança ~6 linhas vazias até o cortador — sobra um "pedaço"
        # gigante embaixo. Avanço curto + corte parcial sem feed extra.
        p.text("\n")
        try:
            p.cut(mode="PART", feed=False)
        except TypeError:
            # python-escpos antigo sem parâmetro feed
            try:
                p.cut(mode="PART")
            except Exception:
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
