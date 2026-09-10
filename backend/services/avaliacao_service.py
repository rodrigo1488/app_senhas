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
    senha = Senha.query.get(finalizado.senha_id)
    operador = Operador.query.get(operador_id)
    return {
        "senha_id": finalizado.senha_id,
        "senha": senha.senha if senha else None,
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
