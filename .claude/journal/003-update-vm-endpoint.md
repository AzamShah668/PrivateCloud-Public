---
date: 2026-04-03
title: Update VM Endpoint (Start/Stop/Restart/Resize)
task: "#14 — Update VM"
sprint: 2
---

### 2026-04-03 — Update VM Endpoint (Start/Stop/Restart/Resize)

**Task:** GitHub Issue #14 — Update VM

**What was done:**
I added a `PATCH /vms/{job_id}` endpoint that lets users control their VMs after creation. It supports four actions: start (boot a stopped VM), stop (hard-stop a running VM), restart (reboot), and resize (change CPU cores and/or RAM). The endpoint follows the same ownership check and audit logging pattern as the existing create and delete endpoints.

I also added three new methods to the ProxmoxClient: `restart_vm()` for rebooting, `get_vm_config()` for reading current config, and `update_vm_config()` for changing CPU/RAM. Plus a `_put()` HTTP helper for future PUT operations.

**Files changed:**
- `backend/app/models/vm.py` — Added `VMAction` enum (start/stop/restart/resize) and `VMUpdateRequest` Pydantic model with validation: cpu_cores and ram_mb are optional but at least one is required when action is "resize"
- `backend/app/proxmox_client.py` — Added `restart_vm()` (POST to /status/reboot), `get_vm_config()` (GET /config), `update_vm_config()` (POST /config with **kwargs), and `_put()` HTTP helper
- `backend/app/routes/vm_routes.py` — Added `PATCH /{job_id}` route with ownership check, state guard (only 'done' VMs can be updated), Proxmox action dispatch, error handling, and audit logging

**Problems encountered:**
1. **Which HTTP method for the update endpoint**: Had to decide between PUT and PATCH.
   - *Decision*: Went with PATCH because we're not replacing the entire resource — we're performing a partial action (start/stop/resize). PATCH better represents "modify this VM" semantics.

2. **Resize requires VM to be stopped**: Proxmox can hot-plug CPU/RAM in some configs, but it's unreliable. For safety, the endpoint doesn't enforce this at our level — Proxmox will reject the config change if the VM is running and hot-plug isn't supported, and we return the error via 502.

3. **How to handle failed actions**: Unlike create/delete where we change the job status to 'failed', for update actions (start/stop/resize) I decided NOT to change the job status. Why — the VM still exists and is still 'done'. A failed stop doesn't mean the VM is broken. So we return 502 with the error in the audit log, but the job stays 'done'.

**Key decisions:**
- **Single endpoint for all actions**: Instead of separate endpoints like `/vms/{id}/start` and `/vms/{id}/stop`, I used one PATCH endpoint with an `action` field. This is cleaner — one route, one model, one set of auth/ownership checks. The frontend just sends `{"action": "stop"}`.
- **model_post_init for resize validation**: Used Pydantic's `model_post_init` to enforce that resize requires at least one of cpu_cores or ram_mb. This is cross-field validation — can't do it with a single field_validator.
- **Don't change job status on action failure**: A failed start/stop doesn't corrupt the VM. The job status stays 'done'. This avoids a situation where a network blip during "stop" marks the job as "failed" even though the VM is fine.

**What I learned:**
- Proxmox uses POST (not PUT) to update VM config at `/nodes/{node}/qemu/{vmid}/config`. Unusual REST design — most APIs use PUT or PATCH for updates. But Proxmox treats config changes as "apply these settings" operations.
- Cross-field validation in Pydantic v2 uses `model_post_init` instead of `@root_validator` from v1.

**If asked "How did you do this?":**
> I added a PATCH endpoint that takes an action (start/stop/restart/resize) and dispatches to the right Proxmox API call. For resize, it sends the new CPU/RAM values to Proxmox's config endpoint. Everything goes through the same ownership check and audit logging as create and delete.

**If asked "Where did you get stuck?":**
> The main design decision was whether to change the job status when an action fails. I decided not to — if you try to stop a VM and it fails due to a network error, the VM is still running and still 'done'. Changing status to 'failed' would be misleading.
