# Stage 1: Build
FROM python:3.11-slim-bookworm AS builder

# Install uv by copying the binary from the official distroless image.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system-level build dependencies.
# gcc, g++, python3-dev, libgdal-dev, libpq-dev are only needed to compile
# Python packages and will NOT be present in the final image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal-dev \
    libgeos-dev \
    libproj-dev \
    libpq-dev \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Tell uv sync to install into /opt/venv instead of the default /.venv
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Silence hardlink warnings when using a cache mount across filesystems.
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# Stage 2: Runtime
FROM python:3.11-slim-bookworm AS runtime

# Only the shared libraries needed at runtime — no compilers, no headers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin \
    libgdal32 \
    libgeos-c1v5 \
    libproj25 \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built venv from the builder stage.
COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Run as an unprivileged user.
RUN useradd --no-create-home --shell /bin/false appuser

WORKDIR /app
COPY . .

# Pre-create writable directories and hand ownership to appuser.
RUN mkdir -p data/Himawari data/VIIRS media && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "3", \
     "--timeout", "120"]
