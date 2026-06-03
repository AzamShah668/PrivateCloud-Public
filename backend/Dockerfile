# =============================================================================
# backend/Dockerfile
# =============================================================================
# Multi-stage build for the FastAPI backend.
#
# Why multi-stage?
#   Stage 1 (builder) — installs dependencies into a virtual environment.
#   Stage 2 (runtime) — copies only the venv and app code, leaving behind
#   all the build tools (gcc, headers, pip cache). Result: a smaller, cleaner
#   production image.
#
# Build:
#   docker build -t proxmox-backend .
#
# Run standalone (needs a running Postgres):
#   docker run --env-file .env -p 8000:8000 proxmox-backend
#
# Preferred: use docker-compose (see ../docker-compose.yml) which starts
# Postgres and this container together.
# =============================================================================

# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

# System libraries required to compile psycopg2's C extension.
# libpq-dev  → PostgreSQL client library headers
# gcc        → C compiler
# We remove the apt cache immediately to keep this layer lean.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install dependencies into an isolated virtual environment.
# Using a venv makes it trivial to copy just the packages to stage 2.
#
# Note: RAG embeddings use ChromaDB's built-in ONNX model (onnxruntime), NOT
# sentence-transformers/torch — so there is no multi-GB ML layer here. Keep it
# that way: do not add torch/sentence-transformers back unless truly required.
COPY backend/requirements.txt .
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.12-slim AS runtime

# Only the PostgreSQL *client* library (libpq.so) is needed at runtime —
# no compiler or headers.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the pre-built virtual environment from stage 1.
COPY --from=builder /opt/venv /opt/venv

# Make the venv's binaries (python, uvicorn, etc.) available on PATH.
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user for security.
# Running as root inside Docker is a bad practice — if the container is
# ever compromised, the attacker gets root-level access to the host too.
RUN useradd --create-home --shell /bin/bash appuser
WORKDIR /home/appuser/app

# Pre-create the RAG data + HuggingFace cache dirs and hand the app dir to
# appuser — done as root, BEFORE the USER switch. When the (initially empty)
# named volumes mount onto these paths, Docker seeds them with appuser
# ownership, so the non-root user can write ChromaDB's SQLite file and the
# downloaded embedding model WITHOUT a runtime chown. Without this, Docker
# creates the volume mountpoints as root and chromadb fails with
# "unable to open database file" (SQLite code 14).
RUN mkdir -p /home/appuser/app/data/chroma /home/appuser/.cache \
    && chown -R appuser:appuser /home/appuser/app /home/appuser/.cache

USER appuser

# Copy the application code.
# Copy the application code and the separate db library.
COPY --chown=appuser:appuser backend/app/ ./app/
COPY --chown=appuser:appuser db/ ./db/

# ---------------------------------------------------------------------------
# Runtime environment variables — defaults only.
# ALWAYS override sensitive values (passwords, secret keys) via:
#   docker run --env-file .env ...   or   docker-compose with an env_file.
# NEVER put real credentials in this Dockerfile.
# ---------------------------------------------------------------------------
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_HOST=postgres \
    DB_PORT=5432 \
    DB_NAME=proxmox_app \
    DB_USER=postgres \
    DB_PASSWORD="" \
    DB_SSLMODE=prefer \
    DB_POOL_MIN=2 \
    DB_POOL_MAX=10 \
    JWT_SECRET_KEY="CHANGE_ME" \
    ACCESS_TOKEN_EXPIRE_MINUTES=60 \
    PROXMOX_HOST="" \
    PROXMOX_USER="root@pam" \
    PROXMOX_PASSWORD="" \
    PROXMOX_NODE="home" \
    PROXMOX_VERIFY_SSL="false"

# The port uvicorn listens on inside the container.
EXPOSE 8000

# ---------------------------------------------------------------------------
# Health check — Docker will mark the container unhealthy if the /
# endpoint stops responding. This also controls the depends_on health
# check in docker-compose.yml so the backend only starts after Postgres
# is confirmed ready.
# ---------------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Start uvicorn.
# --host 0.0.0.0  → listen on all interfaces inside the container
#                   (required so Docker's port mapping works)
# --port 8000     → must match EXPOSE above
# --workers 1     → single worker is fine for Sprint 1; increase for prod
# Remove --reload in production (it's a dev convenience that wastes CPU).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
