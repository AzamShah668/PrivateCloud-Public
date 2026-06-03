# 08 — Clone-from-Template: Teacher Templates → Bulk-Clone to a Class

**Commit:** *uncommitted (working tree)* · **Date:** 2026-05-27 · **Sprint:** 5
**Files:**
- Backend: `backend/app/proxmox_client.py`, `backend/app/models/template.py` (new), `backend/app/routes/template_routes.py` (new), `backend/app/routes/class_routes.py` (new), `backend/app/tasks/clone_tasks.py` (new), `backend/app/celery_app.py`, `backend/app/main.py`, `db/database.py`, `db/templates.py` (new)
- Frontend: `frontend/src/api/templates.ts` (new), `frontend/src/hooks/use-templates.ts` (new), `frontend/src/pages/admin/AdminTemplatesPage.tsx` (new), `frontend/src/pages/admin/AdminClassesPage.tsx` (new), `frontend/src/App.tsx`, `frontend/src/components/admin/AdminSidebar.tsx`
- Docs: `docs/design/clone-templates-architecture.md` (new), `docs/knowledge/11-clone-templates.md` (new)

## The problem

In a lab, every student wastes the first 20–30 minutes installing the required
software on their own laptop. It works on some machines, fails on others, the
environment is inconsistent, and the teacher can't start until everyone is
ready. For a university platform handing out GPU-backed VMs, this is the
single biggest source of dead class time.

## The idea

Teacher pre-bakes one VM (installs the app, configures it, verifies it runs),
publishes it as a **template**, then **bulk-clones** that template to every
student in a **class** in one action. Each student gets an identical,
ready-to-run VM accessible instantly via the console or RDP we already built.

## The realisation that shaped the design

I started by querying the codebase and discovered the platform **already
clones on every provision** — `provision_vm` (Celery task) clones a golden
image via `proxmox_client.clone_vm`. So I wasn't inventing cloning; I was
generalising an existing primitive.

**Consequence:** cloned student VMs go into the **existing `vm_jobs` table**,
which means the student dashboard, console (ttyd), RDP (Guacamole), 2-hour
expiry scheduler, and audit logging all keep working **with zero changes**.
The new tables only layer template→class→clone lineage on top.

## Data model — 5 new tables (added via `init_db()` schema-on-startup)

| Table | Role |
|---|---|
| `vm_templates` | A published, frozen golden VM: `source_vmid`, `os_choice`, `clone_mode` (`full`/`linked`), default specs, status (`draft`/`published`/`archived`). |
| `class_groups` | A reusable class (e.g. `ML-Batch-2026`), owned by a teacher. |
| `class_enrollments` | Many-to-many: which students belong to which class. |
| `clone_batches` | One "distribute template X to class Y" action — the parent job. |
| `clone_jobs` | One row per student clone. `vm_job_id` links to the real `vm_jobs` row. Status: `queued`/`cloning`/`done`/`failed`. |

DB helpers live in a separate `db/templates.py` rather than bloating the
1000-line `database.py`.

## Full vs Linked clones — the per-template choice

`clone_vm()` was hardcoded to `"full": 1`. I added a `full: bool` parameter:

```python
# proxmox_client.py
def clone_vm(self, template_vmid: int, new_vmid: int, name: str, *, full: bool = True, ...):
    params = {"newid": new_vmid, "name": name, "full": 1 if full else 0, "target": node}
    if storage and full:        # linked clones cannot target a different storage
        params["storage"] = storage
    upid = self._post(f"nodes/{node}/qemu/{template_vmid}/clone", params)
    return upid
```

- **Full** — independent disk copy. Robust, more storage. Default.
- **Linked** — shares the template's base disk, only deltas stored. Near-instant
  and tiny on disk. **Requires** converting the source to a Proxmox *template*
  (`qm template` via `convert_to_template()`) and storage that supports linked
  clones (LVM-thin, ZFS, qcow2-on-dir).

The teacher picks the mode when publishing. For a 60-minute lab, linked is
basically free; for long-lived work, full is safer.

## The trickiest bit — race-free VMID allocation

`get_next_vmid()` (`cluster/nextid`) returns the **same** id until that id is
actually consumed by a created VM. Calling it N times for a bulk clone returns
the same value N times. Worse, two concurrent distribute requests could both
read the same Proxmox in-use set and hand out overlapping ids.

Three layers fix this:

1. **`get_free_vmids(count, extra_reserved=...)`** seeds from nextid, lists
   in-use VMIDs from Proxmox, **merges in VMIDs reserved in our own `vm_jobs`
   table** (`database.get_reserved_vmids()` — queued clones not yet on Proxmox),
   then walks upward collecting `count` distinct free ids.
2. **A Redis lock** (`privatecloud:lock:vmid_alloc`) wraps the entire allocate
   + row-creation block in the distribute endpoint:
   ```python
   with _vmid_allocation_lock() as locked:
       vmids = proxmox.get_free_vmids(
           count=len(student_ids),
           extra_reserved=database.get_reserved_vmids(),
       )
       batch = tdb.create_batch(...)
       for student_id, new_vmid in zip(student_ids, vmids):
           vm_job_id = database.create_vm_job(..., vmid=new_vmid, expiry_hours=None)
           clone_job_id = tdb.create_clone_job(batch["id"], student_id)
   # Celery tasks fan out AFTER the lock releases and rows commit.
   ```
3. **DB-reserved exclusion is the safety net** — even if Redis is down, the
   second request will see the first request's `vm_jobs` rows and skip those
   VMIDs.

## Quota and expiry — deliberate bypasses

- **Quota:** `check_daily_quota` is intentionally *not* called in the distribute
  endpoint. A teacher distributing to 30 students shouldn't get blocked because
  the teacher's daily VM quota is 5.
- **Expiry:** `create_vm_job` was updated to accept `expiry_hours=None`,
  leaving `expires_at` NULL → the 2-hour auto-stop scheduler skips the row.
  A class session shouldn't have everyone's VM die mid-lab. `CLONE_LEASE_HOURS`
  env var sets a finite lease if you want one.

## Code review fixes (same day)

I ran the `code-reviewer` agent and fixed every CRITICAL/HIGH it found:

| Severity | Issue | Fix |
|---|---|---|
| CRITICAL | VMID race on concurrent distributes | DB-reserved exclusion + Redis lock (above) |
| HIGH | Source VM status not checked before publish | Reject unless `status == "done"` |
| HIGH | Distributing a `full` template as `linked` would fail every clone | 400 with a clear message |
| HIGH | Double-clicking distribute created duplicate clones | `get_active_batch(template_id, class_id)` → 409 |
| HIGH | `update_template` built SQL with f-string column names | Static column→fragment map |
| HIGH | 2-hour expiry killed lab VMs mid-session | `expiry_hours=None` for distributed clones |
| MEDIUM | Admins enrollable as students | Reject in `enroll_students` |
| MEDIUM | N+1 user lookup in distribute loop | Build `username_by_id` map once |
| MEDIUM | Publish/Distribute modals dismissable mid-mutation | `guardedClose` + disable Cancel while pending |

The one item I deliberately **reversed**: the reviewer added a per-VM ownership
check on publish ("admin can only template their own VM"). You asked for any
admin to template any VM (operator-style permission), so I removed it. The
"source must be `done`" check stays as a technical requirement (Proxmox can't
clone a half-built VM).

## Teaching summary

| | |
|---|---|
| **Trigger** | Lab classes burn 20–30 minutes per student installing software. |
| **Pattern** | Bulk-clone a teacher-published template to a class; reuse the existing `vm_jobs` table for the resulting student VMs. |
| **Cloning** | Generalised an existing primitive (Proxmox `clone`) — added `full` param + `convert_to_template` + `get_free_vmids`. |
| **Hard part** | VMID allocation must be race-free across concurrent distributes — fixed with DB-reserved exclusion + Redis lock + fan-out after commit. |
| **Lesson** | When a feature looks new, query the graph first — half the primitives often already exist. |

See journal `020-clone-from-template.md`, `docs/knowledge/11-clone-templates.md`, and `docs/design/clone-templates-architecture.md`.
