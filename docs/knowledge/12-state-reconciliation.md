# DB ↔ Proxmox State Reconciliation

> How the `vm_jobs` table is kept truthful against the hypervisor.
> Phase 1 of the Iteration-6 "single source of truth" work. See [[07-debugging-journal]] Issue 14.

## The problem (the "hallucinated VM")

`vm_jobs` is a cache of *intent*. Proxmox is the *source of truth* for whether a
VM actually exists. When an admin deletes a VM **directly in the Proxmox UI**
(out-of-band, not through the app), the DB never finds out, so the dashboard
keeps showing a VM that is gone.

An earlier attempt (the `verify_proxmox` flag on `GET /admin/vms`) only
**filtered the response** against live Proxmox — it never wrote anything back,
so the DB stayed permanently stale and every other read path still hallucinated.
Pulling live data straight into the UI also makes the UI depend on Proxmox being
reachable for *correctness*, not just for telemetry.

## The fix: reconcile-on-read, write-back

Proxmox is the source of truth; the DB is **reconciled to match it**, and the UI
reads the reconciled DB.

- **What gets reconciled:** *existence / lifecycle only.* When a VM that should
  be live (`status in {running, done}`) is absent from the live Proxmox VMID set,
  its row is **soft-deleted** (`status='deleted'`). It then drops out of every
  list that already filters `status != 'deleted'` (e.g. `list_user_vm_jobs`,
  `db/database.py`), so the DB self-corrects.
- **What is NOT reconciled:** power state, CPU %, memory, uptime — these are live
  *telemetry*, correctly sourced live as enrichment in the routes. They are
  real-time data, not stale cache, so there is nothing to "fix" by caching them.
  (The DB `vm_jobs.status` column is the **provisioning lifecycle**
  `queued→running→done→failed→deleted`, *not* the power state — don't conflate
  them.)

## Where it lives

| Piece | Location |
|---|---|
| Reconciliation logic | `backend/app/services/reconciliation.py` → `reconcile_vm_existence(jobs, live_vmids)` |
| Soft-delete writer | `db/database.py` → `mark_vm_job_deleted(job_id, reason)` (preserves `proxmox_response`, appends reason to `error_message`) |
| User list wiring | `backend/app/routes/vm_routes.py` → `list_user_vms` (reuses the existing single bulk `list_vms()` call) |
| Admin list wiring | `backend/app/routes/admin_routes.py` → `list_all_vms` (replaced the filter-only `verify_proxmox` with real write-back) |
| Audit trail | `database.add_audit_log(action="vm.reconcile_deleted", ...)`, attributed to the VM's owner |

## Two non-negotiable safety guards

- **G1 — Proxmox-up guard:** only reconcile when the live `list_vms()` call
  *succeeded*. A transient Proxmox outage must never mass-delete the inventory.
  In code this is the `proxmox_reachable` flag (user list) / the `try` that sets
  `live_vmids` (admin list).
- **G2 — pending-state guard:** never touch `queued`/provisioning rows — a fresh
  VM has a reserved VMID (`get_reserved_vmids`) that isn't on Proxmox yet. Only
  `running`/`done` rows are eligible (`_ELIGIBLE_STATUSES` in the service).

## Behavioural notes

- `list_user_vm_jobs` already filters deleted → reconciled VMs vanish from the
  dashboard with **no frontend change**.
- `list_all_vm_jobs` intentionally returns *everything* (incl. deleted) for admin
  history. The admin endpoint still re-reads after reconciling; the legacy
  `verify_proxmox=true` flag now means "also drop non-live VMs from the response"
  (used by the Publish-Template picker).

## Related
- [[07-debugging-journal]] Issue 14 (the read-only filter this supersedes)
- [[08-pending-work]] (Phase 2: `.env` → UI setup wizard)
- [[04-frontend-architecture]] (dashboard VM list consumers)
