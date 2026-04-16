# 011 — Admin Portal: Full-Stack Implementation

**Date:** 2026-04-15
**Sprint:** 3
**Task:** Issue #25 — Admin Portal (from Kanban board)

---

## What Was Done

I built a complete admin portal from scratch — backend API endpoints + full frontend UI — using only the existing database tables (`users`, `vm_jobs`, `audit_logs`). We agreed to skip DB schema changes because Nashid (SheikhMohammadNashid) owns the database design and hasn't completed it yet. So every query I wrote works against the tables that already exist from Sprint 1.

The backend has 6 new API endpoints under `/admin/*`, all protected by the existing `require_admin` dependency. The frontend is a separate admin layout (AdminShell) with its own sidebar, topbar, and 5 pages — all styled with the same AETHER_CLOUD design system but using amber accents instead of cyan to visually distinguish the admin context.

I followed TDD for the backend: wrote 15 tests first, then implemented to make them pass. The frontend was built visually since the components are primarily UI — TypeScript type-checking served as the verification step there.

## Files Changed

- `db/database.py` — Added 5 admin helper functions (`list_all_users`, `list_all_vm_jobs`, `get_admin_stats`, `update_user_role`, `update_user_quota`)
- `backend/app/routes/admin_routes.py` — NEW: 6 admin endpoints (stats, users, vms, audit-logs, role change, quota change), all using `Depends(require_admin)`
- `backend/app/main.py` — Added `admin_router` import and `app.include_router(admin_router)`
- `backend/tests/__init__.py` — NEW: empty init for test package
- `backend/tests/conftest.py` — NEW: shared pytest fixtures (TestClient, JWT tokens, mocked `get_user_by_username`)
- `backend/tests/test_admin_routes.py` — NEW: 15 tests covering all 6 endpoints (admin access, user rejection, unauthenticated rejection, invalid input, missing resources)
- `frontend/src/api/admin.ts` — NEW: 6 API functions matching backend endpoints, using the shared `ky` client
- `frontend/src/hooks/use-admin.ts` — NEW: 7 React Query hooks (4 queries with auto-refetch, 3 mutations with toast notifications)
- `frontend/src/components/shared/AdminRoute.tsx` — NEW: route guard that redirects non-admin users to `/`
- `frontend/src/components/admin/AdminShell.tsx` — NEW: admin layout with AdminTopBar (amber "Admin Panel" badge, search, cluster status) + outlet
- `frontend/src/components/admin/AdminSidebar.tsx` — NEW: amber-themed sidebar with "Back to Dashboard" button, Management section (Dashboard, VMs, Users, Audit Logs), System section (Settings)
- `frontend/src/components/admin/AdminClusterHealth.tsx` — NEW: SVG network topology with 7 nodes (Core, 2 compute, 2 storage, 2 network), animated connection lines, and data packet animations using motion/react
- `frontend/src/components/admin/AdminLiveCharts.tsx` — NEW: 3 live area charts (CPU, Memory, Storage I/O) using Recharts with auto-updating data every 1.5 seconds
- `frontend/src/components/admin/AdminRecentActivity.tsx` — NEW: two-panel layout showing recent audit log entries (with action icons and time-ago) + recent VM deployments (with status badges)
- `frontend/src/pages/admin/AdminDashboardPage.tsx` — NEW: "Command Center" page with 5 animated stat cards, cluster health panel, live charts, and recent activity
- `frontend/src/pages/admin/AdminVMsPage.tsx` — NEW: searchable/filterable table of all VMs across all users, shows owner username, resources (CPU/RAM/disk), and status badges
- `frontend/src/pages/admin/AdminUsersPage.tsx` — NEW: user card grid with inline role toggle (promote/demote button) and click-to-edit quota
- `frontend/src/pages/admin/AdminAuditLogsPage.tsx` — NEW: audit log table with action type filter buttons, details preview, timestamps
- `frontend/src/pages/admin/AdminSettingsPage.tsx` — NEW: "Coming Soon" placeholder with construction icon
- `frontend/src/App.tsx` — Added admin route tree: `ProtectedRoute > AdminRoute > AdminShell > [admin pages]`
- `frontend/src/components/layout/Sidebar.tsx` — Added "Admin Portal" link (amber shield icon) visible only when `user.role === "admin"`

## Problems Encountered

1. **pytest couldn't find modules**: When I ran `python -m pytest`, it said `No module named pytest` even though pip showed it was installed. Turns out the venv is symlinked from `Desktop/proxmox/backend/venv` — a different path than the project. 
   - *First attempt*: Ran `./venv/Scripts/python.exe -m pytest` — got `No module named pytest`
   - *Why it failed*: The symlinked venv's python.exe didn't have pytest on its path
   - *Solution*: Used the full real path `"c:/Users/AZAM RIZWAN/Desktop/proxmox/backend/venv/Scripts/python.exe" -m pytest` and set `PYTHONPATH="backend:$PYTHONPATH"` so `db` and `app` modules could be found

2. **TypeScript unused imports**: I imported several lucide-react icons (`HardDrive`, `Cpu`, `MemoryStick`, `TrendingUp`, `Clock`, `ScrollText`, `Server`, `Users`, `ChevronDown`, `ExternalLink`, `Settings`) that I planned to use but ended up not needing in the final components.
   - *First attempt*: Build failed with 10+ "declared but never read" errors
   - *Solution*: Removed all unused imports one file at a time

3. **TypeScript `undefined` index type on CONNECTIONS array**: The `CONNECTIONS` array is `string[][]`, so destructuring `[from, to]` gives `string | undefined`. Accessing `nodeMap[from]` then fails with "Type 'undefined' cannot be used as an index type."
   - *First attempt*: Used `from!` non-null assertion — still failed because the nodeMap lookup result could be undefined
   - *Solution*: Cast with `as string` and added an early `if (!a || !b) return null` guard

4. **No admin user existed in the database**: After building everything, user couldn't access `/admin` because all 7 users in the DB had `role = 'user'`.
   - *Solution*: Ran `UPDATE users SET role = 'admin' WHERE username = 'azam'` via `docker exec`

## Key Decisions

- **Amber accent for admin vs cyan for user**: I chose amber (#F59E0B) as the admin accent color to create clear visual separation from the user portal's cyan (#0AEFFF). This way admins immediately know they're in the admin context. The sidebar logo gradient shifts from cyan/blue to amber/red.

- **Existing tables only, no schema changes**: Since Nashid owns DB design, I wrote all queries against `users`, `vm_jobs`, and `audit_logs`. The `get_admin_stats()` function uses a single SQL query with 9 subselects — efficient and avoids multiple round trips.

- **Separate AdminShell instead of conditional rendering in AppShell**: I created a completely independent layout rather than adding admin/user conditionals to the existing AppShell. This keeps both layouts clean and makes the admin portal independently extensible without risking regressions in the user dashboard.

- **Mocked DB in tests, not real DB**: Since there's no test database setup, I used `unittest.mock.patch` to mock all `database.*` calls. This makes tests fast (15 tests in 0.22s) and doesn't require a running PostgreSQL instance. The test fixtures create real JWT tokens though — so auth flow is genuinely tested.

## What I Learned

- Using a single SQL query with multiple subselects (`get_admin_stats`) is much more efficient than making 9 separate queries. PostgreSQL handles this well because the subselects are simple COUNT operations on indexed tables.
- Framer Motion's `layoutId` for sidebar active state animation works great for shared layout animations between route transitions — the amber glow pill smoothly slides between nav items.
- FastAPI's `Depends(require_admin)` dependency chain is elegant — it calls `get_current_user` internally, so you get both auth + authorization in a single dependency.

## If Asked "How Did You Do This?"

> I built the admin portal in layers: first the database helper functions that query existing tables, then FastAPI endpoints protected by the `require_admin` dependency, then 15 pytest tests to verify auth and data flow, and finally the React frontend with its own layout shell, API hooks, and 5 pages. I used the same AETHER_CLOUD design system as the user portal but swapped cyan accents for amber to visually distinguish the admin context.

## If Asked "Where Did You Get Stuck?"

> The trickiest part was the pytest setup — the virtual environment is symlinked from a different directory, so `python -m pytest` couldn't find the module even though pip showed it installed. I had to trace the real path and set PYTHONPATH manually. On the frontend side, TypeScript's strict null checking caught an undefined index issue in my SVG cluster topology that would have been a runtime error.
