"""
Pacote da aplicação Flask "CompuFlow".

Este pacote substitui o antigo `backend/__init__.py` monolítico por uma estrutura modular:

- `app/extensions.py`   -> instâncias compartilhadas (SQLAlchemy, SocketIO)
- `backend/models.py`       -> modelos SQLAlchemy (mapeando o schema já existente do SQLite)
- `backend/auth.py`         -> autenticação do admin (sessão) e autenticação por código de
                            setor (token de sessão usado pela Web kiosk e pelo app Android)
- `backend/utils.py`        -> utilitários (imagens, QR Code, caminhos, nome da empresa)
- `backend/services/`       -> regras de negócio (fila, impressão, avaliação, empresa)
- `backend/sockets/`        -> protocolo de tempo real (ver documentacao/REALTIME_PROTOCOL.md)
- `backend/blueprints/`     -> rotas HTTP, organizadas por domínio
"""
import os
import sys

from flask import Flask
from flask_cors import CORS

from backend.extensions import db, socketio


def resource_path(relative_path: str) -> str:
    """Obtém o caminho absoluto para recursos, funciona para dev e PyInstaller."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def _base_dir() -> str:
    """Diretório raiz da API (`api/`), onde ficam templates/, static/ e o SQLite.

    Em desenvolvimento/Docker: pasta pai do pacote `backend/` (ou seja, `api/`).
    Em binário PyInstaller: pasta do executável.
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable) if hasattr(sys, "executable") else os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _resolve_database_config(sqlite_db_path: str) -> tuple[str, dict]:
    """Decide qual banco usar.

    Padrão: PostgreSQL, configurado via `DATABASE_URL` (formato
    `postgresql+psycopg2://usuario:senha@host:porta/banco`) — é o que o
    `docker-compose.yml` define para o serviço `api` apontando para o
    serviço `db`. Isso permite rodar a stack inteira com `docker compose up`.

    Fallback: se `DATABASE_URL` não estiver definida (ex.: dev local sem
    Docker), continua usando o `appsenhas.sqlite` em `api/`, para não quebrar
    quem só quer rodar `python app.py` rapidamente sem subir um Postgres.
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        # Compatibilidade com a variável padrão de alguns provedores de
        # Postgres gerenciado, que às vezes usam o esquema "postgres://"
        # (não suportado mais pelo SQLAlchemy 2.x, que exige "postgresql://").
        if database_url.startswith("postgres://"):
            database_url = "postgresql://" + database_url[len("postgres://"):]
        engine_options: dict = {"pool_pre_ping": True}
        return database_url, engine_options

    return f"sqlite:///{sqlite_db_path}", {"connect_args": {"timeout": 15}}


def _resolve_secret_key(instance_path: str) -> str:
    """Chave de assinatura (sessão Flask + JWT do app).

    Sem chave estável, todo restart/redeploy invalida os JWTs já emitidos
    ("Sessão inválida" no Android). Prioridade:

    1. `APP_SECRET_KEY` no ambiente (recomendado em produção)
    2. Arquivo `instance/secret_key` (sobrevive a redeploy se o volume
       `api_instance` estiver montado, como no docker-compose)
    3. Gera e grava um novo arquivo na primeira execução
    """
    env_key = (os.getenv("APP_SECRET_KEY") or "").strip()
    if env_key:
        return env_key

    os.makedirs(instance_path, exist_ok=True)
    path = os.path.join(instance_path, "secret_key")
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as fh:
            stored = fh.read().strip()
        if stored:
            return stored

    import secrets

    generated = secrets.token_hex(32)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(generated)
    return generated


def create_app(config_overrides: dict | None = None) -> Flask:
    """Application factory. Cria e configura a instância do Flask."""
    from dotenv import load_dotenv

    # Carrega .env da raiz do monorepo e, se existir, de api/.
    api_dir = _base_dir()
    repo_root = os.path.abspath(os.path.join(api_dir, ".."))
    load_dotenv(os.path.join(repo_root, ".env"))
    load_dotenv(os.path.join(api_dir, ".env"), override=True)

    if getattr(sys, "frozen", False):
        template_folder = resource_path("templates")
        static_folder = resource_path("static")
        app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    else:
        app = Flask(
            __name__,
            template_folder=os.path.join(api_dir, "templates"),
            static_folder=os.path.join(api_dir, "static"),
        )

    base_dir = api_dir
    db_path = os.path.join(base_dir, "appsenhas.sqlite")
    upload_folder = os.path.join(base_dir, "static", "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    database_uri, engine_options = _resolve_database_config(db_path)

    # Origens do painel Next (dev e Docker). Cookies de sessão precisam de
    # CORS com credentials quando o browser chama a API diretamente; em
    # produção o proxy Next/Caddy costuma unificar o domínio.
    cors_origins = [
        o.strip()
        for o in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000,http://web:3000",
        ).split(",")
        if o.strip()
    ]

    app.config.update(
        SECRET_KEY=_resolve_secret_key(app.instance_path),
        SQLALCHEMY_DATABASE_URI=database_uri,
        SQLALCHEMY_ENGINE_OPTIONS=engine_options,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=upload_folder,
        ALLOWED_EXTENSIONS={"png", "jpg", "jpeg", "gif", "webp"},
        ALLOWED_VIDEO_EXTENSIONS={"mp4"},
        MAX_FILE_SIZE=5 * 1024 * 1024,
        MAX_VIDEO_SIZE=80 * 1024 * 1024,
        MAX_CONTENT_LENGTH=400 * 1024 * 1024,
        DB_PATH=db_path,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 365,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
        JWT_ALGORITHM="HS256",
        # Tokens de setor/app não usam `exp` (ver create_session_token).
        # Só tokens de ação do operador passam ttl_seconds explícito.
        NOME_EMPRESA_PADRAO="TESTE",
        VAPID_PUBLIC_KEY=os.getenv("VAPID_PUBLIC_KEY", ""),
        VAPID_PRIVATE_KEY=os.getenv("VAPID_PRIVATE_KEY", ""),
        VAPID_EMAIL=os.getenv("VAPID_EMAIL", "admin@compuflow.local"),
        IMPRESSORA_PORTA=9100,
        PROPORCAO_NORMAIS=2,
        LIMITE_PREFERENCIAIS_ALERTA=3,
        CORS_ORIGINS=cors_origins,
    )
    if config_overrides:
        app.config.update(config_overrides)

    CORS(
        app,
        origins=cors_origins,
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        expose_headers=["Content-Type"],
    )
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    # O middleware WSGI do Engine.IO só reconhece `/socket.io/` (com barra).
    # O Next, com trailingSlash padrão, devolve 308 de `/socket.io/` → `/socket.io`
    # e o handshake cai em 404 (xhr poll error). Normalizamos o PATH_INFO antes
    # do middleware — e o Next usa skipTrailingSlashRedirect.
    _wrap_socketio_path_normalization(app)

    with app.app_context():
        from backend.services.push_service import ensure_vapid_keys

        ensure_vapid_keys()
        _init_database(app)

    from backend.blueprints.auth_bp import auth_bp
    from backend.blueprints.admin_bp import admin_bp
    from backend.blueprints.admin_api_bp import admin_api_bp
    from backend.blueprints.setores_bp import setores_bp
    from backend.blueprints.filas_bp import filas_bp
    from backend.blueprints.operador_bp import operador_bp
    from backend.blueprints.avaliacao_bp import avaliacao_bp
    from backend.blueprints.notificacao_bp import notificacao_bp
    from backend.blueprints.api_bp import api_bp
    from backend.blueprints.misc_bp import misc_bp
    from backend.blueprints.streaming_bp import streaming_bp

    app.register_blueprint(misc_bp)
    app.register_blueprint(streaming_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_api_bp)
    app.register_blueprint(setores_bp)
    app.register_blueprint(filas_bp)
    app.register_blueprint(operador_bp)
    app.register_blueprint(avaliacao_bp)
    app.register_blueprint(notificacao_bp)
    app.register_blueprint(api_bp)

    from backend.sockets import register_socket_handlers
    register_socket_handlers(socketio)

    from backend.services.fila_service import iniciar_rotina_virada_dia

    iniciar_rotina_virada_dia(app)

    return app


def _wrap_socketio_path_normalization(app: Flask) -> None:
    """Garante PATH_INFO `/socket.io` → `/socket.io/` antes do middleware Engine.IO."""
    inner = app.wsgi_app

    def _normalize(environ, start_response):
        path = environ.get("PATH_INFO") or ""
        if path == "/socket.io":
            environ = dict(environ)
            environ["PATH_INFO"] = "/socket.io/"
        return inner(environ, start_response)

    app.wsgi_app = _normalize


def _init_database(app: Flask) -> None:
    """Cria tabelas que ainda não existirem e garante índices.

    Os modelos em `backend/models.py` mapeiam o schema histórico do
    `appsenhas.sqlite` (ver `migrate_db.py`), e o mesmo schema é criado em
    PostgreSQL — os tipos usados (`Text`, `Integer`, `Boolean`, `DateTime`)
    são suportados de forma equivalente nos dois dialetos, então `create_all`
    funciona igual nos dois casos. Para migrar dados já existentes do SQLite
    legado para o Postgres, ver `scripts/migrate_sqlite_to_postgres.py`.
    """
    from sqlalchemy import text

    # Import necessário para registrar os modelos em `db.metadata` antes do
    # create_all() — sem isso, `create_all()` não sabe quais tabelas criar
    # (é um no-op silencioso). Isso não dava problema com o appsenhas.sqlite
    # legado porque as tabelas já existiam no arquivo de antes, mas falha
    # com um banco novo/vazio (ex.: Postgres recém-criado pelo Docker).
    import backend.models  # noqa: F401

    db.create_all()
    _migrate_operator_identification_columns()
    _migrate_propagandas_columns()
    _migrate_propaganda_tipo_column()
    _migrate_tv_layout_column()
    _migrate_tv_orientacao_column()
    _migrate_tipo_setor_column()
    _migrate_impressao_via_cliente_column()
    _migrate_usuario_papeis()

    is_sqlite = db.engine.dialect.name == "sqlite"

    with db.engine.connect() as conn:
        if is_sqlite:
            # PRAGMAs só existem no SQLite; no Postgres essas garantias
            # (WAL/foreign keys) já são o comportamento padrão do servidor.
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA foreign_keys=ON"))
        # Colunas novas de analytics — create_all() não ALTER em tabelas
        # já existentes; adiciona de forma idempotente nos dois dialetos.
        _ensure_column(conn, "senhas", "chamada_em", "TIMESTAMP" if not is_sqlite else "DATETIME", is_sqlite)
        _ensure_column(conn, "senhas", "finalizado_em", "TIMESTAMP" if not is_sqlite else "DATETIME", is_sqlite)
        _ensure_column(conn, "senhas", "pedido_em", "TIMESTAMP" if not is_sqlite else "DATETIME", is_sqlite)
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_senhas_setor_status ON senhas (setor_id, status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_senhas_token_unico ON senhas (token_unico)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_senhas_data_hora ON senhas (data_hora)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_qr_scans_setor_scanned_at ON qr_scans (setor_id, scanned_at)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_atendimento_setor_operador ON atendimento_atual (setor_id, operador_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_finalizados_setor_operador ON finalizados (setor_id, operador_id)"))
        conn.commit()

    _backfill_setor_propagandas()
    _seed_admin_padrao(app)


def _migrate_operator_identification_columns() -> None:
    """Adiciona, de forma idempotente, campos novos em SQLite e PostgreSQL."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    setores_columns = {column["name"] for column in inspector.get_columns("setores")}
    operadores_columns = {column["name"] for column in inspector.get_columns("operadores")}
    if_not_exists = "IF NOT EXISTS " if db.engine.dialect.name == "postgresql" else ""

    with db.engine.begin() as conn:
        if "modo_identificacao_operador" not in setores_columns:
            conn.execute(
                text(
                    f"ALTER TABLE setores ADD COLUMN {if_not_exists}"
                    "modo_identificacao_operador VARCHAR(10) NOT NULL DEFAULT 'foto'"
                )
            )
        if "pin_hash" not in operadores_columns:
            conn.execute(
                text(f"ALTER TABLE operadores ADD COLUMN {if_not_exists}pin_hash TEXT")
            )


def _migrate_propagandas_columns() -> None:
    """Garante coluna de toggle por setor (tabela propagandas vem do create_all)."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    setores_columns = {column["name"] for column in inspector.get_columns("setores")}
    if_not_exists = "IF NOT EXISTS " if db.engine.dialect.name == "postgresql" else ""
    bool_default = "FALSE" if db.engine.dialect.name == "postgresql" else "0"

    with db.engine.begin() as conn:
        if "propagandas_ativas" not in setores_columns:
            conn.execute(
                text(
                    f"ALTER TABLE setores ADD COLUMN {if_not_exists}"
                    f"propagandas_ativas BOOLEAN NOT NULL DEFAULT {bool_default}"
                )
            )
        if "propagandas_cliente_ativas" not in setores_columns:
            conn.execute(
                text(
                    f"ALTER TABLE setores ADD COLUMN {if_not_exists}"
                    f"propagandas_cliente_ativas BOOLEAN NOT NULL DEFAULT {bool_default}"
                )
            )


def _migrate_propaganda_tipo_column() -> None:
    """Garante `propagandas.tipo` (image|video) em instalações já existentes."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "propagandas" not in inspector.get_table_names():
        return
    propaganda_columns = {column["name"] for column in inspector.get_columns("propagandas")}
    if_not_exists = "IF NOT EXISTS " if db.engine.dialect.name == "postgresql" else ""

    with db.engine.begin() as conn:
        if "tipo" not in propaganda_columns:
            conn.execute(
                text(
                    f"ALTER TABLE propagandas ADD COLUMN {if_not_exists}"
                    "tipo VARCHAR(10) NOT NULL DEFAULT 'image'"
                )
            )


def _migrate_tv_layout_column() -> None:
    """Garante a preferência de layout exclusiva do painel TV web."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    setores_columns = {column["name"] for column in inspector.get_columns("setores")}
    if_not_exists = "IF NOT EXISTS " if db.engine.dialect.name == "postgresql" else ""

    with db.engine.begin() as conn:
        if "layout_tv_web" not in setores_columns:
            conn.execute(
                text(
                    f"ALTER TABLE setores ADD COLUMN {if_not_exists}"
                    "layout_tv_web VARCHAR(20) NOT NULL DEFAULT 'propaganda'"
                )
            )


def _migrate_tv_orientacao_column() -> None:
    """Garante a preferência de orientação da tela da TV (horizontal/vertical)."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "setores" not in inspector.get_table_names():
        return
    setores_columns = {column["name"] for column in inspector.get_columns("setores")}
    if_not_exists = "IF NOT EXISTS " if db.engine.dialect.name == "postgresql" else ""

    with db.engine.begin() as conn:
        if "orientacao_tv" not in setores_columns:
            conn.execute(
                text(
                    f"ALTER TABLE setores ADD COLUMN {if_not_exists}"
                    "orientacao_tv VARCHAR(20) NOT NULL DEFAULT 'horizontal'"
                )
            )


def _migrate_tipo_setor_column() -> None:
    """Garante `setores.tipo_setor` (atendimento|streaming). Existentes = atendimento."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "setores" not in inspector.get_table_names():
        return
    setores_columns = {column["name"] for column in inspector.get_columns("setores")}
    if_not_exists = "IF NOT EXISTS " if db.engine.dialect.name == "postgresql" else ""

    with db.engine.begin() as conn:
        if "tipo_setor" not in setores_columns:
            conn.execute(
                text(
                    f"ALTER TABLE setores ADD COLUMN {if_not_exists}"
                    "tipo_setor VARCHAR(20) NOT NULL DEFAULT 'atendimento'"
                )
            )
        conn.execute(
            text(
                "UPDATE setores SET tipo_setor = 'atendimento' "
                "WHERE tipo_setor IS NULL OR tipo_setor = ''"
            )
        )


def _migrate_impressao_via_cliente_column() -> None:
    """Toggle por setor: impressão do cupom pelo tablet do cliente (LAN local)."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    if "setores" not in inspector.get_table_names():
        return
    setores_columns = {column["name"] for column in inspector.get_columns("setores")}
    if_not_exists = "IF NOT EXISTS " if db.engine.dialect.name == "postgresql" else ""
    bool_default = "FALSE" if db.engine.dialect.name == "postgresql" else "0"

    with db.engine.begin() as conn:
        if "impressao_via_cliente" not in setores_columns:
            conn.execute(
                text(
                    f"ALTER TABLE setores ADD COLUMN {if_not_exists}"
                    f"impressao_via_cliente BOOLEAN NOT NULL DEFAULT {bool_default}"
                )
            )


def _backfill_setor_propagandas() -> None:
    """Preserva a galeria global existente na primeira migração para vínculos por setor."""
    from sqlalchemy import text

    migration_key = "setor_propagandas_migrado_v1"
    with db.engine.begin() as conn:
        migrated = conn.execute(
            text("SELECT 1 FROM configuracoes WHERE chave = :chave LIMIT 1"),
            {"chave": migration_key},
        ).first()
        if migrated:
            return
        conn.execute(
            text(
                "INSERT INTO setor_propagandas (setor_id, propaganda_id) "
                "SELECT setores.id, propagandas.id FROM setores CROSS JOIN propagandas"
            )
        )
        conn.execute(
            text(
                "INSERT INTO configuracoes (chave, valor, descricao, data_atualizacao) "
                "VALUES (:chave, '1', :descricao, CURRENT_TIMESTAMP)"
            ),
            {
                "chave": migration_key,
                "descricao": "Migração da galeria global para propagandas por setor",
            },
        )


def _migrate_usuario_papeis() -> None:
    """Colunas de papel/nome em usuarios + tabela usuario_setores."""
    from sqlalchemy import inspect, text

    inspector = inspect(db.engine)
    tables = set(inspector.get_table_names())
    if "usuarios" not in tables:
        return
    cols = {c["name"] for c in inspector.get_columns("usuarios")}
    is_pg = db.engine.dialect.name == "postgresql"
    if_not_exists = "IF NOT EXISTS " if is_pg else ""

    with db.engine.begin() as conn:
        if "papel" not in cols:
            conn.execute(
                text(
                    f"ALTER TABLE usuarios ADD COLUMN {if_not_exists}"
                    "papel VARCHAR(20) NOT NULL DEFAULT 'admin'"
                )
            )
        if "nome" not in cols:
            conn.execute(
                text(
                    f"ALTER TABLE usuarios ADD COLUMN {if_not_exists}nome TEXT"
                )
            )
        if "usuario_setores" not in tables:
            if is_pg:
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS usuario_setores (
                            usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
                            setor_id INTEGER NOT NULL REFERENCES setores(id),
                            PRIMARY KEY (usuario_id, setor_id)
                        )
                        """
                    )
                )
            else:
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS usuario_setores (
                            usuario_id INTEGER NOT NULL,
                            setor_id INTEGER NOT NULL,
                            PRIMARY KEY (usuario_id, setor_id),
                            FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
                            FOREIGN KEY(setor_id) REFERENCES setores(id)
                        )
                        """
                    )
                )
        conn.execute(text("UPDATE usuarios SET papel = 'admin' WHERE papel IS NULL OR papel = ''"))


def _ensure_column(conn, table: str, column: str, col_type: str, is_sqlite: bool) -> None:
    """ADD COLUMN idempotente (SQLite não tem IF NOT EXISTS em todas as versões)."""
    from sqlalchemy import text

    if is_sqlite:
        rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        existing = {r[1] for r in rows}
        if column not in existing:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
    else:
        conn.execute(
            text(
                f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}"
            )
        )


def _seed_admin_padrao(app: Flask) -> None:
    """Garante que exista pelo menos um usuário administrador.

    Se a tabela `usuarios` estiver vazia (instalação nova), cria um admin
    padrão com as credenciais de `ADMIN_EMAIL`/`ADMIN_PASSWORD` (ou os
    valores padrão abaixo, se as variáveis não forem definidas). Isso
    permite acessar o painel `/login` logo após o primeiro
    `docker compose up`, sem depender de nenhum serviço externo.

    IMPORTANTE: troque a senha padrão após o primeiro login (não há hoje
    uma tela de "alterar senha" no painel — use
    `scripts/criar_admin.py <email> <nova_senha>` para isso).
    """
    from backend.services.usuario_service import criar_ou_atualizar_admin, existe_algum_admin

    if existe_algum_admin():
        return

    admin_email = os.getenv("ADMIN_EMAIL", "admin@compuflow.local")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    criar_ou_atualizar_admin(admin_email, admin_password)
    app.logger.warning(
        "Nenhum usuário admin encontrado — criado usuário padrão '%s' / senha "
        "'%s'. TROQUE a senha após o primeiro login (script "
        "scripts/criar_admin.py). Defina ADMIN_EMAIL/ADMIN_PASSWORD antes do "
        "primeiro boot para customizar.",
        admin_email,
        admin_password,
    )
