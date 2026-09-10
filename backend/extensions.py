"""Instâncias de extensões compartilhadas entre os módulos do pacote `backend`.

Mantidas em um módulo isolado para evitar import circular entre
`backend/__init__.py`, `backend/models.py`, `backend/blueprints/*` e `backend/sockets/*`.
"""
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO

db = SQLAlchemy()
socketio = SocketIO()
