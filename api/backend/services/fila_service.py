"""Regras de negócio da fila de senhas.

Esta é a camada usada tanto pelas rotas REST (`backend/blueprints/api_bp.py`,
usada pelo app Android) quanto pelos templates web de fallback
(`backend/blueprints/filas_bp.py`, `operador_bp.py`) e pelos handlers de
Socket.IO em `backend/sockets/`. Um único lugar de verdade para "criar senha",
"chamar próxima" etc. evita a duplicação que existia no `backend/__init__.py` legado
(rota REST e handler de socket faziam a mesma coisa de formas diferentes).

Nenhuma função aqui emite eventos de socket diretamente — quem chama decide
quando emitir (normalmente logo depois de uma chamada bem-sucedida), para
manter a camada de serviço testável e livre de efeitos colaterais de rede.
"""
import random
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from backend.extensions import db
from backend.models import AtendimentoAtual, Finalizado, Operador, Senha, Setor
from backend.utils import gerar_token_unico, get_configuracao

# Lock por setor para serializar "chamar próxima" (evita duas senhas iguais
# sendo chamadas simultaneamente por dois operadores do mesmo setor).
_setor_locks: dict[int, threading.Lock] = defaultdict(threading.Lock)


class FilaError(Exception):
    """Erro de negócio esperado (setor não encontrado, sem senhas, etc.)."""


@dataclass
class ChamadaResultado:
    senha: Senha
    tipo_chamado: str
    alerta_preferenciais: bool
    operador: Operador
    senha_anterior_finalizada: Optional[Senha] = None
    pedido: dict = field(default_factory=dict)


def serializar_fila(setor_id: int) -> dict:
    """Monta o payload completo do evento `fila:atualizada` para um setor."""
    pendentes = (
        Senha.query.filter_by(setor_id=setor_id, status="A")
        .order_by(Senha.tipo.desc(), Senha.id.asc())
        .all()
    )
    atendimentos_query = (
        db.session.query(AtendimentoAtual, Operador, Senha)
        .join(Operador, AtendimentoAtual.operador_id == Operador.id)
        .join(Senha, AtendimentoAtual.senha_id == Senha.id)
        .filter(AtendimentoAtual.setor_id == setor_id)
        .order_by(AtendimentoAtual.id.desc())
    )
    ultimo_por_operador: dict[int, tuple] = {}
    for atendimento, operador, senha in atendimentos_query.all():
        if operador.id not in ultimo_por_operador:
            ultimo_por_operador[operador.id] = (operador, senha)

    return {
        "setor_id": setor_id,
        "pendentes": [p.to_dict() for p in pendentes],
        "atendimentos": [
            {
                "operador_id": operador.id,
                "operador_nome": operador.nome,
                "operador_foto": operador.foto_perfil,
                "senha": senha.senha,
                "tipo": senha.tipo,
                "senha_id": senha.id,
            }
            for operador, senha in sorted(ultimo_por_operador.values(), key=lambda t: t[0].nome or "")
        ],
    }


def criar_senha(setor_id: int, tipo: str) -> Senha:
    setor = Setor.query.get(setor_id)
    if not setor:
        raise FilaError("Setor não encontrado")

    codigo_senha = f"{tipo[:1].upper()}{random.randint(1000, 9999)}"
    senha = Senha(
        senha=codigo_senha,
        tipo=tipo,
        setor_id=setor_id,
        status="A",
        token_unico=gerar_token_unico(),
    )
    db.session.add(senha)
    db.session.commit()
    return senha


def listar_operadores(setor_id: int) -> list[Operador]:
    return Operador.query.filter_by(setor_id=setor_id).order_by(Operador.nome).all()


def chamar_proxima(setor_id: int, operador_id: int) -> ChamadaResultado:
    """Reimplementação fiel da lógica de proporção normal/preferencial que
    antes vivia na rota `/chamar_proxima` (POST) do `backend/__init__.py` legado, agora
    lendo os parâmetros de `configuracoes` (antes eram cookies do navegador
    do operador, o que não fazia sentido para múltiplos dispositivos)."""
    operador = Operador.query.get(operador_id)
    if not operador or operador.setor_id != setor_id:
        raise FilaError("Operador não encontrado neste setor")

    lock = _setor_locks[setor_id]
    with lock:
        senha_anterior_finalizada = None
        ultimo_atendimento = (
            AtendimentoAtual.query.filter_by(setor_id=setor_id, operador_id=operador_id)
            .order_by(AtendimentoAtual.id.desc())
            .first()
        )
        agora = datetime.now()
        if ultimo_atendimento:
            senha_anterior = Senha.query.get(ultimo_atendimento.senha_id)
            db.session.add(Finalizado(senha_id=ultimo_atendimento.senha_id, operador_id=operador_id, setor_id=setor_id, avaliacao=""))
            db.session.delete(ultimo_atendimento)
            if senha_anterior:
                senha_anterior.status = "F"
                senha_anterior.finalizado_em = agora
                senha_anterior_finalizada = senha_anterior

        todas = (
            Senha.query.filter_by(setor_id=setor_id, status="A")
            .order_by(Senha.id.asc())
            .all()
        )
        normais = [s for s in todas if s.tipo == "normal"]
        preferenciais = [s for s in todas if s.tipo == "preferencial"]

        proporcao_normais = int(get_configuracao("proporcao_normais") or 2)
        limite_preferenciais_alerta = int(get_configuracao("limite_preferenciais_alerta") or 3)
        normais_chamadas_key = f"normais_chamadas_setor_{setor_id}"
        normais_chamadas = int(get_configuracao(normais_chamadas_key) or 0)

        alerta_preferenciais = False
        proxima = None
        tipo_a_chamar = None

        if len(preferenciais) > limite_preferenciais_alerta:
            proxima = preferenciais[0] if preferenciais else (normais[0] if normais else None)
            tipo_a_chamar = "preferencial" if preferenciais else "normal"
            alerta_preferenciais = True
            normais_chamadas = 0
        elif preferenciais and normais:
            if normais_chamadas < proporcao_normais:
                proxima = normais[0]
                tipo_a_chamar = "normal"
                normais_chamadas += 1
            else:
                proxima = preferenciais[0]
                tipo_a_chamar = "preferencial"
                normais_chamadas = 0
        elif preferenciais:
            proxima = preferenciais[0]
            tipo_a_chamar = "preferencial"
            normais_chamadas = 0
        elif normais:
            proxima = normais[0]
            tipo_a_chamar = "normal"
            normais_chamadas += 1

        if proxima is None:
            db.session.rollback()
            raise FilaError("Sem senhas pendentes")

        proxima.status = "C"
        proxima.chamada_em = agora
        db.session.add(AtendimentoAtual(senha_id=proxima.id, setor_id=setor_id, operador_id=operador_id, data_hora=agora))

        from backend.utils import set_configuracao
        set_configuracao(normais_chamadas_key, str(normais_chamadas))

        db.session.commit()

        return ChamadaResultado(
            senha=proxima,
            tipo_chamado=tipo_a_chamar,
            alerta_preferenciais=alerta_preferenciais,
            operador=operador,
            senha_anterior_finalizada=senha_anterior_finalizada,
        )


def chamar_novamente(senha_id: int) -> Senha:
    senha = Senha.query.get(senha_id)
    if not senha or senha.status != "C":
        raise FilaError("Senha não encontrada ou não está em atendimento")
    return senha


def salvar_pedido(token_unico: str, pedido: str) -> Senha:
    senha = Senha.query.filter_by(token_unico=token_unico).first()
    if not senha:
        raise FilaError("Token não encontrado")
    senha.pedido = pedido
    senha.tem_pedido = True
    db.session.commit()
    return senha


def confirmar_pedido(
    senha_codigo: str,
    setor_id: int | None = None,
    operador_id: int | None = None,
) -> Senha:
    query = Senha.query.filter_by(senha=senha_codigo, status="C")
    if setor_id is not None:
        query = query.filter(Senha.setor_id == setor_id)
    if operador_id is not None:
        query = query.join(AtendimentoAtual, AtendimentoAtual.senha_id == Senha.id).filter(
            AtendimentoAtual.operador_id == operador_id
        )
    senha = query.order_by(Senha.id.desc()).first()
    if not senha:
        raise FilaError("Senha não encontrada ou não está em atendimento")
    senha.pedido_confirmado = True
    db.session.commit()
    return senha


def posicao_na_fila(token_unico: str) -> dict:
    senha = Senha.query.filter_by(token_unico=token_unico).first()
    if not senha:
        raise FilaError("Token não encontrado")

    setor = Setor.query.get(senha.setor_id) if senha.setor_id else None

    if senha.status == "C":
        posicao = 0
    elif senha.status == "F":
        posicao = -1
    else:
        posicao = Senha.query.filter(
            Senha.setor_id == senha.setor_id, Senha.status == "A", Senha.id < senha.id
        ).count()

    avaliacao_pendente = False
    if senha.status == "F":
        from backend.services.avaliacao_service import avaliacao_pendente_por_senha

        avaliacao_pendente = avaliacao_pendente_por_senha(senha.id)

    return {
        "token_unico": token_unico,
        "posicao": posicao,
        "senha": senha.senha,
        "status": senha.status,
        "setor_nome": setor.nome if setor else "Geral",
        "tem_pedido": bool(senha.tem_pedido),
        "pedido": senha.pedido,
        "pedido_confirmado": bool(senha.pedido_confirmado),
        "avaliacao_pendente": avaliacao_pendente,
    }


def estado_atendimento_atual(setor_id: int, operador_id: int | None = None) -> Optional[dict]:
    """Estado da senha em atendimento no momento, no formato do payload de
    `senha:chamada` — usado para hidratar a tela sem precisar de fetch quando
    ela é aberta/recarregada (ver `operador_bp.py` e `filas_bp.py`)."""
    query = (
        db.session.query(AtendimentoAtual, Operador, Senha)
        .join(Operador, AtendimentoAtual.operador_id == Operador.id)
        .join(Senha, AtendimentoAtual.senha_id == Senha.id)
        .filter(AtendimentoAtual.setor_id == setor_id, Senha.status == "C")
        .order_by(Senha.id.desc())
    )
    if operador_id is not None:
        query = query.filter(AtendimentoAtual.operador_id == operador_id)
    row = query.first()
    if not row:
        return None
    _, operador, senha = row
    return {
        "setor_id": setor_id,
        "ticket_token": senha.token_unico,
        "senha_id": senha.id,
        "senha": senha.senha,
        "tipo": senha.tipo,
        "operador_id": operador.id,
        "operador_nome": operador.nome,
        "operador_foto": operador.foto_perfil,
        "tem_pedido": bool(senha.tem_pedido),
        "pedido": senha.pedido,
        "pedido_confirmado": bool(senha.pedido_confirmado),
        "alerta_preferenciais": False,
    }


def verificar_senha(token_unico: str) -> dict:
    senha = Senha.query.filter_by(token_unico=token_unico).first()
    if not senha:
        raise FilaError("Token não encontrado")
    setor = Setor.query.get(senha.setor_id) if senha.setor_id else None
    posicao_info = posicao_na_fila(token_unico)
    return {
        "senha": senha.senha,
        "status": senha.status,
        "chamada": senha.status == "C",
        "finalizado": senha.status == "F",
        "pedido": senha.pedido,
        "tem_pedido": bool(senha.tem_pedido),
        "pedido_confirmado": bool(senha.pedido_confirmado),
        "setor": setor.nome if setor else "N/A",
        # Campos alinhados a `senha:posicao` para hidratar a tela Next sem socket.
        **posicao_info,
        "setor_nome": posicao_info.get("setor_nome") or (setor.nome if setor else "Geral"),
    }
