ARG TARGETPLATFORM=linux/amd64
ARG PYTHON_BASE_IMAGE=python:3.12-slim
FROM --platform=${TARGETPLATFORM} ${PYTHON_BASE_IMAGE}

ARG DEBIAN_MIRROR=http://deb.debian.org/debian
ARG DEBIAN_SECURITY_MIRROR=http://deb.debian.org/debian-security
ARG PYPI_DEFAULT_INDEX=https://pypi.org/simple

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_DEFAULT_INDEX=${PYPI_DEFAULT_INDEX} \
    PIP_INDEX_URL=${PYPI_DEFAULT_INDEX} \
    PATH="/root/.local/bin:${PATH}"

WORKDIR /app

RUN set -eux; \
  if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
    sed -i "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
    sed -i "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
  fi; \
  if [ -f /etc/apt/sources.list ]; then \
    sed -i "s|http://deb.debian.org/debian|${DEBIAN_MIRROR}|g" /etc/apt/sources.list; \
    sed -i "s|http://deb.debian.org/debian-security|${DEBIAN_SECURITY_MIRROR}|g" /etc/apt/sources.list; \
  fi; \
  apt-get update; \
  apt-get install -y --no-install-recommends ca-certificates gcc g++ libgl1 libglib2.0-0; \
  rm -rf /var/lib/apt/lists/*; \
  pip install --no-cache-dir uv

COPY pyproject.toml README.md ./
RUN uv sync --no-dev --default-index "${UV_DEFAULT_INDEX}"

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY assets ./assets
COPY knowledge_base ./knowledge_base

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/healthz', timeout=3)"

CMD ["sh", "-lc", "uv run alembic -c alembic.ini upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
