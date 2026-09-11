# AppSenhas — monorepo

Sistema de senhas / filas: API Flask + painel admin Next.js + app Android.

## Estrutura

```
api/            Flask + Socket.IO (kiosk web, API REST, sockets)
web/            Next.js — painel administrativo (sidebar shadcn)
app/            Android (Kotlin + Compose) — Cliente/Operador/Avaliação/TV
documentacao/   Guias e protocolo de tempo real
```

## Subir com Docker

```bash
cp .env.example .env
docker compose up --build -d
```

| Serviço | URL |
|---------|-----|
| Painel admin (Next) | http://localhost:3000 |
| API / kiosk Flask | http://localhost:5000 |
| Postgres | localhost:5432 |

Admin padrão (primeira subida): `ADMIN_EMAIL` / `ADMIN_PASSWORD` do `.env`
(padrão `admin@appsenhas.local` / `admin123`).

Trocar senha:

```bash
docker compose exec api python scripts/criar_admin.py admin@empresa.com "senha-nova"
```

## Dev sem Docker

**API** (na pasta `api/`):

```bash
cd api
python -m venv ../.venv && source ../.venv/bin/activate
pip install -r requirements.txt
python app.py   # http://localhost:5000
```

Sem `DATABASE_URL`, usa `api/appsenhas.sqlite`.

**Web** (Node **>= 20**):

```bash
cd web
npm install
API_INTERNAL_URL=http://127.0.0.1:5000 npm run dev   # http://localhost:3000
```

O Next faz *rewrite* de `/api/v1/*` e `/uploads/*` para a API Flask, assim os
cookies de sessão do admin funcionam no mesmo host do painel.

**Android**: abrir a pasta `app/` no Android Studio.

## Auth do admin

Sessão Flask (cookie `session` + `user_id`) — sem JWT no painel. Endpoints JSON
em `/api/v1/admin/*` (ver `api/backend/blueprints/admin_api_bp.py`).

## Documentação

- [documentacao/DEPLOY_DOCKER.md](documentacao/DEPLOY_DOCKER.md)
- [documentacao/REALTIME_PROTOCOL.md](documentacao/REALTIME_PROTOCOL.md)
- [documentacao/README.md](documentacao/README.md)
