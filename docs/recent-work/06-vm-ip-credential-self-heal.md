# 06 — VM IP/Credential Self-Heal After Failed Provisioning

**Commit:** `5dd75e8` · **Date:** 2026-05-25 · **Sprint:** 4
**Files:** `backend/app/routes/vm_routes.py`, `backend/app/routes/desktop_routes.py`, `db/database.py`

This commit bundles three related fixes that all surfaced from one VM (job 53 / VMID 109, "Mobile"): the headline self-heal, a latent rename bug it exposed, and a small listing fix.

## The headline bug — `vm_ip` written in exactly one place

`vm_ip` is set in **one** location in the whole codebase: the Celery provisioning task `backend/app/tasks/vm_tasks.py:136`, which calls `proxmox.get_vm_ip_from_agent(...)`. The flow inside `provision_vm`:

```
1. Clone golden template            ✓
2. Apply CPU/RAM config             ✓
3. proxmox.start_vm(...)            ← VM 109 DIED HERE ("MAX 4 vcpus allowed per VM on this node")
4. Poll guest agent for IP          ← never reached
5. Write vm_ip + credentials to DB  ← never reached
```

When step 3 raised `ProxmoxAPIError`, the task jumped to its `except` block and wrote `status=failed` with `vm_ip=NULL`. The user then fixed the vcpu cap in Proxmox and started the VM via the app's **Start** button — but that endpoint (`vm_routes.py:408`) only called `proxmox.start_vm()` and returned. **It never re-polled for the IP.** So `vm_ip` stayed `NULL` forever, and the frontend banner at `VMDetailPage.tsx:86` (`vm.status === "done" && !vm.vm_ip`) was permanently stuck on *"VM is running, but no IP was reported."* Console and Desktop buttons gate on `vmIP`, so both stayed disabled.

Previous Windows VMs worked only because their initial Celery task succeeded all the way through. VM 109 was the first whose initial provision crashed *before* the IP poll — exposing that there was no recovery path.

## Fix A — PATCH endpoint schedules a background IP re-poll

Imported `BackgroundTasks`, added a helper that polls the guest agent for up to 180s, and wired it into Start/Restart:

```python
# vm_routes.py
async def _refresh_vm_ip_async(job_id: int, vmid: int, node: str):
    """Background: poll the guest agent up to 180s and backfill vm_ip if missing."""
    ip = proxmox.get_vm_ip_from_agent(vmid, node, timeout=180)
    if ip:
        database.update_vm_job(job_id, vm_ip=ip)   # DB uses COALESCE → only fills NULL

async def update_vm(job_id, update, response, background_tasks: BackgroundTasks, current_user=...):
    ...
    # after a successful start/restart:
    if not job.get("vm_ip"):
        background_tasks.add_task(_refresh_vm_ip_async, job_id, vmid, node)
```

### Key trade-off: background task, not inline poll

Polling can take 3 minutes. Holding an HTTP request open that long times out browsers and ties up Uvicorn workers. FastAPI's `BackgroundTasks` returns the action response in <1s and does the poll afterward; the dashboard re-fetches periodically and the IP appears on the next refresh. The DB layer's `COALESCE(%s, vm_ip)` means a re-poll can only *fill* a NULL, never clobber a good value.

## Fix B — GET endpoint self-heals IP (inline) and credentials (env lookup)

Action-triggered recovery requires the user to click something. **Read-triggered recovery just happens** on the next page load. The GET endpoint gained two self-heal blocks:

- **IP:** if `vm_ip` is NULL and the VM is running, do a short (~10s) inline poll and backfill.
- **Credentials:** `vm_username`/`vm_password` are *deterministic env-var lookups* keyed off `os_choice` (`VM_WINDOWS_USERNAME`/`VM_WINDOWS_PASSWORD` for Windows, the Linux equivalents otherwise) — no network needed, essentially free. If they're blank, fill them from env.

This was driven by **bonus bug #1**: even after the IP was patched, Desktop failed with *"VM is missing IP or credentials"* — a `SELECT` showed `vm_username = ''` and `vm_password IS NULL`. Same root cause as the IP: the Celery `except` handler bailed before the credential write at `vm_tasks.py:152-160`.

### Final recovery matrix for `vm_jobs`

| Field | Initial writer | Recovery on PATCH | Recovery on GET |
|---|---|---|---|
| `vm_ip` | Celery `vm_tasks.py:136` | `_refresh_vm_ip_async` 180s background poll | ~10s inline poll if NULL |
| `vm_username` | Celery `vm_tasks.py:152` | — | env-var lookup if blank |
| `vm_password` | Celery `vm_tasks.py:152` | — | env-var lookup if NULL |
| `status` | Celery exception handler | manual via DB | — (intentionally) |

`status` recovery stays manual on purpose: auto-promoting a `failed` job to `done` without re-provisioning would mask real failures.

## Fix C — the latent rename bug this uncovered (bonus bug #2)

Once credentials were healed, Desktop reached a line that had **never executed before** and threw HTTP 500:

```
AttributeError: module 'app.services.guacamole_client' has no attribute
'create_windows_desktop_session'. Did you mean: 'create_desktop_session'?
```

The rename from doc [05](05-cross-device-console-desktop.md) updated the function in `guacamole_client.py` but missed the call site in `desktop_routes.py:83`. One-line fix:

```python
# desktop_routes.py
session = guacamole_client.create_desktop_session(...)   # was create_windows_desktop_session
```

This had been broken in `main` for an unknown time — nobody hit it because every Windows VM died at the missing-IP banner first. **Unblocking the happy path exposed the next latent bug.**

## Fix D — hide deleted VMs from listings

`list_user_vm_jobs` was returning soft-deleted rows. Added a status filter:

```python
# db/database.py
cur.execute(
    "SELECT * FROM vm_jobs WHERE user_id = %s AND status != 'deleted' ORDER BY id DESC LIMIT %s",
    (user_id, limit),
)
```

## The lesson (worth internalising)

1. **A single-writer field with no recovery path is a fragility bug.** Any failure in that one write leaves the field permanently broken for every consumer (Console, Desktop, copyable IP/RDP/SSH).
2. **A broken happy path hides an arbitrary number of downstream bugs.** Each time you unblock a stuck flow, expect the next step to be silently broken too — the credentials bug and the rename bug were both latent for as long as the IP bug.
3. **Read-path recovery > action-path recovery** for surfacing these, because it runs automatically and drags the next hidden bug into the light.

## Teaching summary

| | |
|---|---|
| **Trigger** | VM 109 crashed at `qm start` (vcpu cap) before the IP/credential write. |
| **Fix A** | PATCH start/restart schedules a 180s background IP re-poll. |
| **Fix B** | GET self-heals IP (inline poll) + credentials (env lookup) on read. |
| **Fix C** | Repaired stale `create_windows_desktop_session` call → `create_desktop_session`. |
| **Fix D** | `list_user_vm_jobs` excludes `status = 'deleted'`. |
| **Lesson** | Fortify or build recovery for any single-writer field; unblocking one flow reveals the next. |

See also journal `018-vm-ip-recovery-after-failed-provisioning.md`, `018-vm-start-error-state-fix.md`, [`docs/knowledge/07-debugging-journal.md`](../knowledge/07-debugging-journal.md).
