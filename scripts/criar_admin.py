#!/usr/bin/env python3
"""Cria um usuário administrador do painel, ou atualiza a senha se o email
já existir. Útil para trocar a senha do admin padrão (ver
`backend/__init__.py::_seed_admin_padrao`) ou criar administradores extras.

Uso local (fora do Docker):
    python scripts/criar_admin.py admin@empresa.com "senha-nova" ["Nome da Empresa"]

Uso dentro do container (com a stack já rodando via docker-compose):
    docker compose exec backend python scripts/criar_admin.py admin@empresa.com "senha-nova"
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> None:
    if len(sys.argv) < 3:
        print(f"Uso: python {sys.argv[0]} <email> <senha> [nome_empresa]")
        sys.exit(1)

    email = sys.argv[1]
    senha = sys.argv[2]
    nome_empresa = sys.argv[3] if len(sys.argv) > 3 else None

    import eventlet

    eventlet.monkey_patch()

    from backend import create_app
    from backend.services.usuario_service import criar_ou_atualizar_admin

    app = create_app()
    with app.app_context():
        usuario = criar_ou_atualizar_admin(email, senha, nome_empresa)
        print(f"✅ Usuário admin '{usuario.email}' (id={usuario.id}) criado/atualizado com sucesso.")


if __name__ == "__main__":
    main()
