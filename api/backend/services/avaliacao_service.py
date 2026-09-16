"""Regras de negócio da avaliação de atendimento."""
from backend.extensions import db
from backend.models import Finalizado, Operador, Senha


class AvaliacaoError(Exception):
    pass


def buscar_avaliacao_pendente(setor_id: int, operador_id: int) -> dict | None:
    """Retorna a última senha finalizada e ainda não avaliada de um operador."""
    finalizado = (
        Finalizado.query.filter_by(setor_id=setor_id, operador_id=operador_id)
        .filter((Finalizado.avaliacao.is_(None)) | (Finalizado.avaliacao == ""))
        .order_by(Finalizado.id.desc())
        .first()
    )
    if not finalizado:
        return None
    return _serializar_pendente(finalizado)


def buscar_avaliacao_pendente_setor(setor_id: int) -> dict | None:
    """Qualquer atendimento finalizado sem nota no setor (tablet de avaliação)."""
    finalizado = (
        Finalizado.query.filter_by(setor_id=setor_id)
        .filter((Finalizado.avaliacao.is_(None)) | (Finalizado.avaliacao == ""))
        .order_by(Finalizado.id.desc())
        .first()
    )
    if not finalizado:
        return None
    return _serializar_pendente(finalizado)


def _serializar_pendente(finalizado: Finalizado) -> dict:
    senha = Senha.query.get(finalizado.senha_id)
    operador = Operador.query.get(finalizado.operador_id)
    return {
        "senha_id": finalizado.senha_id,
        "senha": senha.senha if senha else None,
        "operador_id": finalizado.operador_id,
        "operador_nome": operador.nome if operador else None,
        "operador_foto": operador.foto_perfil if operador else None,
    }


def registrar_avaliacao(senha_id: int, setor_id: int, operador_id: int, nota) -> None:
    finalizado = (
        Finalizado.query.filter_by(senha_id=senha_id, setor_id=setor_id, operador_id=operador_id)
        .filter((Finalizado.avaliacao.is_(None)) | (Finalizado.avaliacao == ""))
        .first()
    )
    if not finalizado:
        raise AvaliacaoError("Avaliação já registrada ou atendimento não encontrado")
    finalizado.avaliacao = str(nota)
    senha = Senha.query.get(senha_id)
    if senha:
        senha.status = "F"
    db.session.commit()


def registrar_avaliacao_por_token(token_unico: str, nota: int) -> dict:
    """Avaliação pública do cliente do QR (sem sessão de operador)."""
    if nota < 1 or nota > 5:
        raise AvaliacaoError("Nota deve ser entre 1 e 5")

    senha = Senha.query.filter_by(token_unico=token_unico).first()
    if not senha:
        raise AvaliacaoError("Senha não encontrada")

    finalizado = (
        Finalizado.query.filter_by(senha_id=senha.id)
        .order_by(Finalizado.id.desc())
        .first()
    )
    if not finalizado:
        raise AvaliacaoError("Atendimento ainda não finalizado")

    if finalizado.avaliacao not in (None, ""):
        return {"ok": True, "ja_avaliado": True, "nota": finalizado.avaliacao}

    finalizado.avaliacao = str(nota)
    senha.status = "F"
    db.session.commit()
    return {"ok": True, "ja_avaliado": False, "nota": str(nota)}


def avaliacao_pendente_por_senha(senha_id: int) -> bool:
    finalizado = (
        Finalizado.query.filter_by(senha_id=senha_id)
        .order_by(Finalizado.id.desc())
        .first()
    )
    if not finalizado:
        return False
    return finalizado.avaliacao in (None, "")
