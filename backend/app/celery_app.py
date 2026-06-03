# =============================================================================
# celery_app.py
# =============================================================================
# Central Celery application instance.
#
# Celery is a distributed task queue — it lets us take slow, blocking work
# (like cloning a VM on Proxmox, which can take 1-5 minutes) and run it
# in a completely separate worker process.
#
# This file creates the Celery "app" object that both the FastAPI backend
# and the Celery worker processes import.  The broker (Redis) sits between
# them: FastAPI pushes tasks onto Redis, and the worker pulls them off.
#
#   FastAPI  ──(push task)──►  Redis  ──(pull task)──►  Celery Worker
#
# Configuration is read from environment variables so Docker Compose can
# inject the correct Redis URL without hard-coding anything.
# =============================================================================

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Redis connection URL.  Inside Docker Compose the hostname is the service
# name ("redis"), and the default Redis port is 6379.
# Format: redis://<host>:<port>/<database_number>
REDIS_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")

# Create the Celery application instance.
#   - "privatecloud" is just a namespace label for log messages.
#   - broker: where tasks are queued (Redis).
#   - backend: where task results/status are stored (also Redis).
celery_app = Celery(
    "privatecloud",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

# ── Celery Configuration ─────────────────────────────────────────────────────
celery_app.conf.update(
    # Serialise task arguments as JSON (safe, human-readable, debuggable).
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Use UTC timestamps everywhere — matches our database convention.
    timezone="UTC",
    enable_utc=True,

    # ── Concurrency control (THE key production setting) ─────────────────
    # This limits how many VM provisioning tasks run AT THE SAME TIME.
    # Why 2?  Proxmox is a single physical server — its disk I/O and CPU
    # are the bottleneck, not our code.  Allowing more than 2-3 concurrent
    # full-clones will saturate the storage and slow ALL clones down.
    # Increase this only if you add more Proxmox nodes to the cluster.
    worker_concurrency=2,

    # A full clone of a large Windows disk + boot + guest-agent IP polling can
    # legitimately run 20-40 min, so the hard kill has to sit above that or a
    # slow-but-healthy clone gets killed and marked failed. Clones are rare and
    # Proxmox is the bottleneck, so a generous ceiling is fine.
    task_time_limit=3600,        # hard kill at 60 min

    # Soft limit ~55 min — gives the task a chance to clean up first.
    task_soft_time_limit=3300,

    # Acknowledge tasks only AFTER they complete (not when picked up).
    # This means if a worker crashes mid-task, Redis still has the task
    # and another worker will retry it.
    task_acks_late=True,

    # Each worker fetches only 1 task at a time from Redis.
    # Prevents one worker from hoarding tasks while others sit idle.
    worker_prefetch_multiplier=1,
)

# ── Import tasks ─────────────────────────────────────────────────────────────
# Tell Celery to explicitly import these task modules so it registers the
# @celery_app.task decorated functions.
celery_app.conf.imports = ["app.tasks.vm_tasks", "app.tasks.clone_tasks"]
