---

### 2026-04-12 — Fix All 8 Code Review Issues from Golden Image Integration

**Task:** Fix the 1 critical, 2 high, 3 medium, and 2 low issues found during the code review of the golden-image template integration (Sprint 2).

**What was done:**
I went through all 8 issues from the code review and fixed every single one. The biggest fix was replacing the hardcoded cloud-init password (`ChangeMe123!`) with a randomly generated one per VM — this was marked CRITICAL because before, every cloned VM had the exact same SSH login. I also made sure the password gets returned to the user in the API response so they can actually log in, added cleanup logic if provisioning fails halfway, replaced a hardcoded `time.sleep(5)` with proper task polling, removed redundant authentication calls, added a guard against impossible disk-shrink operations, converted all logging to lazy format, and added missing return type annotations.

**Files changed:**
- `backend/app/routes/vm_routes.py` — 7 out of 8 issues were fixed here:
  - Replaced `_DEFAULT_CIPASSWORD = "ChangeMe123!"` with `_generate_ci_password()` using `secrets.token_urlsafe()`
  - Changed `_provision_from_template()` to return a dict with `{vmid, ci_username, ci_password}` instead of just an int
  - Added try/except rollback around post-clone steps — if config/resize/cloudinit fails, the orphaned VM gets deleted
  - Updated the `create_vm()` caller to store the full credential dict in `proxmox_response`
  - Replaced `time.sleep(5)` in the delete endpoint with `_wait_for_task(node, stop_upid, timeout=30)`
  - Removed 5 redundant `proxmox._ensure_authenticated()` calls — the client's internal `_get/_post/_put/_delete` methods already handle this
  - Converted all 19 `logger.X(f"...")` calls to lazy `logger.X("...", arg1, arg2)` format
  - Added return type annotations to all 5 route functions (`-> VMJobResponse`, `-> List[VMEnrichedResponse]`)

- `backend/app/proxmox_client.py` — 2 issues fixed here:
  - Added disk shrink guard in `resize_disk()` — fetches current config, parses the `size=XG` string, raises clear error if new size < current size
  - Converted all 12 `logger.X(f"...")` calls to lazy `%s` format
  - Added `import re` for the disk size parsing

**Problems encountered:**
1. **IDE warnings about unused imports right after adding them**: When I added `import secrets` and `import re`, the IDE flagged them as unused because the functions using them hadn't been edited yet. This resolved itself once the dependent code was modified. No actual problem — just the order of edits.

2. **Finding all f-string logger calls**: The initial grep for `logger\.\w+\(f"` missed some multi-line f-strings where the `f"` was on the next line. I did a broader search for `f"` to catch the remaining 3 instances (lines 385, 614, 698) that were inside `logger.warning()` and `logger.info()` calls split across lines.

3. **The `ChangeMe123!` false positive in verification**: After fixing, `grep -r "ChangeMe123" backend/` still matched — but only in `__pycache__/vm_routes.cpython-314.pyc` (compiled bytecode from before the fix). The source code is clean. The `.pyc` files get regenerated automatically when the backend restarts.

**Key decisions:**
- **`secrets.token_urlsafe(16)` for passwords**: Produces a 22-character URL-safe string (letters, digits, hyphens, underscores). Chosen over `secrets.token_hex` because it's denser (more entropy per character) and doesn't have special characters that break shell copy-paste. Every VM now gets a unique password.
- **Credentials stored in `proxmox_response` JSONB**: Instead of adding a new DB column, I reused the existing `proxmox_response` field that `VMJobResponse` already exposes. For template-cloned VMs, this dict now contains `{"vmid": X, "ci_username": "ubuntu", "ci_password": "random_string"}`. For ISO VMs, it stays as `{"vmid": X, "result": "OK"}`. Zero schema changes needed.
- **Rollback deletes the orphaned VM, then re-raises**: The `except` block in `_provision_from_template()` attempts `proxmox.delete_vm()` for cleanup, but if even the cleanup fails, it logs and moves on — the original exception is still re-raised so the job gets marked "failed". The user sees the error; the orphaned VM is a known risk that can be cleaned up manually.
- **30-second timeout for stop polling in delete**: The old `time.sleep(5)` was a guess. The new `_wait_for_task(timeout=30)` polls every 2 seconds (using the existing `_CLONE_POLL_INTERVAL`). 30 seconds is generous — stops typically finish in 2-5 seconds — but safe.

**What I learned:**
- The `proxmox_response` JSONB column is a flexible "bag of data" — perfect for storing per-VM metadata like generated credentials without schema migrations. This pattern is common in job queue systems.
- Lazy logging (`logger.info("msg %s", val)`) isn't just about performance — if `str(val)` raises an exception, the lazy form catches it gracefully, while the f-string form would crash the request handler.

**If asked "How did you do this?":**
> I fixed 8 issues from the code review. The most important one was replacing a hardcoded password that every VM shared with a randomly generated one using Python's `secrets` module. I also added rollback logic so if provisioning fails halfway, the partially-built VM gets cleaned up. I replaced a hardcoded sleep with proper task status polling, removed duplicate authentication calls, added a guard against impossible disk shrink operations, and cleaned up all the logging to use lazy formatting.

**If asked "Where did you get stuck?":**
> The trickiest part was refactoring `_provision_from_template()` to do three things at once — generate a unique password, return it to the caller, AND handle rollback on failure. I had to change the return type from `int` to `dict`, wrap the post-clone steps in try/except, and update the caller to handle both the template path (dict with credentials) and the ISO path (simple dict with just vmid). Getting the rollback right was important because a half-built VM wastes server resources.
