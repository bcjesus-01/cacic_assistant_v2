# Estágio 1: Builder
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# ---> A SOLUÇÃO: Proibir download do Python 3.15 e forçar o uso do 3.11 do sistema <---
ENV UV_PYTHON_DOWNLOADS=never
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential

COPY pyproject.toml uv.lock ./
# (O resto do arquivo continua exatamente igual...)
RUN uv sync --frozen --no-install-project --no-dev

COPY . /app
RUN uv sync --frozen --no-dev

# Estágio 2: Runner
FROM python:3.12-slim-bookworm
WORKDIR /app

# ---> A SOLUÇÃO: Instala a biblioteca C do Postgres e limpa o cache <---
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY . /app
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
