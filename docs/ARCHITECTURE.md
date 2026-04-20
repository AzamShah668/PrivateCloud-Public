# PrivateCloud Architecture

## System Overview

**PrivateCloud** is a FastAPI backend + React frontend for managing Proxmox VMs with user authentication, audit logging, and admin controls.

```
┌─────────────────────────────────────────────────────────────────┐
│ Frontend (React + TypeScript, frontend/)                         │
│ ├─ Dashboard: List user's VMs + daily quota usage               │
│ ├─ Create VM: Form → POST /api/vms                              │
│ ├─ VM Detail: Status, credentials, actions (start/stop/delete)  │
│ ├─ User Profile: GET/PATCH /api/auth/me                         │
│ └─ Admin: Users, VMs, Audit logs, Settings                      │
└─────────────────────────────────────────────────────────────────┘
                           HTTP/REST
┌─────────────────────────────────────────────────────────────────┐
│ Backend (FastAPI, backend/app/)                                  │
│ ├─ auth_routes.py: Register, Login, Profile, JWT tokens         │
│ ├─ vm_routes.py: Create, List, Get, Update, Delete              │
│ ├─ admin_routes.py: Users, VMs, Audit, Settings (all endpoints) │
│ ├─ proxmox_client.py: API client + token auth + error handling   │
│ ├─ models/: Pydantic request/response schemas                    │
│ └─ auth.py: JWT encoding/decoding + user dependency             │
└─────────────────────────────────────────────────────────────────┘
                      psycopg2 (ThreadedPool)
┌─────────────────────────────────────────────────────────────────┐
│ PostgreSQL (Docker: postgres:16, db/database.py)                 │
│ ├─ users: id, username, password_hash, role, daily_quota, ...   │
│ ├─ vm_jobs: user_id, vmid, vm_name, os_choice, status, ...      │
│ ├─ audit_logs: user_id, action, target_type, target_id, ...     │
│ └─ system_settings: key-value store (admin config)               │
└─────────────────────────────────────────────────────────────────┘
                           REST API
┌─────────────────────────────────────────────────────────────────┐
│ Proxmox VE (VM host, token auth via ProxmoxClient)               │
│ ├─ Clone golden image template to create new VMs                │
│ ├─ Start/stop/restart VMs                                       │
│ ├─ Poll for IP address once VM is running                       │
│ └─ Resize CPU/RAM (via qm config)                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## Class Diagram (CRC Cards)

### Core Models (Pydantic)

**UserInDB** (user.py)
- Responsibility: User domain entity (created at registration)
- Fields: id, username, password_hash, role, daily_quota, created_at, deleted_at, status
- Collaborators: auth_routes (login), admin_routes (user mgmt)

**VMCreateRequest** (vm.py)
- Responsibility: Validate VM creation input from frontend
- Fields: vm_name, os_choice
- Collaborators: vm_routes.create_vm()

**VMEnrichedResponse** (vm.py)
- Responsibility: Return VM job + live Proxmox status
- Fields: id, user_id, vmid, status, vm_ip, vm_username, vm_password, proxmox_status, created_at
- Collaborators: vm_routes.get_vm(), vm_routes.list_my_vms()

**AdminStatsResponse** (admin_routes.py)
- Responsibility: Dashboard stats (user count, VM count, failed jobs, etc.)
- Fields: total_users, total_admins, total_vms, active_vms, failed_vms, queued_vms
- Collaborators: admin_routes.get_stats()

**VMJobAdminResponse** (admin_routes.py)
- Responsibility: VM job view for admins (includes owner username)
- Fields: id, owner_username, vm_name, status, created_at, updated_at
- Collaborators: admin_routes.list_all_vms()

**TokenData** (auth.py)
- Responsibility: JWT payload (who you are + when token expires)
- Fields: sub (user_id), exp (expiration), iat (issued-at)
- Collaborators: auth.py (encode/decode), auth_routes (dependency)

### Service Layer

**ProxmoxClient** (proxmox_client.py:64)
- Responsibility: Bridge to Proxmox REST API with token auth
- Methods:
  - `_ensure_authenticated()` — obtain ticket + token
  - `._get() / ._post() / ._put() / ._delete()` — HTTP verbs
  - `get_task_status()` — poll long-running operations
  - `clone_vm()`, `start_vm()`, `stop_vm()`, `resize_vm()`
- Collaborators: vm_routes (VM lifecycle), proxmox_client (self-managing)

**Database Layer** (db/database.py)
- Responsibility: SQL queries + connection pooling
- Methods: user CRUD, vm_job CRUD, audit logging, settings CRUD
- Collaborators: all routes (data access)

### Route Handlers

**auth_routes.py** — Authentication & User Management
- POST /auth/register: Create new user account
- POST /auth/login: Authenticate + return JWT
- GET /auth/me: Fetch current user profile
- PATCH /auth/me: Update username/password/quota

**vm_routes.py** — VM Lifecycle
- POST /vms: Create VM (queued → background provisioning)
- GET /vms: List current user's VMs
- GET /vms/{job_id}: Get VM details + live Proxmox status
- PATCH /vms/{job_id}: Perform action (start/stop/restart/resize)
- DELETE /vms/{job_id}: Destroy VM + purge from Proxmox

**admin_routes.py** — Admin Dashboard & Settings
- GET /admin/stats: Dashboard card counts
- GET /admin/users: List all users with quotas
- GET /admin/vms: List all VMs (across all users) with owner names
- GET /admin/audit: Audit log entries (filterable by action_type)
- PATCH /admin/users/{id}/role: Change user role
- PATCH /admin/users/{id}/quota: Adjust daily quota
- GET/PATCH /admin/settings: Read/write platform settings

---

## Sequence Diagrams (Key Flows)

### 1. User Registration & Login

```
User (Frontend)        Backend           Database        Proxmox
   │                     │                   │               │
   ├─ POST /register ──→ │                   │               │
   │  (username, pwd)    │                   │               │
   │                     ├─ Hash password   │               │
   │                     ├─ INSERT user ───→ │               │
   │                     │ ← user.id        │               │
   │                     ├─ INSERT audit ──→ │               │
   │                     ├─ UserResponse ──→ │
   │                     ←─────────────────→ │               │
   ├─ 201 + token ←─────┤                   │               │
   │                     │                   │               │
   ├─ POST /login ─────→ │                   │               │
   │  (username, pwd)    │                   │               │
   │                     ├─ SELECT user ───→ │               │
   │                     │ ← row            │               │
   │                     ├─ Verify bcrypt   │               │
   │                     ├─ Encode JWT      │               │
   │                     ├─ INSERT audit ──→ │               │
   │                     ├─ TokenResponse ──→ │
   │                     ←─────────────────→ │               │
   │                     │                   │               │
   ├─ 200 + JWT ←───────┤                   │               │
```

### 2. VM Creation (Async Background Provisioning)

```
User (Frontend)        Backend           Database        Proxmox
   │                     │                   │               │
   ├─ POST /vms ──────→ │                   │               │
   │  (vm_name, os)     │                   │               │
   │                     ├─ Check quota ───→ │               │
   │                     │ ← count          │               │
   │                     ├─ Increment quota  │               │
   │                     ├─ INSERT vm_job ─→ │               │
   │                     │ ← job_id         │               │
   │                     ├─ INSERT audit ──→ │               │
   │                     ├─ Spawn background task
   │                     ├─ VMJobResponse ──→ │
   │                     ←─────────────────→ │               │
   ├─ 202 (queued) ←───┤                   │               │
   │                     │                   │               │
   │                     │ ┌─ BACKGROUND TASK ──────────────┐
   │                     │ │ 1. _ensure_authenticated() ───→ │
   │                     │ │ 2. Get VMID ────────────────→ │
   │                     │ │    ← vmid                     │
   │                     │ │ 3. clone_vm(golden → vmid) ──→ │
   │                     │ │    (wait for task)            │
   │                     │ │ 4. start_vm(vmid) ───────────→ │
   │                     │ │ 5. Poll for IP address ─────→ │
   │                     │ │    (retry 60x, 5s intervals)  │
   │                     │ │ 6. UPDATE vm_job ──────────→ │
   │                     │ │    (status=done, vm_ip, ...) │
   │                     │ │ 7. INSERT audit ────────────→ │
   │                     │ └──────────────────────────────┘
   │                     │                   │               │
   ├─ [polling] ──────→ │ GET /vms/{id} ───┐ │               │
   │                     │ SELECT vm_job ────→ │               │
   │                     │ ← (status, ip, pwd) │               │
   │                     ├─ Live Proxmox check ──────────────→ │
   │                     │                ← status             │
   │                     ├─ VMEnrichedResponse ──→ │
   │                     ←─────────────────→ │               │
   ├─ 200 (done) ◄─────┤                   │               │
```

### 3. Admin: Soft-Delete User

```
Admin (Frontend)       Backend           Database        Proxmox
   │                     │                   │               │
   ├─ POST /admin/users/{id}/suspend ──→ │   │               │
   │                     │                   │               │
   │                     ├─ soft_delete_user() (new helper)
   │                     │  UPDATE users ──→ │               │
   │                     │  SET status='suspended',
   │                     │      deleted_at=NOW() │           │
   │                     │                   │               │
   │                     ├─ INSERT audit ──→ │               │
   │                     │ (action_type='user.suspend',
   │                     │  target_user_id=:id) │            │
   │                     │                   │               │
   │                     ├─ UserResponse ──→ │
   │                     ←─────────────────→ │               │
   │                     │                   │               │
   ├─ 200 ◄────────────┤                   │               │
```

---

## Data Flow: Audit Logging

Every significant action is logged to `audit_logs`:

| Action | action_type | target_type | target_id | target_user_id |
|--------|------------|-------------|-----------|----------------|
| User registers | user.create | user | {user_id} | NULL |
| Admin changes user role | user.role_change | user | {user_id} | {user_id} |
| User creates VM | vm.create | vm_job | {job_id} | NULL |
| Admin suspends user | user.suspend | user | {user_id} | {user_id} |
| Admin updates setting | settings.change | setting | {key} | NULL |

**Query Patterns:**
- All actions by admin X: `WHERE user_id = :admin_id`
- All actions ON user Y: `WHERE target_user_id = :user_id`
- Filter by action type: `WHERE action_type = 'user.create'`

---

## Sprint 3 Scope (I3)

✓ All **I3 features complete**:
- [x] Admin Dashboard (/admin/stats, users, vms, audit, settings)
- [x] Soft-delete users (deleted_at + status columns)
- [x] Audit action taxonomy (action_type enum)
- [x] Admin action attribution (target_user_id FK)
- [x] System settings table (key-value platform config)
- [x] User profile view/update (GET/PATCH /auth/me)
- [x] VM details + live status enrichment (GET /vms/{id})

**I4 Deferred:**
- Per-user resource caps (CPU/RAM aggregates — schema support ready, logic deferred)
- Email field on users (rejected for I3; backward-incompatible)

---

## File Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py            — FastAPI app setup
│   │   ├── auth.py            — JWT encoding/decoding
│   │   ├── models/
│   │   │   ├── user.py        — User domain entity
│   │   │   ├── vm.py          — VM request/response schemas
│   │   ├── routes/
│   │   │   ├── auth_routes.py
│   │   │   ├── vm_routes.py
│   │   │   ├── admin_routes.py
│   │   ├── proxmox_client.py  — Proxmox API client
│   │   └── dependencies.py    — get_current_user, etc.
│   └── Dockerfile             — Python 3.12 + FastAPI
├── db/
│   └── database.py            — PostgreSQL schema + helpers
├── frontend/
│   ├── src/
│   │   ├── components/        — React components
│   │   ├── pages/             — Dashboard, Admin, Profile
│   │   ├── api/               — API client + types
│   │   └── App.tsx            — Root component
│   └── vite.config.ts         — Vite config
├── docs/
│   ├── ARCHITECTURE.md        — This file
│   ├── api-routes.md          — REST endpoint reference
│   └── db-schema.md           — Database schema DDL
└── docker-compose.yml         — Multi-container setup
```

---

## References

- **Issue #25**: Admin Portal (Complete)
- **Issue #26**: Admin DB Design (Complete)
- **Journal Entry 011**: Admin Portal Full-Stack Implementation
- **Journal Entry 014**: I3 DB Schema Extensions
