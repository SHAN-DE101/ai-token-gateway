# Stage 1: Build stage
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential libpq-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir uv && \
    uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -r pyproject.toml prometheus-client tabulate asyncpg psycopg2-binary

# Stage 2: Minimal Runtime Stage
FROM python:3.11-slim AS runner

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 && rm -rf /var/lib/apt/lists/*

# Non-root security user
RUN groupadd -r gateway && useradd -r -g gateway gateway

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY app/ app/
COPY scripts/ scripts/

USER gateway

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4", "--loop", "uvloop", "--no-access-log"]
