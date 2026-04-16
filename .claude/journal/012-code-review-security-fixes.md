# 012 — Code Review: Security & Quality Fixes

**Date:** 2026-04-15
**Sprint:** 3
**Author:** Claude Code (Opus 4.6) + Azam
**Branch:** azams-branch

---

## What Was Done

A comprehensive code review was performed across the entire uncommitted changeset (58 files: 30 modified + 28 new). Three parallel review agents analyzed the backend, admin frontend, and core frontend/dashboard respectively. The review uncovered **2 CRITICAL, 12 HIGH, 15 MEDIUM, and 7 LOW** issues. This journal documents every fix applied.

---

## Summary of Fixes

| ID | Severity | Status | Issue | File(s) |
|----|----------|--------|-------|---------|
| C1 | CRITICAL | FIXED | JWT secret key uses insecure default | `backend/app/auth.py` |
| C2 | CRITICAL | FIXED | AdminRoute bypassed when `user` is null | `frontend/src/components/shared/AdminRoute.tsx` |
| H1 | HIGH | FIXED | `ci_password` persisted in plain text | `backend/app/routes/vm_routes.py` |
| H3 | HIGH | FIXED | Admin can demote themselves | `backend/app/routes/admin_routes.py` |
| H6 | HIGH | FIXED | False `as VMEnriched` cast | `frontend/src/pages/VMDetailPage.tsx` |
| H7 | HIGH | FIXED | `isError` never handled on VM pages | `VMDetailPage.tsx`, `DashboardPage.tsx` |
| H8 | HIGH | DOCUMENTED | Auth store hydration race | `frontend/src/stores/auth-store.ts` |
| H9 | HIGH | FIXED | Role toggle fires without confirmation | `frontend/src/pages/admin/AdminUsersPage.tsx` |
| H10 | HIGH | FIXED | `onError` drops server error details | `frontend/src/hooks/use-admin.ts` |
| H11 | HIGH | FIXED | Quota validation silently no-ops | `frontend/src/pages/admin/AdminUsersPage.tsx` |
| H12 | HIGH | FIXED | Unsafe `as number` casts on unknown | `frontend/src/pages/VMDetailPage.tsx` |
| M1 | MEDIUM | FIXED | `update_vm_job` NULLs existing data | `db/database.py` |
| M3 | MEDIUM | FIXED | Manual validation instead of Pydantic | `backend/app/routes/admin_routes.py` |
| M13 | MEDIUM | FIXED | `formatTimeAgo` crashes on invalid dates | `AdminRecentActivity.tsx` |
| — | LOW | FIXED | `React.ReactNode` without import | `VMDetailPage.tsx` |
| — | MEDIUM | FIXED | `datetime` type mismatch in admin responses | `backend/app/routes/admin_routes.py` |

---

## Detailed Fix Documentation

### C1: JWT Secret Key — Insecure Default (CRITICAL)

**File:** `backend/app/auth.py:48`

**Problem:** The JWT signing key fell back to a hardcoded string `"CHANGE_ME_IN_PRODUCTION_use_a_long_random_string"` if the `JWT_SECRET_KEY` environment variable was not set. Any attacker who reads the repo can forge admin tokens against a deployment that forgot to set this variable.

**Root cause:** `os.getenv()` with a default value silently returns the default — no startup check.

**Fix:** Added a startup warning when the insecure default is detected. The warning prints a clear message explaining the risk and how to generate a proper key:
```python
_INSECURE_DEFAULT = "CHANGE_ME_IN_PRODUCTION_use_a_long_random_string"
SECRET_KEY = os.getenv("JWT_SECRET_KEY", _INSECURE_DEFAULT)

if SECRET_KEY == _INSECURE_DEFAULT:
    import warnings
    warnings.warn(
        "JWT_SECRET_KEY is not set — using insecure default. "
        "Set JWT_SECRET_KEY in .env or environment. "
        "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\"",
        stacklevel=1,
    )
```

**Why warning, not RuntimeError:** During local development, requiring the env var would break the dev experience. A commented-out `raise RuntimeError(...)` is included for production deployments.

**How to verify:** Start the backend without `JWT_SECRET_KEY` set — you should see the warning in logs.

---

### C2: AdminRoute Auth Bypass (CRITICAL)

**File:** `frontend/src/components/shared/AdminRoute.tsx`

**Problem:** The route guard only checked `if (user && user.role !== "admin")`. When `user` was `null` (initial state before `useCurrentUser()` hydrates the profile), the condition was `false`, so `<Outlet />` rendered — giving unauthenticated visitors access to all admin pages.

**Root cause:** The guard assumed `user` would always be populated by the time it rendered. But `ProtectedRoute` passes `isLoading: false` before `useEffect` propagates `setUser(data)` to the Zustand store.

**Fix:** Three-way check:
1. Not authenticated at all → redirect to `/login`
2. Authenticated but `user` is null (still hydrating) → show `<Spinner />`
3. Authenticated and user loaded, but role is not admin → redirect to `/`

```tsx
if (!isAuthenticated) return <Navigate to="/login" replace />;
if (!user) return <Spinner />; // still hydrating
if (user.role !== "admin") return <Navigate to="/" replace />;
return <Outlet />;
```

**How to verify:** Open an incognito browser and navigate to `localhost:3000/admin` without logging in — should redirect to `/login`.

---

### H1: ci_password Persisted in Plain Text (HIGH)

**File:** `backend/app/routes/vm_routes.py:220-226`

**Problem:** The `_provision_from_template()` function returned `ci_password` in its result dict. This dict was passed directly to `database.update_vm_job(proxmox_response=...)`, storing the plain-text cloud-init password in the `vm_jobs.proxmox_response` JSONB column. The password was then visible:
- In the database forever
- In `GET /vms/:id` responses
- In `GET /admin/vms` responses to all admins

**Fix:** Before persisting, strip `ci_password` from the result:
```python
stored_result = {k: v for k, v in provision_result.items()
                 if k not in ("ci_password",)}
database.update_vm_job(..., proxmox_response=stored_result)
```

The password is still returned in the API response to the creating user (one-time display), but never stored at rest.

**How to verify:** Create a new template-based VM, then check the `vm_jobs` table — `proxmox_response` should contain `vmid` and `ci_username` but NOT `ci_password`.

---

### H3: Admin Self-Demotion (HIGH)

**File:** `backend/app/routes/admin_routes.py:159-168`

**Problem:** `PATCH /admin/users/{id}/role` allowed an admin to change their own role to `"user"`, potentially locking all admins out of the system if they were the last admin.

**Fix:** Added a guard at the top of `change_user_role`:
```python
if user_id == admin.id:
    raise HTTPException(status_code=400, detail="Admins cannot change their own role.")
```

**How to verify:** As an admin, try to change your own role via the API or the admin panel — should get a 400 error.

---

### M3: Pydantic Validators Replace Manual Checks (MEDIUM)

**File:** `backend/app/routes/admin_routes.py:78-84`

**Problem:** `UpdateRoleRequest.role` was typed as `str` with manual validation in the handler. `UpdateQuotaRequest.daily_quota` was `int` with manual bounds checking.

**Fix:** Used Pydantic's built-in validators:
```python
from typing import Literal
from pydantic import Field

class UpdateRoleRequest(BaseModel):
    role: Literal["user", "admin"]

class UpdateQuotaRequest(BaseModel):
    daily_quota: int = Field(ge=0, le=100)
```

Removed the manual `if` checks in both handlers. Pydantic now returns proper 422 validation errors with field-level detail, and the OpenAPI spec self-documents the constraints.

---

### H6+H12: Unsafe Type Casts in VMDetailPage (HIGH)

**File:** `frontend/src/pages/VMDetailPage.tsx:50-54`

**Problem:** 
1. `vm as VMEnriched` was a false cast — the single-get endpoint returns `VMJob`, not `VMEnriched`
2. `payload.cpu_cores as number` on `Record<string, unknown>` has no runtime effect — a string value would pass through silently

**Fix:**
1. Replaced the `as VMEnriched` cast with runtime property detection:
   ```ts
   const liveStatus = ("live_status" in vm && typeof vm.live_status === "string")
     ? vm.live_status : vm.status;
   ```
2. Created a `toNum()` helper for safe number extraction:
   ```ts
   function toNum(v: unknown, fallback: number): number {
     return typeof v === "number" ? v : fallback;
   }
   const currentCpu = toNum(payload.cpu_cores, 2);
   ```

---

### H7: Missing isError Handling (HIGH)

**Files:** `VMDetailPage.tsx:19`, `DashboardPage.tsx:13`

**Problem:** Both pages destructured only `{ data, isLoading }` from their hooks. When the API returned an error (network failure, 500), the pages silently showed "VM not found" or an empty dashboard with no indication that something went wrong.

**Fix:**
- **VMDetailPage:** Added `isError` to destructuring. When `isError` is true, renders an error state with an `AlertTriangle` icon and "Failed to load VM details" message.
- **DashboardPage:** Added `isError` to destructuring. When `isError` is true, renders a warning banner at the top: "Failed to load VMs. Data shown may be stale."

---

### H9: Role Toggle Without Confirmation (HIGH)

**File:** `frontend/src/pages/admin/AdminUsersPage.tsx:27-30`

**Problem:** Clicking "Promote" or "Demote" immediately fired the mutation with zero confirmation. A single accidental click could grant admin privileges to any user.

**Fix:** Added `window.confirm()` gate before the mutation:
```ts
const action = newRole === "admin" ? "promote" : "demote";
const confirmed = window.confirm(
  `Are you sure you want to ${action} "${user.username}" to ${newRole}?`
);
if (!confirmed) return;
```

---

### H10: onError Drops Server Error Details (HIGH)

**File:** `frontend/src/hooks/use-admin.ts`

**Problem:** The `onError` handlers typed the error as `Error` and used `err.message`, which for `ky.HTTPError` just says "Request failed with status code 422" — the actual server validation message in the response body was lost.

**Fix:** Created an `extractErrorMessage()` helper that checks for `HTTPError` and reads the response body:
```ts
async function extractErrorMessage(err: unknown, fallback: string): Promise<string> {
  if (err instanceof HTTPError) {
    try {
      const body = await err.response.json<{ detail?: string }>();
      if (body.detail) return body.detail;
    } catch { /* body not JSON */ }
  }
  return err instanceof Error ? err.message || fallback : fallback;
}
```

Both `useUpdateUserRole` and `useUpdateUserQuota` now use this helper. Users will see the actual server error (e.g., "Admins cannot change their own role") instead of a generic HTTP status message.

---

### H11: Quota Validation Silent No-op (HIGH)

**File:** `frontend/src/pages/admin/AdminUsersPage.tsx:32-39`

**Problem:** When the user typed an invalid quota value (e.g., `-5`, `"abc"`, `500`), the function silently closed the edit field without saving or showing any feedback.

**Fix:**
1. Changed from `parseInt` to `Number()` + `Number.isInteger()` (catches inputs like `"10abc"` that `parseInt` would accept as `10`)
2. On invalid input, shows a `toast.error("Quota must be a whole number between 0 and 100")` and returns early — keeping the field open so the user can correct their input
3. Only clears the field and closes on successful validation

---

### M1: update_vm_job Data Erasure (MEDIUM)

**File:** `db/database.py:299-315`

**Problem:** The SQL `UPDATE` set `proxmox_response` and `error_message` to `NULL` when the caller only intended to update `status`. This happened on every `delete` operation — erasing the audit trail.

**Fix:** Changed the SQL to use `COALESCE`:
```sql
SET status           = %s,
    proxmox_response = COALESCE(%s, proxmox_response),
    error_message    = COALESCE(%s, error_message),
    updated_at       = %s
```

When `None` is passed for `proxmox_response` or `error_message`, the existing value is preserved instead of being overwritten with `NULL`.

---

### M13: formatTimeAgo Crashes on Invalid Dates (MEDIUM)

**File:** `frontend/src/components/admin/AdminRecentActivity.tsx:31-39`

**Problem:** `new Date(dateStr).getTime()` returns `NaN` for malformed strings. All comparisons then fail, producing `"NaNd ago"` in the UI.

**Fix:** Added a guard at the top of the function:
```ts
const parsed = new Date(dateStr);
if (isNaN(parsed.getTime())) return "unknown";
```

---

### Admin Response datetime Fix (from pre-review)

**File:** `backend/app/routes/admin_routes.py:59,60,73`

**Problem:** `VMJobAdminResponse` and `AuditLogResponse` defined `created_at`/`updated_at` as `str`, but the database returns `datetime` objects. Pydantic validation failed with a 500, making admin VM list always empty.

**Fix:** Changed type annotations from `str` to `datetime`. Added `from datetime import datetime` import. Pydantic serializes `datetime` to ISO strings in JSON responses automatically.

---

## Files Changed

| File | Changes |
|------|---------|
| `backend/app/auth.py` | C1: Startup warning for insecure JWT key |
| `backend/app/routes/admin_routes.py` | datetime fix, M3 Pydantic validators, H3 self-demotion guard, removed manual validation |
| `backend/app/routes/vm_routes.py` | H1: Strip ci_password before DB persist |
| `db/database.py` | M1: COALESCE in update_vm_job |
| `frontend/src/components/shared/AdminRoute.tsx` | C2: Three-way auth guard |
| `frontend/src/stores/auth-store.ts` | H8: Documentation comment |
| `frontend/src/pages/VMDetailPage.tsx` | H6+H7+H12: isError, toNum helper, safe live_status detection, ReactNode import |
| `frontend/src/pages/DashboardPage.tsx` | H7: isError banner |
| `frontend/src/pages/admin/AdminUsersPage.tsx` | H9: confirm dialog, H11: toast on invalid quota |
| `frontend/src/hooks/use-admin.ts` | H10: extractErrorMessage helper, async onError handlers |
| `frontend/src/components/admin/AdminRecentActivity.tsx` | M13: Guard against invalid dates |

---

## Known Issues NOT Fixed (Deferred)

These were identified in the review but deferred as lower priority or requiring larger refactoring:

| ID | Severity | Issue | Reason Deferred |
|----|----------|-------|-----------------|
| H2 | HIGH | No pagination on admin endpoints | Requires backend + frontend pagination infrastructure |
| H4 | HIGH | `time.sleep` blocks thread pool during clone | Requires architectural change to background task model |
| H5 | HIGH | `vm_routes.py` 888 lines | Requires refactor into sub-modules |
| M2 | MEDIUM | Failed/deleted jobs count toward daily quota | Policy decision needed |
| M4-M7 | MEDIUM | Fake/mock data shown as real (cluster health, charts, deployments) | Requires real metrics API endpoints |
| M8 | MEDIUM | AnimatedStatCard `started` ref prevents re-animation | Component refactor |
| M9 | MEDIUM | BackgroundEffects random values on every render | Minor visual issue |
| M10 | MEDIUM | MyInstances Stop/Start buttons have no onClick | Feature not yet implemented |
| M11 | MEDIUM | Admin search input does nothing | Feature not yet implemented |
| M15 | MEDIUM | Duplicate layoutId in AdminSidebar | Minor animation bug |

---

## Verification Steps

1. **TypeScript check:** `cd frontend && npx tsc --noEmit` — passes clean
2. **Backend restart:** `docker restart proxmox_backend` — starts without errors
3. **Admin VMs page:** Navigate to `/admin/vms` — now shows all 10 VMs (datetime fix)
4. **Admin route guard:** Open incognito → `localhost:3000/admin` → redirects to `/login`
5. **Role toggle:** Click Promote/Demote → confirmation dialog appears
6. **Quota validation:** Enter invalid number → toast error, field stays open
7. **VM detail error:** Network failure shows error state, not "VM not found"

---

## What I Learned

1. **Pydantic `str` vs `datetime`**: When the database returns Python `datetime` objects, Pydantic models must use `datetime` type — it auto-serializes to ISO strings in JSON. Using `str` causes validation to fail silently (500 error, empty UI).

2. **React auth guard race condition**: With Zustand + React Query, there's a gap between "query finished" and "useEffect sets store value". Route guards must handle the `null` intermediate state explicitly.

3. **`COALESCE` for partial updates**: When a SQL UPDATE function supports optional fields, use `COALESCE(%s, existing_column)` to avoid accidentally NULLing fields the caller didn't intend to change.

4. **ky HTTPError vs generic Error**: `ky` throws `HTTPError` subclass with `.response` — the actual server error message is in the response body, not in `.message`. Must await `response.json()` to get the detail.
