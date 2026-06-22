FROM python:3.12-slim

RUN apt-get update && apt-get install -y git gcc poppler-utils tesseract-ocr tesseract-ocr-spa tesseract-ocr-cat antiword

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# Run via uvicorn --proxy-headers/--forwarded-allow-ips replace Flask's ProxyFix.
# Add `--workers N` here for multi-core in one container.
CMD ["uvicorn", "tipi_backend.wsgi:app", "--host", "0.0.0.0", "--port", "5000", "--proxy-headers", "--forwarded-allow-ips", "*"]
