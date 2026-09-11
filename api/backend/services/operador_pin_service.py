"""Cadastro e validação segura do PIN numérico dos operadores."""
from werkzeug.security import check_password_hash, generate_password_hash

from backend.models import Operador

PIN_LENGTH = 4


class OperadorPinError(ValueError):
    pass


def validar_formato_pin(pin: str) -> str:
    pin = (pin or "").strip()
    if not pin.isdigit() or len(pin) != PIN_LENGTH:
        raise OperadorPinError("O PIN deve conter exatamente 4 números")
    return pin


def garantir_pin_unico_no_setor(pin: str, setor_id: int, ignorar_operador_id: int | None = None) -> None:
    for operador in Operador.query.filter_by(setor_id=setor_id).all():
        if operador.id == ignorar_operador_id or not operador.pin_hash:
            continue
        if check_password_hash(operador.pin_hash, pin):
            raise OperadorPinError("Este PIN já pertence a outro operador do setor")


def definir_pin(operador: Operador, pin: str, setor_id: int | None = None) -> None:
    pin = validar_formato_pin(pin)
    setor = setor_id if setor_id is not None else operador.setor_id
    if setor is None:
        raise OperadorPinError("Selecione o setor antes de definir o PIN")
    garantir_pin_unico_no_setor(pin, int(setor), operador.id)
    operador.pin_hash = generate_password_hash(pin)


def identificar_operador_por_pin(setor_id: int, pin: str) -> Operador | None:
    try:
        pin = validar_formato_pin(pin)
    except OperadorPinError:
        return None
    for operador in Operador.query.filter_by(setor_id=setor_id).all():
        if operador.pin_hash and check_password_hash(operador.pin_hash, pin):
            return operador
    return None
