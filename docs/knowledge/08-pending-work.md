# Pending Work

## Iteration 6 Phase 1: DB↔Proxmox reconciliation — DONE (2026-06-04)
- **Status**: Implemented on `azams-branch`. Existence reconciliation with write-back
  is live in `reconcile_vm_existence` + `mark_vm_job_deleted`, wired into the user
  and admin VM lists. See [[12-state-reconciliation]] and [[07-debugging-journal]] Issue 16.
- **Not yet verified end-to-end** (user deferred live verification to save tokens):
  delete a VM in the Proxmox UI → refresh dashboard → row should soft-delete; kill
  Proxmox → refresh → existing VMs must still list (G1). Verify before the viva.

## Iteration 6 Phase 2: `.env` → UI setup wizard — PLANNED (next)
- **Goal**: Move operational config out of the committed `.env` into the DB-backed
  `system_settings` store, configured via a first-run admin setup wizard (Kanban
  #53–#57). Matches the existing `AdminSettingsPage` + `/admin/settings` infra.
- **Stays in docker-compose (bootstrap, can't move):** `DB_*`, `CELERY_BROKER_URL`,
  `JWT_SECRET_KEY`, new `SETTINGS_ENCRYPTION_KEY` (Fernet). (Kanban #56.)
- **Moves to DB/wizard (Fernet-encrypted where secret):** `PROXMOX_*`,
  `GOLDEN_IMAGE_VMID`, `WINDOWS_TEMPLATE_VMID`, `VM_DEFAULT_*`, `VM_WINDOWS_*`,
  `OPENAI_API_KEY/BASE_URL/MODEL`, `GUACAMOLE_*`, `CLONE_LEASE_HOURS`.
- **Next steps**: (1) `secret_crypto.py` (Fernet) + add `secret` to the
  `system_settings` value_type CHECK; (2) `config.py` `get_config(key)` resolver
  (DB-first, env fallback, cached) and refactor the ~10 `os.getenv` call sites
  (`proxmox_client`, `llm_agent`, `guacamole_client`, `models/vm`, `template_routes`)
  onto it; (3) mask secrets in `list_settings`/`SettingResponse`; (4) seed new keys
  in `init_db()`; (5) `GET /setup/status` + `POST /setup`; (6) frontend onboarding
  wizard; (7) shrink `.env`, update `docker-compose.yml` + `.env.example`.
- **SECURITY note**: `.env` is gitignored and NOT tracked in git (verified), so
  the real secrets were never committed. Once the wizard is run they also live
  encrypted (Fernet) in `system_settings`. `SETTINGS_ENCRYPTION_KEY` is the only
  new bootstrap secret — keep it stable or saved secrets become undecryptable.
- Plan file: `~/.claude/plans/tender-noodling-rose.md`.

## Iteration 6 Phase 2: `.env` → UI setup wizard — IMPLEMENTED (2026-06-04)
- **Status**: Built on `azams-branch` (not yet live-verified — user deferred to save tokens).
  See [[13-config-and-setup-wizard]]. Backend config now resolves DB-first with env
  fallback; first-run wizard at `/setup`; secrets Fernet-encrypted + masked.
- **Verify before viva**: fresh DB → register first user (auto-admin) → wizard appears →
  enter Proxmox + LLM → "Test connection & finish" → VM create + AI chat work from DB
  config → `SELECT value FROM system_settings WHERE key='proxmox.password'` is ciphertext
  (`enc::…`) and `GET /admin/settings` masks it.

## CRITICAL: Guacamole URL Rewrite - Docker Rebuild Needed
- **Status**: Code patched, NOT deployed
- **What was done**: Added rewriteGuacUrl() to GuacamoleModal.tsx, typed the parameter
- **What remains**: Run `docker compose up --build -d frontend` and verify build passes
- **Risk**: The fix_guac.js script may have introduced untyped JS (function instead of TS function)
- **Verify**: Check that rewriteGuacUrl has `(raw: string): string` signature, not just `(raw)`

## Guacamole SSH Refactor (Partially Started)
- **Context**: guacamole_client.py's create_desktop_session() accepts protocol param (rdp/ssh)
- **Status**: Backend supports it but no frontend path to trigger SSH mode
- **If needed for viva**: Would need a new button or auto-detect based on OS

## LLM Agent System Instructions
- **File**: backend/app/services/llm_agent.py (lines 187-194)
- **What was done**: Updated system prompt with OS-specific defaults
- **Status**: Deployed (backend hot-reloads)

## Sprint 5: Clone-from-Template — DEPLOYED & LIVE-VERIFIED (2026-06-03)
- **Status**: Live in Docker, verified end-to-end against real Proxmox. 9 successful clones across the test pass (full + linked, single-source + cross-source). See [[11-clone-templates]] and `docs/recent-work/09-sprint5-end-to-end-test.md`.
- **Fixes applied during E2E** (see [[07-debugging-journal]] Issues 10 & 11):
  - Per-source Redis lock around `clone_vm + wait_for_task` so concurrent clones of the same source serialise (Proxmox flocks the source config during a clone)
  - `pg_advisory_xact_lock(7501231)` at the start of `init_db()`'s schema-setup transaction so concurrent Celery worker startups don't deadlock on the audit-constraint `ALTER TABLE`
- **Verified guards**: duplicate-distribution (409), linked-mode mismatch (400), source-must-be-done (400), admin-cannot-be-enrolled-as-student (400)
- **Verified speeds**: linked clones ~30-60 s per VM, full clones ~2-4 min per VM; cross-template distributions run in parallel (only same-source serialises)
- **Remaining (optional) next steps**:
  - "Retry only the failed students in a batch" endpoint (today the workaround is to re-distribute; new clones come for everyone)
  - Per-batch lease override UI (today distributed clones have `expires_at = NULL` by default; configurable via `CLONE_LEASE_HOURS` env)
  - Multi-node Proxmox cluster support in `get_free_vmids` (today scans a single node — fine for the single-node deployment)
  - Optional: bump `worker_concurrency` above 2 if the Proxmox host has IO headroom (different-source clones would gain throughput)

## RAG Knowledge Base — DEPLOYED & WORKING (2026-05-26)
- **Status**: Live in Docker. Vector store reports `available: True`, embedding
  model downloaded + cached, login healthy. Image fully baked (no hot-patches).
- **Fixes applied during deploy** (see [[07-debugging-journal]] Issues 7 & 8):
  - `bcrypt==4.0.1` pinned (passlib 1.7.4 vs chromadb conflict)
  - CPU-only torch (`torch==2.5.1+cpu`) in its own cached Docker layer
  - Dockerfile pre-creates + chowns `data/chroma` and `.cache/huggingface` for
    the non-root appuser
- **Remaining (optional) next steps**:
  - Upload real source PDFs via Admin → Knowledge Base (currently 0 docs indexed)
  - Consider the parent-child retrieval upgrade for answer quality (documented in
    the vault; not yet implemented)
- **Full design**: see [[10-rag-knowledge-base]]

## Dedicated Proxmox templates (rework) — follow-ups
- **No "retry failed build" endpoint yet.** If `clone.build_template` fails the
  row sits at `status=failed`; the admin must re-publish (archive the failed one).
  A `POST /templates/{id}/rebuild` would re-dispatch the build task.
- **Building from a running source** relies on Proxmox allowing a full clone of a
  running VM. If a given storage/config rejects it, the build fails — a future
  improvement could stop the source (or snapshot it) before cloning, then restart.
- **Orphaned template VMID on failure**: a failed build may leave a half-created
  VM at `template_vmid` on Proxmox; it stays reserved (status≠archived) but isn't
  auto-deleted. Archiving the template doesn't delete the Proxmox template either.
- See [[11-clone-templates]] (Rework section) and [[07-debugging-journal]] Issue 12.

## Knowledge Base Maintenance
- After any code changes, update Graphify: `py -3 -m graphify . --update`
- After any session, add relevant notes to docs/knowledge/
