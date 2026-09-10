"""Protocolo de tempo real (ver documentacao/REALTIME_PROTOCOL.md).

`register_socket_handlers` é chamado uma vez, em `app.create_app`.
"""


def register_socket_handlers(socketio) -> None:
    """Importa o módulo de handlers para que os decorators `@socketio.on(...)`
    sejam registrados. `socketio` aqui é a mesma instância de
    `backend.extensions.socketio` usada dentro de `handlers.py`."""
    from backend.sockets import handlers  # noqa: F401
