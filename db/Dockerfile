# =============================================================================
# Dockerfile — Proxmox Cloud VM App
# =============================================================================
#
# Build image:
#   docker build -t proxmox-vm-app .
#
# Run (pass env vars inline or via an .env file):
#   docker run --env-file .env -p 8000:8000 proxmox-vm-app
#
# The app expects a running PostgreSQL instance reachable at DB_HOST.
# Use docker-compose (see docker-compose.yml) for a full local stack that
# starts both the app and a Postgres container together.
# =============================================================================

# --- Stage 1: base Python image -----------------------------------------------
FROM python:3.12-slim AS base

# Install the C libraries that psycopg2 needs to talk to PostgreSQL.
# libpq-dev   → PostgreSQL client headers / libpq.so
# gcc         → needed to compile the psycopg2 C extension
# We clean up the apt cache afterwards to keep the layer small.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Set a sensible working directory inside the container.
WORKDIR /app

# --- Stage 2: install Python dependencies ------------------------------------
# Copy requirements first so Docker can cache this layer; the layer is only
# rebuilt when requirements.txt actually changes, not every time code changes.
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# --- Stage 3: copy application code ------------------------------------------
COPY . .

# ---------------------------------------------------------------------------
# Environment variables — defaults shown here; override at runtime.
# NEVER put real credentials in this file; use docker run --env-file .env
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
    DB_POOL_MAX=10

# Expose the port your web framework listens on (adjust if different).
EXPOSE 8000

# Start the application.
# Replace this command with whatever launches your actual web server, e.g.:
#   uvicorn app.main:app --host 0.0.0.0 --port 8000   (FastAPI)
#   gunicorn app.main:app ...                          (Flask / Django)
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
