# Imagem do backend Flask + Socket.IO ("App Senhas").
#
# O container roda com Gunicorn + worker eventlet (mesma abordagem já usada
# em `app.py`/`requirements.txt`), servindo a mesma aplicação Flask-SocketIO
# usada em dev (`python app.py`). O banco de dados é PostgreSQL, configurado
# via a variável de ambiente `DATABASE_URL` (ver `docker-compose.yml` e
# `backend/__init__.py::_resolve_database_config`).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependências de sistema:
# - build-essential/libjpeg62-turbo-dev/zlib1g-dev/libpq-dev: compilar
#   pacotes sem wheel pronta para todas as arquiteturas (cryptography,
#   Pillow, psycopg2-binary em alguns ambientes).
# - fonts-dejavu-core: a imagem "python:3.12-slim" não vem com NENHUMA
#   fonte TrueType instalada. Sem isso, backend/utils.py::gerar_imagem_senha
#   (usada para imprimir o número da senha) cai no fallback
#   ImageFont.load_default(), que gera um bitmap minúsculo (~8px) — o
#   número impresso saía ilegível.
# Removidas do apt cache no mesmo layer para manter a imagem pequena.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libpq-dev \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p static/uploads

EXPOSE 5000

# Um único worker eventlet: o Flask-SocketIO com eventlet não é
# compatível com múltiplos workers do Gunicorn sem um message queue
# externo (Redis) para sincronizar as rooms entre processos — para o
# volume desta aplicação (fila de senhas de um setor), um worker é
# suficiente. Ver documentacao/DEPLOY_DOCKER.md.
CMD ["gunicorn", "--worker-class", "eventlet", "--workers", "1", \
     "--bind", "0.0.0.0:5000", "--timeout", "120", "app:app"]
