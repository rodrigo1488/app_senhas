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
        SECRET_KEY=os.getenv("APP_SECRET_KEY") or os.urandom(24),
        SQLALCHEMY_DATABASE_URI=database_uri,
        SQLALCHEMY_ENGINE_OPTIONS=engine_options,
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        UPLOAD_FOLDER=upload_folder,
        ALLOWED_EXTENSIONS={"png", "jpg", "jpeg", "gif", "webp"},
        MAX_FILE_SIZE=5 * 1024 * 1024,
        DB_PATH=db_path,
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 365,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
        JWT_ALGORITHM="HS256",
        SESSION_TOKEN_TTL_SECONDS=60 * 60 * 12,  # 12h para tokens de setor/app
        NOME_EMPRESA_PADRAO="TESTE",
        VAPID_PUBLIC_KEY=os.getenv("VAPID_PUBLIC_KEY", "m8SlKTywMoMWfmtEYVdH7SMWFOQjGeMMvP7Q-d8FSwY"),
        VAPID_PRIVATE_KEY=os.getenv("VAPID_PRIVATE_KEY", "OBrReW-zVxCF6JWKKRyQNNNkPbY-8plD2cFdajsJ-dk"),
        VAPID_EMAIL=os.getenv("VAPID_EMAIL", "seu-email@exemplo.com"),
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

    with app.app_context():
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

    app.register_blueprint(misc_bp)
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

    return app


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
    _migrate_tv_layout_column()

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
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_senhas_setor_status ON senhas (setor_id, status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_senhas_token_unico ON senhas (token_unico)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_senhas_data_hora ON senhas (data_hora)"))
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
