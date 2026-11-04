FROM python:3.12-slim-trixie

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-dev --no-install-project

COPY src ./src

RUN useradd --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser


CMD ["sh", "-c", "fastapi run src/main.py --host 0.0.0.0 --port ${PORT:-1000}"]