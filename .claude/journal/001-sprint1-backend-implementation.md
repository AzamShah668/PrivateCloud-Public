---
date: 2026-04-02
title: Sprint 1 Retrospective — Full Backend Implementation
task: "Iteration 1 — Full backend implementation"
sprint: 1
---

### 2026-04-02 — Sprint 1 Retrospective (Backfill)

**Task:** Iteration 1 — Full backend implementation

**What was done:**
We built the entire backend from scratch during Sprint 1. This included user authentication (register/login with JWT tokens), VM creation through the Proxmox API, audit logging for every action, and daily quota limits so users can't spin up unlimited VMs. We also set up the PostgreSQL database with Docker Compose and wrote all the schema DDL with a schema-on-startup pattern.

**Files changed:**
- `backend/app/main.py` — FastAPI app entry point with lifespan handler (init DB on startup, close pool on shutdown)
- `backend/app/auth.py` — JWT token creation/verification, password hashing with bcrypt, FastAPI auth dependencies
- `backend/app/proxmox_client.py` — HTTP client that talks to Proxmox VE API with ticket-based auth
- `backend/app/routes/auth_routes.py` — Register, login, and "get me" endpoints
- `backend/app/routes/vm_routes.py` — Create VM, list VMs, get VM status endpoints with quota enforcement
- `backend/app/models/user.py` — Pydantic schemas for user input validation
- `backend/app/models/vm.py` — Pydantic schemas for VM requests and job tracking
- `db/database.py` — PostgreSQL connection pool, all tables (users, vm_jobs, audit_logs), helper functions
- `docker-compose.yml` — PostgreSQL 16 + backend service on shared Docker network

**Problems encountered:**
1. **Proxmox API authentication**: Proxmox uses ticket-based auth that expires after 2 hours
   - *First attempt*: Authenticate once at startup
   - *Why it failed*: Tickets expire, causing 401 errors on long-running instances
   - *Solution*: Auto-renewal at 115 minutes (5 min before expiry) inside ProxmoxClient

2. **OS ISO mapping**: Different OS choices need different Proxmox `ostype` and ISO file paths
   - *First attempt*: Hardcoded ISO paths
   - *Why it failed*: Not flexible, hard to maintain
   - *Solution*: Created `_OS_MAP` dictionary mapping OS choices to their ostype and ISO paths

**Key decisions:**
- **Raw psycopg2 instead of SQLAlchemy ORM**: We wanted to understand exactly what SQL was running. For a university project, showing raw SQL demonstrates we understand databases, not just an abstraction layer.
- **Schema-on-startup (CREATE TABLE IF NOT EXISTS)**: No migration tool needed. The app creates tables if they don't exist when it boots. Simple and works perfectly for our scale.
- **Synchronous VM creation**: We create the VM and wait for the Proxmox task to complete before responding. Simpler than async polling for now.

**What I learned:**
- Connection pooling matters even for small apps — without it, we'd open/close DB connections on every request
- JWT tokens need to store minimal claims (just user_id and role) — don't put sensitive data in them since they're base64, not encrypted

**If asked "How did you do this?":**
> We built a FastAPI backend with three layers: auth (JWT-based), a Proxmox HTTP client that creates real VMs via their REST API, and a PostgreSQL database with raw SQL. Everything runs in Docker containers on the same network.

**If asked "Where did you get stuck?":**
> The hardest part was Proxmox API authentication — their ticket system expires after 2 hours, so we had to build auto-renewal logic. Also figuring out the right ISO paths for different OS templates took trial and error.
