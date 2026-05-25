# 01 — Celery Auto-Discovery & Worker Healthcheck Fix

**Commit:** `7027dfd` · **Date:** 2026-05-24 · **Files:** `backend/app/celery_app.py`, `docker-compose.yml`

## The problem in one sentence

Background VM provisioning silently never ran: the Celery worker received the `vm.provision` task, didn't recognise it, threw a `KeyError`, and discarded it — so VMs sat in `queued` forever. On top of that, the worker container always reported `(unhealthy)` even when fine.

## Why it happened

There were two independent root causes that looked like one bug.

### Cause 1 — Auto-discovery relies on a filename convention

Celery's `autodiscover_tasks(["app.tasks"])` looks **specifically for a module named `tasks.py`** inside each listed package. Our task file is named `vm_tasks.py` for clarity. So Celery scanned `app.tasks`, found no `tasks.py`, registered zero tasks, and every incoming `vm.provision` was an "unregistered task."

```
Web (FastAPI)  ──.delay("vm.provision")──►  Redis broker  ──►  Worker
                                                                   │
                                                    "vm.provision"? Not in registry → KeyError → message discarded
```

### Cause 2 — Worker inherited the web server's HTTP healthcheck

The `celery-worker` service is built from the **same Dockerfile** as the backend. That Dockerfile defines a `HEALTHCHECK` that runs `curl http://localhost:8000/`. The web container runs Uvicorn on 8000, so that works. But the worker is a **background process with no HTTP server** — port 8000 is closed — so the curl always failed and the container was marked `(unhealthy)` permanently.

## The fix

### Fix 1 — Explicit imports instead of auto-discovery

In `backend/app/celery_app.py`, the task module is named explicitly so registration no longer depends on the filename:

```python
# Explicitly tell Celery where the @task definitions live.
# autodiscover_tasks() only finds files literally named "tasks.py";
# ours is "vm_tasks.py", so we register it by full module path.
celery_app.conf.imports = ["app.tasks.vm_tasks"]
```

This guarantees the `@celery_app.task(name="vm.provision")` decorator inside `vm_tasks.py` is imported and registered at worker startup, regardless of the file's name.

### Fix 2 — A Celery-native healthcheck override

In `docker-compose.yml`, the `celery-worker` service **overrides** the inherited HTTP healthcheck with Celery's own liveness probe:

```yaml
celery-worker:
  # ...build/command...
  healthcheck:
    test: ["CMD-SHELL", "celery -A app.celery_app:celery_app inspect ping --timeout 5 || exit 1"]
    interval: 30s
    timeout: 10s
    retries: 3
```

`celery ... inspect ping` asks the running worker to respond over the broker. If the worker is alive it replies `pong`; otherwise the command exits non-zero and the container is correctly marked unhealthy. This actually measures the thing we care about (is the worker processing?) instead of an HTTP port the worker never opens.

## Collateral cleanup performed the same day

These were one-off operational steps, not code, but they're part of the same fix:

1. **Corrupted build cache.** A rebuild hit `parent snapshot ... does not exist: not found` (BuildKit layer corruption). Fixed with:
   ```bash
   docker builder prune -a -f
   ```
   then a clean `docker compose build`.

2. **Orphaned DB jobs.** Jobs 47 and 48 had been submitted while the worker was broken; their Redis messages were discarded but the Postgres rows stayed `queued`. We reconciled DB state to reality:
   ```sql
   UPDATE vm_jobs
   SET status = 'failed',
       error_message = 'Discarded: worker could not register task during outage'
   WHERE id IN (47, 48);
   ```

## How it was verified

- `docker compose ps` → all 8 containers `(healthy)`.
- Triggered a fresh provision (Job 49, "dddd") → completed and acquired IP `192.168.1.82`.
- Backend / frontend / worker logs all clean.

## Teaching summary

| | |
|---|---|
| **Symptom** | VMs stuck in `queued`; worker container `(unhealthy)`. |
| **Root cause A** | `autodiscover_tasks` only finds `tasks.py`; our file is `vm_tasks.py`. |
| **Root cause B** | Worker inherited the web Dockerfile's `curl localhost:8000` healthcheck; worker has no HTTP server. |
| **Fix A** | `celery_app.conf.imports = ["app.tasks.vm_tasks"]` (explicit registration). |
| **Fix B** | Override healthcheck with `celery inspect ping` in compose. |
| **Lesson** | Convention-based discovery is invisible when you break the convention. Healthchecks must probe what the process actually does. |

See also: [`docs/knowledge/03-celery-provisioning.md`](../knowledge/03-celery-provisioning.md), journal `016-celery-worker-fix.md`.
