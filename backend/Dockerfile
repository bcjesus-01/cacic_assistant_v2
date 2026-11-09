# Estágio 1: builder (instala as dependências com uv, nas versões travadas no uv.lock)
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Usa o Python 3.12 da própria imagem; o uv não baixa outra versão
ENV UV_PYTHON_DOWNLOADS=never
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

# Camada de dependências (fica em cache enquanto pyproject.toml e uv.lock não mudam)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . /app
RUN uv sync --frozen --no-dev

# Estágio 2: runner
FROM python:3.12-slim-bookworm
WORKDIR /app

# libpq: biblioteca C do PostgreSQL exigida pelo psycopg
RUN apt-get update && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY . /app
ENV PATH="/app/.venv/bin:$PATH"

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
