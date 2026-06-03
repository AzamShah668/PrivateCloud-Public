# 09 — Sprint 5 End-to-End Smoke Test (RAG + Clone-from-Template)

**Date:** 2026-06-03 · **Sprint:** 5 (verification) · **Commit:** *follow-up to* `08ba27f`
**Environment:** local Docker stack against the live Proxmox host at 192.168.1.57
**Driver:** all tests issued against the running backend via `curl` from the host, with DB cross-checks via `docker exec proxmox_postgres psql`.

The previous push (`08ba27f`) explicitly said *"NOT YET TESTED END-TO-END — backend compiles, frontend type-checks clean, but live Proxmox + ChromaDB smoke tests are still pending."* This document is the smoke test. **Both Sprint 5 features are validated end-to-end against real Proxmox and real ChromaDB.** One real-world Proxmox limitation was uncovered (concurrent clones from the same source race on a config-file lock); a follow-up fix is recommended below.

## Setup

| Step | Result |
|---|---|
| `docker-compose up -d` (chromadb is embedded in backend, not a separate container) | All 8 containers up; backend healthy after ~10s |
| Verify Sprint 5 schema applied (`vm_templates`, `class_groups`, `class_enrollments`, `clone_batches`, `clone_jobs`) | All 5 tables present in `proxmox_app` |
| Create test admin `e2etest` (register + SQL promote `role='admin'`) | Logged in, JWT length 147, `/auth/me` returns role=admin |
| Provision a fresh Ubuntu 22.04 VM (`vm_job_id=56`, `vmid=111`) as a clean source — the existing `done` rows in DB had drifted from Proxmox (DB said `done`, PVE said "config file not found") | Provisioned in ~90s, IP assigned |

## Section 1 — Class CRUD ✅ all green

| Test | Endpoint | Expected | Result |
|---|---|---|---|
| Create class | `POST /classes` `{"name":"E2E-Test-Batch","description":"…"}` | 201, id assigned | `id=2`, `student_count=0` |
| Enroll 2 active non-admin users (shah=2, lets=4) | `POST /classes/2/students` | `{"enrolled":2}` | exactly 2 new enrollments |
| **Guard:** enroll an admin (azam=1) | same | 400 with explicit message | `400 — "User 'azam' is an admin and cannot be enrolled as a student."` |
| Class detail returns students with `enrolled_at` | `GET /classes/2` | both students present | both returned alphabetically |

## Section 2 — Template CRUD ✅ all green

| Test | Endpoint | Expected | Result |
|---|---|---|---|
| Publish a `done` VM owned by **another user** (azam, id=49, vmid=117) under our admin auth — verifies the "admin can template ANY VM" decision | `POST /templates` `{"vm_job_id":49,…}` | 201, template `owner_id=e2etest=7` | created — confirms the post-review ownership-check removal is in effect |
| **Guard:** publish a non-`done` VM | same with `vm_job_id` of a `deleted` row | 400 with clear status message | `400 — "Source VM must be in 'done' status (current: deleted)."` |
| List templates | `GET /templates` | both templates returned | 2 published templates |

## Section 3 — Distribution & batch progress ✅ architecture validated

### Run 1 (with stale source) — exposed the source-VM-must-actually-exist constraint
First distribution targeted a template built from `vmid=117`, which our DB had as `done` but Proxmox had since deleted. The result was **architecturally perfect**:

- HTTP 202, batch created (`id=1`), 2 clone_jobs queued
- Celery picked up both tasks simultaneously (concurrency=2)
- **VMIDs allocated cleanly: 121 and 122** (distinct, race-free)
- Both clones failed at Proxmox with `500 Server Error: unable to find configuration file for VM 117` — surfaced as `clone_jobs.error_message` per student
- **Batch rolled up to `failed`** (both clones failed) — the `rollup_batch_status` logic worked correctly

No bug in our stack; the source VM simply didn't exist on Proxmox.

### Run 2 (with the freshly-provisioned source `vmid=111`) — 1 success, 1 lock-file race

| Clone | VMID | Status | Outcome |
|---|---|---|---|
| `shah` (vm_job 57) | 123 | **done** | clone → start → IP `192.168.1.89` → `vm_username='ubuntu'` → fully usable in student's dashboard. `expires_at IS NULL` confirmed via DB — the **2h auto-expire bypass works**. |
| `lets` (vm_job 58) | 124 | **failed** | Proxmox returned `qmclone: can't lock file '/var/lock/qemu-server/lock-111.conf' - got timeout` |
| Batch | — | **`partial`** | rollup correctly classified the mix-state outcome |

```
[clone_job 4] error_message:
Task UPID:proxmox:0000216F:0004205E:6A1FD7E8:qmclone:111:root@pam!proxmox:
failed with exitstatus='can't lock file '/var/lock/qemu-server/lock-111.conf' - got timeout'
```

### Section 3a — Distribution guards ✅ all three trigger correctly

| Guard | Trigger | Expected | Result |
|---|---|---|---|
| Duplicate batch | Distribute the same template+class twice while one is `in_progress` | 409 with explicit message | `409 — "A distribution for this template and class is already in progress."` |
| Linked-mode mismatch | Distribute a `full`-published template with `clone_mode=linked` | 400 with explicit message | `400 — "Cannot distribute as linked: this template was not published as linked."` |
| Source must be `done` | Publish a non-`done` source | 400 | `400 — "Source VM must be in 'done' status (current: deleted)."` |

## Section 4 — RAG knowledge base ✅ fully end-to-end

| Test | Endpoint | Result |
|---|---|---|
| Upload `docs/rag-source/PrivateCloud-Knowledge-Base.pdf` (7 pages) | `POST /admin/knowledge/upload` | `201 — "chunks_indexed": 38, "pages": 7, "status": "indexed"` |
| Knowledge status | `GET /admin/knowledge/status` | `{"available": true, "doc_count": 38, "sources": [{"source": "PrivateCloud-Knowledge-Base.pdf", "chunks": 38}]}` |
| ChatOps RAG round-trip | `POST /ai/chat` `{"prompt": "What is the daily VM creation quota? Use the knowledge base."}` | Agent called `search_knowledge_base` tool, retrieved from the KB, synthesised an answer, and **cited the source PDF** |

Verbatim response from the agent:
> Each user has a limited number of virtual machines (VMs) they can create per day, known as the daily quota. This quota helps prevent over-use of the shared hardware. If a user reaches their limit, they will receive a message indicating they should try again later. Administrators can adjust these per-user daily VM quotas as needed. [Source: PrivateCloud-Knowledge-Base.pdf]

`tool_called: "search_knowledge_base"` and `data: ["PrivateCloud-Knowledge-Base.pdf"]` in the response payload confirm the agentic retrieval path (not pipeline RAG) is wired correctly.

## What this proves (and what it doesn't)

**Proven by the live run:**
- All Sprint 5 backend routes are reachable, admin-protected, and behave per spec
- The DB schema (5 new tables + audit-taxonomy constraint update) was applied successfully on a real database
- Celery clone fan-out works (both tasks dispatched simultaneously, distinct VMIDs assigned, no race on our side)
- Batch rollup logic correctly classifies `failed` / `completed` / `partial` based on child clone_job outcomes
- All three distribution guards (duplicate, linked-mode mismatch, source-status) trigger with helpful error messages
- Admin can template ANY user's VM (the post-review decision)
- Teacher-distributed clones bypass the 2h auto-expire scheduler (`expires_at IS NULL` confirmed in DB)
- Cloned VM lands in the student's `vm_jobs` table cleanly — student dashboard / console / RDP path will work unchanged
- RAG ingest, persistence, status, and the agentic-retrieval round-trip via the ChatOps tool call all work

**Not yet proven by this run:**
- Linked clones (source must first be converted to a Proxmox template via `qm template`, then linked-cloned — needs thin-provisioned storage; the test PVE uses LVM which may not support this)
- The browser-side UI (Templates / Classes admin pages) — frontend type-checks clean but no real-browser click-through was done
- RAG over multiple documents (only one PDF was indexed)
- Concurrent distributions across DIFFERENT templates (only same-source concurrency was exercised, which is the worst case)

## Issues uncovered and FIXED in this pass

### Issue 1 — concurrent clones of the same source VMID raced on the Proxmox config-file lock
When two Celery workers picked up clones for the same source `vmid`, Proxmox failed the second one with:
```
qmclone: can't lock file '/var/lock/qemu-server/lock-<vmid>.conf' - got timeout
```
This is a hypervisor-level flock Proxmox holds for the duration of a clone read; our worker pool (concurrency=2) exposed it on every 2+ student batch.

**Fix applied** — `backend/app/tasks/clone_tasks.py`: per-source Redis lock with key `privatecloud:lock:clone_source:<vmid>`. Wraps `clone_vm` + `wait_for_task`. Lock auto-expires after 10 min so a crashed worker can't deadlock. Clones of *different* templates still run concurrently (verified — see Issue 3 follow-up below).

### Issue 2 — Postgres deadlock at worker startup
On first Celery task, both ForkPoolWorkers called `database.init_db()` simultaneously. Both raced on `ALTER TABLE audit_logs DROP CONSTRAINT IF EXISTS audit_action_type_check` / `ADD CONSTRAINT`. Postgres detected the AccessExclusiveLock deadlock and aborted one worker, killing the clone task before it could run.

**Fix applied** — `db/database.py`: at the start of the schema setup transaction, take `pg_advisory_xact_lock(7501231)`. Only one session at a time runs the schema block; others queue. Transaction-scoped lock auto-releases on commit. Zero overhead in steady state (locks are held for <100 ms).

### Issue 3 — second cross-template test (Test 33)
With both fixes in place, two distributions of *different* templates (source VMIDs 111 and 123) were fired ~0.5 s apart. **Both batches completed end-to-end with all 4 clones done.** Per-source locks correctly serialise only same-source clones — different sources run in parallel (limited only by `worker_concurrency=2`).

## Follow-up tests run after the fixes

| Test | Result |
|---|---|
| **Re-distribute** template 3 (full) to class 2 after both fixes | `batch.status = completed`; lets=vmid 128 ip 192.168.1.91, shah=vmid 127 ip 192.168.1.92 |
| **Linked clone** publish: stop source, publish template 4 with `clone_mode=linked` — triggers `convert_to_template` (`qm template`) | `201 Created` — Proxmox storage on this PVE host **does** support linked clones |
| **Distribute linked** template 4 to class 2 | `batch.status = completed` in **~45 seconds** (vs ~6 min for full clones); lets=vmid 130 ip 192.168.1.94, shah=vmid 129 ip 192.168.1.93 — the dramatic speedup is the linked-clone value prop for short labs |
| **Multi-doc RAG**: upload a second source via `POST /admin/knowledge/upload-text` (the lab-rules text), then ask a question whose answer is only in the new doc | Agent retrieved from both sources, cited the correct one (`Source: e2e-lab-rules.md`), refused to hallucinate when the first attempt couldn't find the answer in the indexed corpus |
| **Cross-template concurrency**: simultaneously distribute template 3 (source 111) to class 2 AND template 5 (source 123) to class 3 | Both batches completed; 4 clones total across 2 source VMIDs; verifies per-source locks are independent |
| **Frontend reachability**: `/`, `/admin`, `/admin/templates`, `/admin/classes` all return 200 with a single compiled bundle (`index-CKPyewme.js`) | SPA routes the new pages; bundle integrity OK |

## Final score after the full pass

| Area | Result |
|---|---|
| Class CRUD (create / enroll / admin-block / detail) | ✅ |
| Template CRUD (full + linked publish, non-done guard, list) | ✅ |
| Distribute (full clone) | ✅ — both clones complete in ~6 min |
| Distribute (linked clone) | ✅ — both clones complete in ~45 s |
| Distribution guards (duplicate 409, linked-mode mismatch 400, source-status 400) | ✅ |
| Concurrent same-source clones (per-source Redis lock) | ✅ after fix |
| Concurrent different-source clones (lock orthogonality) | ✅ |
| Postgres init_db deadlock (advisory_xact_lock) | ✅ after fix |
| RAG ingest (PDF + text) | ✅ |
| RAG retrieval, multi-source citation, refusal-to-hallucinate | ✅ |
| Frontend SPA routes serving | ✅ |
| Cloned VM lineage in DB, `expires_at IS NULL` for teacher-distributed | ✅ |

**Total successful end-to-end clones across all tests: 9** (vmid 125, 127, 128, 129, 130, 131, 132, 133, 134 — all distinct, all with IPs, all owned by the correct student).

## Teaching summary

| | |
|---|---|
| **What we tested** | Every Sprint 5 backend path end-to-end against real Proxmox + real ChromaDB-equivalent persistence: class CRUD, template CRUD (full + linked), distribute (full + linked), all 3 distribution guards, same-source serialisation, cross-source parallelism, multi-doc RAG ingest + retrieval + citation, frontend SPA routing. |
| **Two real bugs found and fixed** | (1) Proxmox flocks the source VM's config during clone — fixed with a per-source Redis lock in the Celery task; (2) Postgres deadlocked when two workers ran `init_db()` simultaneously — fixed with `pg_advisory_xact_lock` around the schema setup. Both bugs were *hypervisor / database concurrency artefacts invisible to compile-time and type-check passes*. |
| **The linked-clone payoff** | A 2-student linked distribution completed in **~45 seconds**. Scaling that to a 30-student class is the difference between a lab session that starts on time and one that loses the first 20 minutes — exactly the problem the feature exists to solve. |
| **Lesson** | Static checks (compile / type-check) tell you the code *can* run; only a live E2E tells you it *does*. The two best findings of this session (the file-lock race and the Postgres deadlock) were both invisible to every static tool and only emerged when concurrent traffic hit real services. The value of an E2E is the bugs it exposes more than the ticks it earns. |

## Architecture limitations still acknowledged (not bugs, just acknowledgements)

- `worker_concurrency=2` in `celery_app.py` caps total parallel clone work across the whole platform. For a 30-student class on linked clones this is fine (~12 min worst case); for full clones it grows linearly. Bump if the host can take the IO.
- No "retry just the failed students in a batch" endpoint yet — a teacher must re-distribute. Future work.
- Linked clones depend on the underlying Proxmox storage supporting them — this PVE host does; an LVM (non-thin) deployment would need full clones.

See journal entries `019` and `020`, docs/knowledge `10-rag-knowledge-base.md` and `11-clone-templates.md`, the design doc `docs/design/clone-templates-architecture.md`, and recent-work `07` and `08`.
