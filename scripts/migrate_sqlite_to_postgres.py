#!/usr/bin/env python3
"""Migra os dados do `appsenhas.sqlite` legado para o PostgreSQL.

Uso:
    DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/appsenhas \
        python scripts/migrate_sqlite_to_postgres.py [caminho_do_sqlite]

O que este script faz:
1. Usa a mesma `create_app()` do backend (com `DATABASE_URL` apontando para o
   Postgres de destino) para criar o schema no Postgres — reaproveita
   exatamente os mesmos modelos/índices que o servidor usa em produção
   (ver `backend/__init__.py::_init_database`).
2. Lê cada tabela do `appsenhas.sqlite` de origem (linha a linha, com
   `sqlite3.Row`) e insere no Postgres via SQLAlchemy, preservando os `id`
   originais (necessário para manter as chaves estrangeiras entre
   `senhas`, `atendimento_atual`, `finalizados`, etc. intactas).
3. Ajusta as sequences do Postgres (`nextval`) para continuar depois do
   maior `id` migrado, senão o próximo INSERT feito pela aplicação colidiria
   com um id já existente.

Por segurança, se uma tabela de destino já tiver linhas, ela é pulada (para
não duplicar dados em uma migração rodada por engano duas vezes). Use
`--forcar` para truncar e migrar novamente do zero.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys

# Garante que o pacote `backend` seja importável quando o script é chamado
# como `python scripts/migrate_sqlite_to_postgres.py` a partir da raiz do repo.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Ordem importa: tabelas com FK vêm depois das tabelas que elas referenciam.
TABELAS_EM_ORDEM = [
    "setores",
    "operadores",
    "impressoras",
    "senhas",
    "atendimento_atual",
    "finalizados",
    "configuracoes",
]


def _linhas_sqlite(conn: sqlite3.Connection, tabela: str) -> list[sqlite3.Row]:
    cursor = conn.execute(f"SELECT * FROM {tabela}")
    return cursor.fetchall()


def _tabela_existe_sqlite(conn: sqlite3.Connection, tabela: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (tabela,)
    ).fetchone()
    return row is not None


def migrar(sqlite_path: str, forcar: bool) -> None:
    if not os.path.exists(sqlite_path):
        print(f"❌ Arquivo SQLite não encontrado: {sqlite_path}")
        sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Defina DATABASE_URL apontando para o Postgres de destino, ex.:")
        print("   DATABASE_URL=postgresql+psycopg2://appsenhas:appsenhas@localhost:5432/appsenhas")
        sys.exit(1)

    import eventlet

    eventlet.monkey_patch()

    from backend import create_app
    from backend.extensions import db
    from backend.models import AtendimentoAtual, Configuracao, Finalizado, Impressora, Operador, Senha, Setor

    modelo_por_tabela = {
        "setores": Setor,
        "operadores": Operador,
        "impressoras": Impressora,
        "senhas": Senha,
        "atendimento_atual": AtendimentoAtual,
        "finalizados": Finalizado,
        "configuracoes": Configuracao,
    }

    app = create_app({"SQLALCHEMY_DATABASE_URI": database_url})

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    with app.app_context():
        from sqlalchemy import text

        for tabela in TABELAS_EM_ORDEM:
            modelo = modelo_por_tabela[tabela]

            if not _tabela_existe_sqlite(sqlite_conn, tabela):
                print(f"⚠️  Tabela '{tabela}' não existe no SQLite de origem — pulando.")
                continue

            total_destino = db.session.query(modelo).count()
            if total_destino > 0:
                if not forcar:
                    print(f"↷ '{tabela}' já tem {total_destino} linha(s) no Postgres — pulando (use --forcar para truncar e migrar de novo).")
                    continue
                print(f"🗑️  Truncando '{tabela}' no Postgres (--forcar)...")
                db.session.execute(text(f"TRUNCATE TABLE {tabela} RESTART IDENTITY CASCADE"))
                db.session.commit()

            linhas = _linhas_sqlite(sqlite_conn, tabela)
            if not linhas:
                print(f"— '{tabela}': nenhuma linha para migrar.")
                continue

            colunas_modelo = {c.name for c in modelo.__table__.columns}
            objetos = []
            for linha in linhas:
                dados = {chave: linha[chave] for chave in linha.keys() if chave in colunas_modelo}
                objetos.append(modelo(**dados))

            db.session.bulk_save_objects(objetos)
            db.session.commit()
            print(f"✅ '{tabela}': {len(objetos)} linha(s) migrada(s).")

            # Como os `id` originais foram preservados, a sequence do Postgres
            # (usada pelo próximo INSERT sem id explícito) precisa ser
            # avançada manualmente até o maior id migrado.
            db.session.execute(
                text(
                    f"SELECT setval(pg_get_serial_sequence('{tabela}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {tabela}), 1))"
                )
            )
            db.session.commit()

    sqlite_conn.close()
    print("\n🎉 Migração concluída.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "sqlite_path",
        nargs="?",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "appsenhas.sqlite"),
        help="Caminho do appsenhas.sqlite de origem (padrão: raiz do repo)",
    )
    parser.add_argument(
        "--forcar",
        action="store_true",
        help="Trunca as tabelas de destino no Postgres antes de migrar, mesmo que já tenham dados",
    )
    args = parser.parse_args()
    migrar(args.sqlite_path, args.forcar)
