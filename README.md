# App Senhas

Sistema de gerenciamento de fila de senhas (tipo "guichê"/recepção): clientes
retiram uma senha, operadores chamam a próxima, uma tela de TV mostra as
chamadas em tempo real e o cliente pode avaliar o atendimento — tudo
sincronizado via Socket.IO, sem polling.

## Estrutura do projeto

```
backend/                 Aplicação Flask (app factory, blueprints, services, sockets)
  blueprints/            Rotas HTTP: admin, auth, api (REST para o app Android), etc.
  services/              Regras de negócio (fila, impressão, avaliação)
  sockets/                Handlers e emissores de eventos Socket.IO
templates/               Painel admin (Jinja2) e telas web de fallback (kiosk)
static/                  CSS/JS/imagens do painel admin e das telas web
APPSENHAS/               App Android (Kotlin + Jetpack Compose) — Cliente/Operador/Avaliação/TV
documentacao/            Documentação técnica (protocolo Socket.IO, deploy, etc.)
scripts/                 Scripts utilitários (ex.: migração SQLite -> PostgreSQL)
app.py                   Ponto de entrada do backend (mantido na raiz por compatibilidade com o build PyInstaller)
Dockerfile / docker-compose.yml   Deploy em container (backend + PostgreSQL)
```

## Como rodar

### Com Docker (recomendado)

```bash
cp .env.example .env   # edite as senhas/chaves
docker compose up --build
```

Backend disponível em `http://localhost:5000`. Detalhes, variáveis de
ambiente e como migrar dados de uma instalação antiga (SQLite) para o
Postgres do container: ver [`documentacao/DEPLOY_DOCKER.md`](documentacao/DEPLOY_DOCKER.md).

### Localmente, sem Docker (dev rápido)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env    # opcional; sem DATABASE_URL, usa o appsenhas.sqlite local
python app.py
```

Sem `DATABASE_URL` definida, o backend usa automaticamente o
`appsenhas.sqlite` da raiz do repo (comportamento legado, mantido só para
esse cenário de dev sem Docker — em produção o banco é sempre PostgreSQL).

## App Android

O app Android (`APPSENHAS/`) substitui as telas de kiosk (`templates/senhas.html`,
`operador.html`, etc.) para uso em tablets/celulares: login por código do
setor, seleção de papel (Cliente/Operador/Avaliação/TV), e cada tela consome
a API REST (`backend/blueprints/api_bp.py`) + Socket.IO para tempo real. Ver
[`documentacao/REALTIME_PROTOCOL.md`](documentacao/REALTIME_PROTOCOL.md) para
o contrato completo entre backend e clientes.

## Painel administrativo

Acesse `/login` para gerenciar setores, operadores, impressoras,
configurações da fila e ver o dashboard de atendimentos/avaliações. A
autenticação é local (tabela `usuarios`) — um admin padrão
(`admin@appsenhas.local` / `admin123`, customizável via `ADMIN_EMAIL`/
`ADMIN_PASSWORD`) é criado automaticamente na primeira inicialização. Troque
a senha com `python scripts/criar_admin.py <email> <senha-nova>` — detalhes
em [`documentacao/DEPLOY_DOCKER.md`](documentacao/DEPLOY_DOCKER.md#usuário-administrador-padrão).

## Documentação

Ver a pasta [`documentacao/`](documentacao/README.md) para guias detalhados
(protocolo de tempo real, deploy, impressão térmica, notificações, etc.).
