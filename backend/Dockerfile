# syntax=docker/dockerfile:1

FROM python:3.13-slim AS base

COPY --from=ghcr.io/astral-sh/uv:0.12.17 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_SYSTEM_CERTS=true \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN --mount=type=secret,id=local_ca \
    --mount=type=cache,target=/root/.cache/uv \
    if [ -f /run/secrets/local_ca ]; then \
        cp /run/secrets/local_ca /usr/local/share/ca-certificates/local-ca.crt; \
        update-ca-certificates; \
    fi \
    && uv sync --locked --no-dev --no-install-project

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

FROM base AS development

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --dev --no-install-project

COPY --chown=app:app app ./app
COPY --chown=app:app tests ./tests
COPY --chown=app:app scripts ./scripts

USER app

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

FROM base AS runtime

COPY --chown=app:app app ./app
COPY --chown=app:app scripts ./scripts

USER app

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
