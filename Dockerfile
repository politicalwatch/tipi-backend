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

# Which hops are trusted to set X-Forwarded-For. An ENV rather than a CMD flag on purpose:
# uvicorn falls back to $FORWARDED_ALLOW_IPS when the flag is absent, so a deployment can
# correct this from its env_file and a restart, with no image rebuild.
#
# "*" trusts EVERY caller's header, and uvicorn then reads its leftmost entry — a value the
# caller controls. That makes every per-IP rate limit (the search caps, /alerts, /scanned)
# resettable with one rotating header. It stays the default only because it is what this
# image already did. The right value is the address or network of the proxy that actually
# fronts the deployment: uvicorn then walks the list from the right and takes the first
# UNTRUSTED host, which is the real client nginx appends via $proxy_add_x_forwarded_for.
# Naming a host that does NOT front us is worse than "*" — every client collapses into one
# bucket, i.e. /alerts at 10/hour for the entire audience.
ENV FORWARDED_ALLOW_IPS="*"

# --proxy-headers replaces Flask's ProxyFix; the trusted-hops list is the ENV above.
# Add `--workers N` here for multi-core in one container — but note the slowapi limiter
# keeps its counters in memory, so limits would count per worker instead of per container.
CMD ["uvicorn", "tipi_backend.wsgi:app", "--host", "0.0.0.0", "--port", "5000", "--proxy-headers"]
