"""
Pacote da aplicação Flask "App Senhas".

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
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable) if hasattr(sys, "executable") else os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(".")


def _resolve_database_config(sqlite_db_path: str) -> tuple[str, dict]:
    """Decide qual banco usar.

    Padrão: PostgreSQL, configurado via `DATABASE_URL` (formato
    `postgresql+psycopg2://usuario:senha@host:porta/banco`) — é o que o
    `docker-compose.yml` define para o serviço `backend` apontando para o
    serviço `db`. Isso permite rodar a stack inteira com `docker compose up`.

    Fallback: se `DATABASE_URL` não estiver definida (ex.: dev local sem
    Docker), continua usando o `appsenhas.sqlite` legado, para não quebrar
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
    load_dotenv()

    if getattr(sys, "frozen", False):
        template_folder = resource_path("templates")
        static_folder = resource_path("static")
        app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
    else:
        app = Flask(
            __name__,
            template_folder=os.path.join(os.path.abspath("."), "templates"),
            static_folder=os.path.join(os.path.abspath("."), "static"),
        )

    base_dir = _base_dir()
    db_path = os.path.join(base_dir, "appsenhas.sqlite")
    upload_folder = os.path.join(base_dir, "static", "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    database_uri, engine_options = _resolve_database_config(db_path)

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
        JWT_ALGORITHM="HS256",
        SESSION_TOKEN_TTL_SECONDS=60 * 60 * 12,  # 12h para tokens de setor/app
        NOME_EMPRESA_PADRAO="TESTE",
        VAPID_PUBLIC_KEY=os.getenv("VAPID_PUBLIC_KEY", "m8SlKTywMoMWfmtEYVdH7SMWFOQjGeMMvP7Q-d8FSwY"),
        VAPID_PRIVATE_KEY=os.getenv("VAPID_PRIVATE_KEY", "OBrReW-zVxCF6JWKKRyQNNNkPbY-8plD2cFdajsJ-dk"),
        VAPID_EMAIL=os.getenv("VAPID_EMAIL", "seu-email@exemplo.com"),
        IMPRESSORA_PORTA=9100,
        PROPORCAO_NORMAIS=2,
        LIMITE_PREFERENCIAIS_ALERTA=3,
    )
    if config_overrides:
        app.config.update(config_overrides)

    CORS(app)
    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    with app.app_context():
        _init_database(app)

    from backend.blueprints.auth_bp import auth_bp
    from backend.blueprints.admin_bp import admin_bp
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

    is_sqlite = db.engine.dialect.name == "sqlite"

    with db.engine.connect() as conn:
        if is_sqlite:
            # PRAGMAs só existem no SQLite; no Postgres essas garantias
            # (WAL/foreign keys) já são o comportamento padrão do servidor.
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_senhas_setor_status ON senhas (setor_id, status)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_senhas_token_unico ON senhas (token_unico)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_atendimento_setor_operador ON atendimento_atual (setor_id, operador_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_finalizados_setor_operador ON finalizados (setor_id, operador_id)"))
        conn.commit()

    _seed_admin_padrao(app)


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

    admin_email = os.getenv("ADMIN_EMAIL", "admin@appsenhas.local")
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
