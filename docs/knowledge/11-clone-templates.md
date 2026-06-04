# Clone-from-Template (Sprint 5)

> Teacher publishes a pre-configured VM as a template, then bulk-clones it to a
> whole class of students in one action. Solves the "every student wastes 20-30
> min installing lab software" problem. Full design:
> `docs/design/clone-templates-architecture.md`.

## ⚠️ Rework (post-Sprint-5): publish makes a REAL Proxmox template
The original implementation never created a Proxmox *template* — "publish" just
saved a `vm_templates` row pointing at the admin's still-running source VM, and
only the linked path froze the source. The admin (correctly) flagged that the
"templates" appeared as ordinary running VMs in Proxmox, unlike the global
golden images 9000/9001. **Now publishing builds a dedicated, frozen Proxmox
template** (clone source → freeze the copy), so it shows up in Proxmox exactly
like 9000/9001 — but private/scoped instead of global. Two consumers clone from
it: the existing class distribution, and a new **admin-only "Templates" category
in the Deploy page** (single self-serve deploy). See issue in
[[07-debugging-journal]].

### What changed
- `vm_templates` gained **`template_vmid`** = the dedicated frozen Proxmox
  template's VMID (NULL until built). `source_vmid` stays the admin's untouched
  working VM (lineage only — never frozen now).
- New statuses: `building` (clone+freeze in flight) and `failed`. CHECK widened
  to `('draft','building','published','failed','archived')` via idempotent
  DROP/ADD migration; column added with `ADD COLUMN IF NOT EXISTS`.
- Publish is now **async**: `POST /templates` returns 202 with status=building
  and dispatches `clone.build_template`, which full-clones the source → the new
  `template_vmid` then `convert_to_template` (qm template). Source can be running
  (full clone supports it); on failure the row goes `failed`.
- Distribute now clones **`template_vmid`** (the frozen template), not
  `source_vmid`. Requires status=published. The old "published as linked"
  mismatch guard was removed — any built template supports full *and* linked.
- New `POST /templates/{id}/deploy` (admin-only): clones the template into one
  VM in `vm_jobs` (mirrors provision) via `clone.deploy_for_user`. Powers the
  Deploy-page Templates category. Quota not checked; uses `CLONE_LEASE_HOURS`.
- `get_reserved_vmids()` now also reserves non-archived `template_vmid`s so a
  building template's allocated id can't be handed to a concurrent clone/deploy.
- Frontend: `CreateVMForm` shows `TemplateSelector` (admin only, published
  templates) below the OS grid; selecting one switches submit to
  `deployFromTemplate`. AdminTemplatesPage shows building/failed badges and
  disables Distribute until published.

## Why this exists
For the university/GPU hand-off: a professor pre-bakes a VM (installs the app,
configures it, verifies), saves it as a template, and distributes one identical,
ready-to-run clone per student. Students open console/RDP and start instantly.

## Core insight
The platform already clones on every provision (`provision_vm` clones a golden
image). This feature **generalises that primitive** rather than inventing one.
Cloned student VMs land in the **existing `vm_jobs` table**, so the student
dashboard, console (ttyd), RDP (Guacamole), 2h expiry, and audit logging all
work unchanged. The new tables only add template→class→clone lineage.

## Data model (new tables, in `db/database.py init_db()`)
- `vm_templates` — published golden VM: `source_vmid`, `os_choice`,
  `clone_mode` (full|linked), default specs, status (draft|published|archived).
- `class_groups` + `class_enrollments` — reusable class with enrolled students.
- `clone_batches` — one "distribute template X to class Y" action.
- `clone_jobs` — one clone per student; `vm_job_id` links to the real VM in
  `vm_jobs`. Status: queued|cloning|done|failed.

DB helpers live in **`db/templates.py`** (kept separate from the 1000-line
`database.py`). Audit `action_type` CHECK constraint was made re-runnable
(DROP + ADD) so new values (`template.*`, `class.*`, `clone.create`) apply on
existing databases.

## Clone modes (`proxmox_client.clone_vm` gained a `full: bool` param)
- **full** (`full=1`): independent disk copy. Robust, more storage. Default.
- **linked** (`full=0`): shares the template's base disk, only deltas stored.
  Near-instant + tiny. **Requires** the source to be a Proxmox *template*
  (`convert_to_template` → `qm template`) on linked-clone-capable storage
  (LVM-thin/ZFS/qcow2-dir). Storage arg must be omitted for linked clones.

## VMID allocation (race-free)
`get_next_vmid()` (cluster/nextid) returns the *same* id until consumed, so it
can't allocate N ids for a bulk clone. `proxmox_client.get_free_vmids(count,
extra_reserved=...)` seeds from nextid, lists in-use VMIDs, **also excludes
VMIDs reserved in our own `vm_jobs` table** (`database.get_reserved_vmids()` —
queued clones not yet on Proxmox), and walks upward collecting `count` distinct
free ids. The distribute endpoint runs allocation + row creation under a
**Redis lock** (`privatecloud:lock:vmid_alloc`) so two concurrent distributes
can't read the same in-use set. Celery tasks are dispatched only AFTER the rows
are committed and the lock is released. If Redis is down, allocation proceeds
degraded (the DB-reserved exclusion still covers the common case).

## Safety guards (added in code review)
- **No ownership restriction (by design):** an admin is the platform operator
  and may publish ANY user's VM as a template. (A code-review pass added an
  owner-only check; it was later removed per product decision — admins template
  any VM. Caveat: linked publish freezes the source VM irreversibly.)
- **Source status:** source VM must be `done` before publishing.
- **Linked-mode mismatch:** distributing a `full` template as `linked` is rejected
  (the source was never converted to a Proxmox template).
- **Double-distribution:** an in-progress batch for the same (template, class)
  returns 409 (`get_active_batch`), preventing duplicate clones per student.
- **Admin-as-student:** admins cannot be enrolled in a class.

## Flow
1. `POST /templates` — publish from an existing `vm_job_id` (admin). **Now builds
   a dedicated frozen Proxmox template asynchronously** (see Rework section above);
   returns 202/status=building, flips to published/failed when the build task
   finishes.
2. `POST /classes` + `POST /classes/{id}/students` — build a class.
3. `POST /templates/{id}/distribute {class_id, cpu?, ram?}` — allocates VMIDs,
   creates `vm_jobs` + `clone_jobs`, fans out one `clone.template_for_student`
   Celery task per student. **Quota is intentionally NOT checked** —
   teacher-distributed clones bypass the per-student daily limit.
4. `clone_tasks.clone_template_for_student` — clone (mode) → configure CPU/RAM →
   start → poll IP → store creds → update vm_jobs + clone_jobs → roll up batch.
5. `GET /clone-batches/{id}` — live per-student progress (frontend polls every
   4s while `in_progress`).

## Batch status rollup (`db/templates.rollup_batch_status`)
any pending → `in_progress`; all done → `completed`; all failed → `failed`;
mix → `partial`.

## Frontend (admin portal)
- `pages/admin/AdminTemplatesPage.tsx` — list, Publish modal (pick a `done` VM +
  mode + specs), Distribute modal (pick class + specs), live Batch progress modal.
- `pages/admin/AdminClassesPage.tsx` — create class, enroll/unenroll students.
- `api/templates.ts` + `hooks/use-templates.ts` (TanStack Query, mirrors
  `use-admin.ts`). Sidebar gains "Templates" and "Classes" links.

## Files
- Backend: `proxmox_client.py` (clone_vm `full`, `convert_to_template`,
  `get_free_vmids`), `models/template.py`, `db/templates.py`,
  `tasks/clone_tasks.py`, `routes/template_routes.py`, `routes/class_routes.py`,
  `celery_app.py` (imports clone_tasks), `main.py` (routers), `db/database.py`
  (schema + audit taxonomy).
- Frontend: `api/templates.ts`, `hooks/use-templates.ts`,
  `pages/admin/AdminTemplatesPage.tsx`, `pages/admin/AdminClassesPage.tsx`,
  `App.tsx`, `components/admin/AdminSidebar.tsx`.

## Known limitations / pending
- Student clones do **not** auto-expire by default (`expiry_hours=None`);
  set env `CLONE_LEASE_HOURS=N` to give them a finite lease. Teacher manages
  lifecycle. No per-batch override UI yet.
- No "retry failed clones in a batch" endpoint yet (failed `clone_jobs` are
  visible but must be re-distributed).
- Linked-clone storage compatibility isn't pre-checked — if storage is plain
  LVM, the Proxmox clone call fails and the clone_job is marked failed.
- Deleting a template/class doesn't cascade-delete running clones (archive only).
- `get_free_vmids` scans a single node — fine for the single-node deployment;
  a multi-node cluster would need `cluster/resources`.
- Batch can stay `in_progress` if a worker is killed between the clone_job
  commit and the rollup (acks_late retry mitigates; a sweep job would close it).

## Related
- [[03-celery-provisioning]] — the provision_vm task this mirrors
- [[05-console-connectivity]] / [[06-guacamole-integration]] — student access
- [[02-docker-infrastructure]] — celery-worker runs the clone tasks

---

## Rework (v2): Student Self-Serve Template Deploy

### Problem
The original "distribute" model auto-creates VMs for *every* student the
moment the admin clicks "Distribute". This wastes compute (idle VMs students
may never use), locks up Proxmox during large class clones, and removes
student agency.

### New architecture: "Assign" + student-triggered deploy
- **Admin assigns** a template to a class → `POST /templates/{id}/assign`
  creates `template_assignments` rows (one per student). **Zero Proxmox calls,
  instant, no VMs created.**
- **Student sees** assigned templates on their Deploy page via
  `GET /templates/available`. They pick a template, name their VM, optionally
  adjust CPU/RAM, and click Deploy.
- **Deploy** → `POST /templates/{id}/deploy` (now accepts students, not just
  admins). Backend verifies the student has an `available` assignment, allocates
  a VMID, creates a `vm_job`, dispatches `deploy_template_for_user`, and marks
  the assignment `deployed`.
- **Old distribute** remains as a secondary "Auto-Deploy" option for urgent
  scenarios (e.g. exam starts in 5 min).

### New table: `template_assignments`
```
template_assignments (
    id, template_id, student_id, class_id?, assigned_by,
    assigned_at, cpu_cores, ram_mb, clone_mode,
    vm_job_id?, status [available|deployed|revoked]
)
UNIQUE (template_id, student_id)
```
- Upsert on conflict: re-assigning after revoke resets to `available`.
- `vm_job_id` filled once the student deploys.

### New/changed endpoints
| Endpoint | Auth | Purpose |
|---|---|---|
| `POST /templates/{id}/assign` | admin | Grant class access (no VMs) |
| `GET /templates/available` | any user | Student's deployable templates |
| `POST /templates/{id}/deploy` | any user | Deploy VM (admin or student with assignment) |
| `POST /templates/{id}/revoke` | admin | Revoke available assignments |
| `GET /templates/{id}/assignments` | admin | List all assignments for a template |
| `GET /templates/{id}/assignments/count` | admin | Quick counts (available/deployed/revoked) |

### DB layer (`db/templates.py` additions)
- `create_or_update_assignment()` — upsert with ON CONFLICT
- `list_student_assignments(student_id)` — join templates, filter available+published
- `get_assignment(template_id, student_id)` — deploy auth check
- `mark_assignment_deployed(assignment_id, vm_job_id)` — status flip
- `revoke_assignment(assignment_id)` — soft revoke
- `list_template_assignments(template_id)` — admin view
- `count_template_assignments(template_id)` — badge counts

### Frontend changes
- `CreateVMForm.tsx`: students now see assigned templates via `useStudentTemplates`
  hook; template cards appear below OS selection (same TemplateSelector component).
- `api/templates.ts`: new `StudentTemplate` type, `listAvailableTemplates()`,
  `assignTemplate()`, `revokeTemplateAssignments()`.
- `hooks/use-templates.ts`: `useStudentTemplates`, `useAssignTemplate`,
  `useRevokeAssignments`.

### Design decisions
- **Quota bypass**: assigned template deploys bypass the student's daily quota
  (same as teacher-distribute). The admin explicitly granted access.
- **Students can adjust specs**: CPU/RAM from the assignment defaults can be
  overridden by the student at deploy time.
- **One deploy per assignment**: UNIQUE(template_id, student_id) + status check
  prevents double deploys. Admin can re-assign after revoke.

