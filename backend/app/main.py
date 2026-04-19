# =============================================================================
# main.py
# =============================================================================
# The FastAPI application entry point.
#
# This file does three things:
#   1. Creates the FastAPI app instance with metadata (title, docs URL, etc.)
#   2. Registers the lifespan handler — code that runs ONCE on startup
#      (initialise the DB pool) and ONCE on shutdown (close it cleanly)
#   3. Mounts the routers — tells FastAPI which URL prefixes go to
#      which route files
#
# Starting the server (run from the /backend directory):
#   uvicorn app.main:app --reload --port 8000
#
# Auto-generated docs are available at:
#   http://localhost:8000/docs       ← Swagger UI (interactive)
#   http://localhost:8000/redoc      ← ReDoc (read-only, prettier)
# =============================================================================

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import database
from app.routes.auth_routes import router as auth_router
from app.routes.vm_routes import router as vm_router
from app.routes.admin_routes import router as admin_router

# ---------------------------------------------------------------------------
# Logging configuration
# basicConfig sets the format for ALL loggers in the process.
# In production you'd ship logs to a centralised service (Loki, CloudWatch…)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan: startup + shutdown logic
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Everything BEFORE `yield` runs at startup (once).
    Everything AFTER `yield` runs at shutdown (once).

    We initialise the database connection pool here so it's ready before
    the first request arrives. If the DB is unreachable at startup the
    app will crash with a clear error rather than failing silently on
    the first request.
    """
    # ── Startup ───────────────────────────────────────────────────────────
    logger.info("Starting Proxmox Cloud VM API…")
    database.init_db()          # creates connection pool + applies schema
    logger.info("Database ready. API is accepting requests.")

    yield  # ← the application runs here, handling requests

    # ── Shutdown ──────────────────────────────────────────────────────────
    logger.info("Shutting down. Closing database connection pool…")
    if database._pool:
        database._pool.closeall()
    logger.info("Goodbye.")


# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Proxmox Cloud VM API",
    description=(
        "Private cloud management API built on top of Proxmox VE. "
        "Allows authenticated users to provision and monitor Virtual Machines."
    ),
    version="0.1.0",          # Sprint 1
    docs_url="/docs",         # Swagger UI
    redoc_url="/redoc",       # ReDoc
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS — allow the frontend dev server and production origin to call the API
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Vite dev server
        "http://localhost:3000",    # Docker frontend (nginx)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Mount routers
# ---------------------------------------------------------------------------

# Auth routes:  /auth/register,  /auth/login,  /auth/me
app.include_router(auth_router)

# VM routes:    /vms/,  /vms/{job_id}
app.include_router(vm_router)

# Admin routes:  /admin/stats,  /admin/users,  /admin/vms,  /admin/audit-logs
app.include_router(admin_router)


# ---------------------------------------------------------------------------
# Root health-check endpoint
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"], summary="Health check")
def root():
    """
    Simple endpoint to confirm the API is running.
    Useful for Docker health checks and load balancer probes.
    """
    return {"status": "ok", "message": "Proxmox Cloud VM API is running."}
