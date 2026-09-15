# Deploy com Docker + PostgreSQL

Monorepo: **`api`** (Flask), **`web`** (Next admin), **`db`** (Postgres 16).

## Arquivos

| Arquivo | Papel |
|---|---|
| `api/Dockerfile` | Imagem da API (Python 3.12 + Gunicorn + eventlet) |
| `web/Dockerfile` | Imagem do painel Next.js (standalone) |
| `docker-compose.yml` | Serviços `db`, `api`, `web` |
| `.env` / `.env.example` | Senhas, chaves, URLs |
| `api/backend/__init__.py` | SQLite vs Postgres via `DATABASE_URL` |
| `api/scripts/migrate_sqlite_to_postgres.py` | Migra SQLite legado → Postgres |

## Subindo a stack

```bash
cp .env.example .env
# edite POSTGRES_PASSWORD, APP_SECRET_KEY, ADMIN_PASSWORD

docker compose up --build -d
```

| Serviço | Porta | Função |
|---------|-------|--------|
| `web` | **3000** | Painel admin Next.js (sidebar) |
| `api` | **5000** | Flask: kiosk, `/api/v1/*`, Socket.IO |
| `db` | 5432 | PostgreSQL |

Volumes: `postgres_data`, `uploads_data` (fotos de operadores).

O schema é criado automaticamente em banco vazio (`db.create_all()`).

## Admin padrão

Na primeira inicialização, se a tabela `usuarios` estiver vazia:

- Email: `ADMIN_EMAIL` (padrão `admin@compuflow.local`)
- Senha: `ADMIN_PASSWORD` (padrão `admin123`)

Login do painel: **http://localhost:3000/login**

A autenticação continua sendo **sessão Flask** (cookies). O Next faz rewrite
de `/api/v1/*` para a API, então o browser só fala com a porta 3000 para o
admin.

Trocar senha:

```bash
docker compose exec api python scripts/criar_admin.py admin@compuflow.local "senha-nova-forte"
```

## Migrando SQLite → Postgres

Com a stack no ar e `appsenhas.sqlite` disponível (ex.: em `api/`):

```bash
docker compose exec -e DATABASE_URL=postgresql+psycopg2://appsenhas:SENHA@db:5432/appsenhas \
  api python scripts/migrate_sqlite_to_postgres.py /caminho/appsenhas.sqlite
```

(Em host local, monte o arquivo ou copie para o container.)

## Rodando sem Docker

**API** (`cd api && python app.py`) — sem `DATABASE_URL` usa `api/appsenhas.sqlite`.

**Web** (Node >= 20):

```bash
cd web
npm install
API_INTERNAL_URL=http://127.0.0.1:5000 npm run dev
```

## Notas

- Um único worker eventlet no Gunicorn (rooms Socket.IO não compartilham
  memória entre workers sem Redis).
- Kiosk HTML (`/senhas`, `/senha_atual`, etc.) continua na API Flask.
- Rotas Jinja `/admin` e `/login` redirecionam para o Next (`ADMIN_WEB_URL`).
- QR do cliente: `{ADMIN_WEB_URL}/acompanhar/<token>` (ver README_NOTIFICACOES).
- No boot, a API adiciona colunas `senhas.chamada_em` / `senhas.finalizado_em`
  se ainda não existirem (necessário para métricas de espera do dashboard).
- Abandono operacional: senhas `A` há mais de 30 min (configurável). Ver
  seção Analytics no [README](../README.md).
