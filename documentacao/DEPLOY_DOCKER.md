# Deploy com Docker + PostgreSQL

O backend Flask passou a rodar em container, com **PostgreSQL** como banco de
dados padrão (substituindo o `appsenhas.sqlite` legado, que continua
disponível apenas como fallback de desenvolvimento sem Docker — ver seção
["Rodando sem Docker"](#rodando-sem-docker)).

## Arquivos envolvidos

| Arquivo | Papel |
|---|---|
| `Dockerfile` | Imagem do backend (Python 3.12 + Gunicorn + worker eventlet) |
| `docker-compose.yml` | Orquestra os serviços `db` (Postgres 16) e `backend` |
| `.dockerignore` | Evita copiar `.venv`, `APPSENHAS/`, `.git`, etc. para a imagem |
| `.env` / `.env.example` | Variáveis de ambiente (senhas, chaves, Supabase, VAPID) |
| `backend/__init__.py` | `_resolve_database_config()` decide SQLite vs Postgres |
| `scripts/migrate_sqlite_to_postgres.py` | Migra os dados do `appsenhas.sqlite` existente para o Postgres |

## Subindo a stack

```bash
cp .env.example .env
# edite .env: defina POSTGRES_PASSWORD, APP_SECRET_KEY, e as credenciais
# de Supabase/VAPID que já estavam em uso.

docker compose up --build
```

Isso sobe dois containers:

- **`db`**: PostgreSQL 16, com os dados persistidos no volume `postgres_data`
  (sobrevive a `docker compose down` — para apagar de vez, use
  `docker compose down -v`).
- **`backend`**: a aplicação Flask + Socket.IO, servida por Gunicorn com um
  worker eventlet, na porta `5000`. As fotos de operador enviadas pelo admin
  ficam no volume `uploads_data` (`/app/static/uploads` dentro do container),
  para não se perderem a cada rebuild da imagem.

O backend só inicia depois que o Postgres responde ao `pg_isready`
(`depends_on: condition: service_healthy` no `docker-compose.yml`).

Ao subir por cima de um banco Postgres vazio, o backend cria o schema
automaticamente (`db.create_all()` em `backend/__init__.py::_init_database`)
— nenhuma migration manual é necessária para uma instalação nova.

## Migrando dados existentes do SQLite

Se você já tem um `appsenhas.sqlite` com dados reais (setores, operadores,
senhas, avaliações) e quer preservá-los ao migrar para o Postgres do
`docker-compose.yml`:

```bash
# 1. Suba só o banco:
docker compose up -d db

# 2. Rode a migração (localmente, com o Postgres exposto em localhost:5432
#    pelo docker-compose.yml, ou de dentro de um container com acesso à rede
#    do compose):
DATABASE_URL=postgresql+psycopg2://appsenhas:SUA_SENHA@localhost:5432/appsenhas \
    python scripts/migrate_sqlite_to_postgres.py

# 3. Suba o backend normalmente:
docker compose up -d backend
```

O script (`scripts/migrate_sqlite_to_postgres.py`):
- Cria o schema no Postgres (reaproveita `create_app()`);
- Copia os dados tabela por tabela, preservando os `id` originais (essencial
  para manter as chaves estrangeiras entre `senhas`, `atendimento_atual` e
  `finalizados` intactas);
- Ajusta as sequences do Postgres para continuarem depois do maior `id`
  migrado;
- Pula tabelas que já têm dados no destino (evita duplicar em uma segunda
  execução); use `--forcar` para truncar e migrar de novo do zero.

## Variáveis de ambiente

Ver `.env.example` para a lista completa. As mais relevantes para o Docker:

| Variável | Uso |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Credenciais do container `db`; usadas também para montar o `DATABASE_URL` do `backend` |
| `DATABASE_URL` | Só precisa ser definida manualmente se você **não** usar o `docker-compose.yml` (ex.: Postgres gerenciado externo) |
| `APP_SECRET_KEY` | Chave de sessão do Flask (defina algo aleatório e fixo em produção) |
| `SUPABASE_URL` / `SUPABASE_KEY` | Login do painel admin (ver `backend/blueprints/auth_bp.py`) |
| `VAPID_*` | Notificações Web Push |

## Por que um único worker eventlet?

O Flask-SocketIO com `eventlet` mantém o estado das *rooms* (setor, ticket,
avaliação — ver `documentacao/REALTIME_PROTOCOL.md`) na memória do processo.
Com mais de um worker Gunicorn, cada processo teria sua própria cópia
dessas rooms, e um cliente conectado ao worker A nunca receberia eventos
emitidos a partir de uma requisição atendida pelo worker B — quebraria o
tempo real. Rodar múltiplos workers exigiria um message queue externo
(Redis, via `socketio.init_app(app, message_queue=...)`), o que não é
necessário para o volume de uso desta aplicação (fila de senhas de um único
setor/estabelecimento por instância).

## Rodando sem Docker

Se `DATABASE_URL` não estiver definida, `backend/__init__.py` continua
usando o `appsenhas.sqlite` da raiz do repo — o mesmo comportamento de
antes da migração para Postgres. Isso serve para quem só quer rodar
`python app.py` rapidamente em desenvolvimento, sem subir um Postgres.

## Verificando que subiu corretamente

```bash
curl http://localhost:5000/api/v1/health
# {"status": "ok"}
```

Os logs de cada serviço: `docker compose logs -f backend` / `docker compose logs -f db`.
