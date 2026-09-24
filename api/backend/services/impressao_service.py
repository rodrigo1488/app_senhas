"""Serviço de impressão térmica (ESC/POS) — cupom compacto.

Dois modos por setor:
- servidor: conecta na impressora pela rede (mesma LAN do backend)
- via cliente: monta os bytes ESC/POS e devolve no JSON para o tablet
  (na LAN da impressora) encaminhar via TCP :9100 — útil com API atrás de túnel
"""
from __future__ import annotations

import base64
import io

from flask import current_app

from backend.models import Impressora, Senha, Setor
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


def montar_cupom_escpos(
    senha: str,
    nome_setor: str = "Setor",
    descricao_setor: str = "",
    token_unico: str | None = None,
) -> bytes | None:
    """Gera o payload ESC/POS do cupom sem falar com a impressora."""
    try:
        from escpos.printer import Dummy
    except ImportError:  # pragma: no cover
        current_app.logger.warning("python-escpos não instalado; cupom ignorado.")
        return None

    try:
        p = Dummy()
        _escrever_cupom(
            p,
            senha=senha,
            nome_setor=nome_setor,
            descricao_setor=descricao_setor,
            token_unico=token_unico,
        )
        return bytes(p.output)
    except Exception as exc:
        current_app.logger.error(f"Erro ao montar cupom ESC/POS '{senha}': {exc}")
        return None


def imprimir_senha_com_ip(
    senha: str,
    impressora_ip: str,
    nome_setor: str = "Setor",
    descricao_setor: str = "",
    token_unico: str | None = None,
    impressora_porta: int | None = None,
) -> bool:
    """Envia a senha para a impressora térmica usando ESC/POS."""
    try:
        from escpos.printer import Network
    except ImportError:  # pragma: no cover - ambiente sem escpos instalado
        current_app.logger.warning("python-escpos não instalado; impressão ignorada.")
        return False

    porta = int(impressora_porta or current_app.config.get("IMPRESSORA_PORTA") or 9100)
    p = None
    try:
        p = Network(impressora_ip, porta)
        _escrever_cupom(
            p,
            senha=senha,
            nome_setor=nome_setor,
            descricao_setor=descricao_setor,
            token_unico=token_unico,
        )
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


def despachar_impressao_senha(setor: Setor | None, senha: Senha) -> dict | None:
    """Imprime no servidor ou devolve payload para o tablet do cliente.

    Retorno:
    - None: sem impressora cadastrada
    - {"via_cliente": False}: impressão despachada no servidor
    - {"via_cliente": True, "impressora_ip", "impressora_porta", "escpos_base64"}
    """
    if setor is None or senha is None:
        return None
    impressora = Impressora.query.filter_by(setor_id=setor.id).first()
    if not impressora or not (impressora.ip or "").strip():
        return None

    nome = setor.nome or "Setor"
    descricao = setor.descricao or ""
    porta = int(impressora.porta or current_app.config.get("IMPRESSORA_PORTA") or 9100)

    if bool(getattr(setor, "impressao_via_cliente", False)):
        raw = montar_cupom_escpos(
            senha.senha,
            nome_setor=nome,
            descricao_setor=descricao,
            token_unico=senha.token_unico,
        )
        if not raw:
            return {
                "via_cliente": True,
                "impressora_ip": impressora.ip.strip(),
                "impressora_porta": porta,
                "erro": "Não foi possível montar o cupom",
            }
        return {
            "via_cliente": True,
            "impressora_ip": impressora.ip.strip(),
            "impressora_porta": porta,
            "escpos_base64": base64.b64encode(raw).decode("ascii"),
        }

    imprimir_senha_em_background(
        senha.senha,
        impressora.ip.strip(),
        nome_setor=nome,
        descricao_setor=descricao,
        token_unico=senha.token_unico,
        impressora_porta=porta,
    )
    return {"via_cliente": False}


def _escrever_cupom(p, *, senha: str, nome_setor: str, descricao_setor: str, token_unico: str | None) -> None:
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
