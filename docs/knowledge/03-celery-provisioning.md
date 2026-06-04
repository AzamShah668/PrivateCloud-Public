# Celery Async Provisioning

## Architecture
FastAPI receives VM creation requests and immediately returns status=queued.
The actual Proxmox work runs in a Celery worker process.

## Flow
1. User POST /api/vms -> FastAPI creates vm_job row (status=queued) -> returns immediately
2. Celery task picks up the job from Redis queue
3. Task clones golden image, configures VM, starts it, polls for IP
4. Task updates vm_job row with status=running, vm_ip, credentials

## IP & Credential Recovery Paths (added 2026-05-25)
If the initial Celery task fails BEFORE the IP poll (e.g. `qm start` rejects the
config), `vm_ip` / `vm_username` / `vm_password` all stay NULL because they are
all written together in the same final block of `provision_vm` at
`vm_tasks.py:152-160`. Three recovery hooks make this self-healing:

1. **PATCH `/vms/{job_id}` (action-triggered, long poll)** — after a successful
   Start or Restart, if `job.vm_ip` is NULL, schedules `_refresh_vm_ip_async`
   as a FastAPI BackgroundTask. Polls the guest agent for up to 180s (handles
   cold boots).
2. **GET `/vms/{job_id}` IP self-heal** — if the VM is `live_status == "running"`
   but `vm_ip` is NULL, does a single 10s agent poll inline and writes the
   result back. Runs on every page load, so any "agent was asleep during
   Windows Update / startup" case self-corrects on the next refresh without
   requiring a reboot.
3. **GET `/vms/{job_id}` credential self-heal** — if `vm_username` or
   `vm_password` is missing, calls `proxmox.get_post_provision_credentials(os_choice)`
   and writes the result back. Deterministic (just env var lookups, no network
   call), so essentially free. Without this, half-failed Windows jobs can have
   a valid IP but still block the Desktop / RDP buttons forever.

See [[07-debugging-journal]] Issue 6 for full root cause and the related rename
bug in `desktop_routes.py` that the IP+credential self-heal exposed.

## Components
- `backend/app/celery_app.py` - Celery app configuration
- `backend/app/tasks/` - Task definitions
- `backend/app/routes/vm_routes.py` - API endpoints that dispatch tasks
- Redis at redis://redis:6379/0 - Message broker

## Why Celery?
- VM provisioning takes 30-120 seconds (clone + boot + IP assignment)
- Without Celery, FastAPI worker threads block, causing 503s under load
- Celery workers run in a separate container, isolating heavy work

## Golden Images
- Linux: Template VMID configured in env (clone-based provisioning)
- Windows 11: Separate template with RDP pre-configured

## Related
- [[02-docker-infrastructure]] - Worker container config
- [[09-viva-preparation]] - How to explain this architecture
