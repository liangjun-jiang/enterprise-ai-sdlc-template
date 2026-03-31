FROM ghcr.io/astral-sh/uv:0.5.4 AS uv
FROM python:3.12-slim-bookworm AS builder

COPY --from=uv /uv /uvx /usr/local/bin/
WORKDIR /build
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen --no-cache

FROM python:3.12-slim-bookworm AS runtime

RUN useradd --system --create-home --shell /bin/bash python
WORKDIR /app
COPY --from=builder /build/.venv /app/.venv
COPY app/ ./app/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
USER python
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
