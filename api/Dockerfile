# Imagem da API Flask + Socket.IO ("CompuFlow").
#
# Contexto de build: pasta `api/` (ver docker-compose.yml).
# Gunicorn + worker eventlet (1 worker — estado de rooms Socket.IO não
# sobrevive entre workers sem Redis). Banco via DATABASE_URL (Postgres).
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

# Dependências de sistema:
# - build-essential/libjpeg62-turbo-dev/zlib1g-dev/libpq-dev: compilar
#   pacotes sem wheel (cryptography, Pillow, psycopg2 em alguns ambientes).
# - fonts-dejavu-core: imagem slim sem fontes TrueType; sem isso a impressão
#   da senha cai em load_default() minúsculo.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        libpq-dev \
        fonts-dejavu-core \
        tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

RUN mkdir -p static/uploads

EXPOSE 5000

CMD ["gunicorn", "--worker-class", "eventlet", "--workers", "1", "--bind", "0.0.0.0:5000", "--timeout", "120", "app:app"]
