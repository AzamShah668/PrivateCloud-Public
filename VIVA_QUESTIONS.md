# PrivateCloud — Viva / Defense Prep (Top 100 Q&A)

A study guide of the 100 most likely questions a professor or examiner will ask
about the PrivateCloud project, with concise, technically accurate answers
grounded in the actual codebase.

---

## A. Project Overview & Motivation (1–10)

**1. What is the PrivateCloud project in one sentence?**
A self-hosted, Proxmox-backed private cloud platform that lets authenticated users provision, monitor, and manage virtual machines through a REST API and a React web portal.

**2. What real problem does it solve?**
It gives organizations (labs, startups, universities) the convenience of AWS-style VM provisioning on their own hardware — avoiding cloud bills, keeping data on-prem, and adding role-based control, quotas, and audit logs that bare Proxmox does not provide.

**3. Why did you choose Proxmox VE as the hypervisor?**
Proxmox is open-source, production-grade, supports both KVM (full VMs) and LXC (containers), exposes a complete REST API, and runs on commodity hardware — making it the closest free equivalent to vSphere or AWS EC2.

**4. Why build a custom layer instead of just using the Proxmox web UI?**
The native UI is admin-oriented and exposes the full hypervisor. We needed multi-tenant user accounts, daily quotas, audit trails, OS-template abstractions, and a developer-friendly REST API — features Proxmox does not ship.

**5. Who are the intended users?**
Three roles: (a) end users who request VMs from a catalog, (b) admins who manage users and infrastructure, and (c) developers who script against the REST API.

**6. What is your tech stack?**
Backend: FastAPI 0.110 on Python 3.12. Database: PostgreSQL 16 with raw psycopg2. Frontend: React + TypeScript + Vite. Infrastructure: Docker Compose orchestrating the backend and DB, talking to a Proxmox VE cluster over HTTPS.

**7. What is the current sprint status?**
Sprint 1 is complete: registration, login, JWT auth, VM CRUD against Proxmox, audit logging, and per-user daily quotas. Sprint 2 added the admin portal, VM provisioning UX, and DB schema extensions for richer admin features.

**8. What were your biggest design constraints?**
Run on a single Proxmox host with limited RAM, keep the codebase small enough for a 4-person team to understand end-to-end, and avoid heavy frameworks (no ORM, no Celery in Sprint 1) so debugging stays simple.

**9. How does this differ from OpenStack?**
OpenStack is a massive multi-service IaaS suite (Nova, Neutron, Keystone, etc.) requiring a team to operate. PrivateCloud is a thin opinionated layer over a single Proxmox cluster — orders of magnitude simpler, but limited to one hypervisor.

**10. What would you do differently if you started over?**
Pick async VM creation from day one (background worker + task queue), adopt SQLAlchemy Core for type safety without full ORM weight, and ship a proper migration tool (Alembic) instead of `CREATE TABLE IF NOT EXISTS`.

---

## B. System Architecture (11–20)

**11. Describe the high-level architecture.**
Three tiers: (1) browser/CLI client, (2) FastAPI backend on port 8000 handling auth, validation, business logic, and (3) two backing services — PostgreSQL on 5432 for state and Proxmox VE on 8006 for hypervisor operations.

**12. Why three tiers and not a monolith?**
Separating state (Postgres) from compute (Proxmox) from API logic lets each scale and fail independently. A Proxmox outage does not corrupt our DB; a DB restart does not destroy running VMs.

**13. Walk me through what happens when a user creates a VM.**
Client POSTs `/vms/` with a JWT → `get_current_user` validates the token and loads the user → `check_daily_quota` counts today's jobs → `ProxmoxClient.get_next_vmid()` reserves a VM ID → a row is inserted into `vm_jobs` with `status=queued` → either `clone_template` (fast) or `create_vm` (ISO) is called → status updated to `done`/`failed` → audit log written → JSON response returned.

**14. What is the Docker Compose topology?**
Two services on a bridge network `proxmox_net`: `postgres` (postgres:16-alpine with a named volume and a `pg_isready` healthcheck) and `backend` (Python 3.12-slim, depending on Postgres being healthy, with the source mounted for hot reload in dev).

**15. Why is the backend not in the same network as Proxmox?**
Proxmox runs on a physical host, often a separate subnet. The backend reaches Proxmox over HTTPS to its public-facing 8006 API, which is exactly how any external client would.

**16. How does the frontend talk to the backend?**
The Vite-built React SPA calls the FastAPI REST endpoints over HTTPS, attaching the JWT in an `Authorization: Bearer …` header. CORS is configured on the backend for the frontend origin.

**17. What is your deployment topology in production?**
Backend + Postgres in Docker on a hardened Linux VM, fronted by Nginx for TLS termination and reverse proxy. Proxmox runs on dedicated hardware. Frontend static bundle served by Nginx or a CDN.

**18. Where does the Proxmox cluster sit in this picture?**
Outside the application network entirely. The backend treats Proxmox as a remote resource accessed only through a single client class (`proxmox_client.py`), so the rest of the code is hypervisor-agnostic.

**19. What are the trust boundaries?**
Three: (1) browser ↔ backend (JWT-authenticated, TLS), (2) backend ↔ Postgres (private network, password auth), (3) backend ↔ Proxmox (TLS, API token in header). Each boundary is enforced separately.

**20. How is configuration managed?**
A single `.env` file consumed by both Docker Compose and the FastAPI process. Secrets (`JWT_SECRET_KEY`, `PROXMOX_TOKEN_SECRET`, DB password) live there and are never committed.

---

## C. FastAPI & Backend Design (21–30)

**21. Why FastAPI over Flask or Django?**
FastAPI gives async-ready I/O, automatic OpenAPI/Swagger docs, and Pydantic-based request/response validation out of the box — exactly what a typed REST API needs without writing schema code by hand.

**22. How does dependency injection work in FastAPI?**
Functions declared with `Depends(...)` are resolved per request. We use it for `get_current_user` (JWT validation) and `require_admin` (role check) so route handlers stay clean.

**23. Explain `Depends(get_current_user)`.**
It is a FastAPI dependency that extracts the Bearer token from the `Authorization` header (via `OAuth2PasswordBearer`), decodes it with `python-jose`, fetches the matching user from the DB, and either returns a `UserInDB` object or raises HTTP 401.

**24. How are routes organized?**
Each domain has its own file under `backend/app/routes/` — `auth_routes.py`, `vm_routes.py`, `admin_routes.py` — each declaring an `APIRouter` with a prefix and tag, mounted in `main.py` via `app.include_router()`.

**25. Why use Pydantic models?**
They give automatic input validation, type coercion, JSON serialization, and free OpenAPI schema generation. A bad request fails fast with a 422 before our handler runs.

**26. What is the difference between `XCreate`, `XResponse`, and `XInDB`?**
A naming convention: `XCreate` is request input (no auto fields like id), `XResponse` is what we return (no secrets), `XInDB` is the internal representation including sensitive fields like `password_hash`. Prevents accidental secret leakage.

**27. How do you handle errors globally?**
Pydantic raises 422 automatically. Auth failures raise 401. Custom Proxmox exceptions (`ProxmoxAuthError`, `ProxmoxAPIError`) are caught in routes and mapped to 502/503. All routes use try/except around external calls.

**28. How do you generate API documentation?**
FastAPI auto-generates Swagger UI at `/docs` and ReDoc at `/redoc` from the route signatures and Pydantic schemas — no hand-written OpenAPI spec required.

**29. Is the API synchronous or asynchronous?**
Sprint 1 is synchronous — the request blocks until Proxmox replies. This is acceptable for sub-second clones but blocks for ISO installs. Sprint 2's plan is to enqueue the job and return 202 Accepted with a poll URL.

**30. How do you log application events?**
A module-level `logger = logging.getLogger(__name__)` per file. `.info()` for significant events (login, VM created), `.error()` for failures, `.debug()` for diagnostics. Log level is set via env var.

---

## D. Database & PostgreSQL (31–40)

**31. Why PostgreSQL and not MySQL or SQLite?**
Postgres has first-class JSONB (we store `request_payload` and `proxmox_response` as JSONB), strong concurrency via MVCC, mature transaction semantics, and excellent tooling. SQLite cannot handle concurrent writes from a containerized backend.

**32. Why no ORM? Why raw psycopg2?**
For a small schema (3 tables) an ORM adds learning overhead, hides SQL, and complicates debugging. Raw psycopg2 with `RealDictCursor` keeps queries explicit, reviewable, and easy to optimize.

**33. What are the main tables and their purpose?**
`users` (accounts, roles, quotas), `vm_jobs` (every VM provisioning request and its lifecycle), `audit_logs` (immutable event trail for compliance and forensics).

**34. Why JSONB for `request_payload` and `proxmox_response`?**
The shape of these payloads can evolve as we add VM options or Proxmox returns extra fields. JSONB lets us store the full snapshot without schema migrations and still query into specific keys when needed.

**35. How do you manage connections?**
A `ThreadedConnectionPool(min=2, max=10)` is created at startup. The `_conn()` context manager borrows a connection per request and returns it to the pool on exit, avoiding the cost of opening a new TCP connection every call.

**36. How do you handle schema migrations?**
Schema-on-startup: `init_db()` runs `CREATE TABLE IF NOT EXISTS` for each table on boot, and `ALTER TABLE … ADD COLUMN IF NOT EXISTS` for new columns. It is idempotent. For a real production system Alembic would be better.

**37. How do you enforce a daily quota?**
`count_user_jobs_today(user_id)` runs a `SELECT COUNT(*) … WHERE user_id = $1 AND created_at >= today_utc`. The index `idx_vm_jobs_user_created` on `(user_id, created_at)` makes this O(log n).

**38. How do you ensure password hashes are never read into business code?**
The `UserResponse` Pydantic model omits `password_hash`. Only `UserInDB` includes it, and it is used only inside `auth.py` where bcrypt verification happens.

**39. How do you prevent SQL injection?**
Every query uses parameterized statements (`%s` placeholders) — psycopg2 escapes values safely. We never build SQL by string concatenation with user input.

**40. What happens if Postgres goes down?**
Pool exhaustion will cause new requests to fail with 500. We use Compose's `depends_on: condition: service_healthy` so the backend will not start until Postgres passes `pg_isready`. In production we would add retry/backoff and a circuit breaker.

---

## E. Authentication & Security (41–55)

**41. How does authentication work?**
Users register with username + password. Login posts credentials to `/auth/login`, the server verifies the bcrypt hash, then issues a signed JWT containing `sub` (username), `role`, and `exp`. Subsequent requests include `Authorization: Bearer <jwt>`.

**42. What is JWT and why use it?**
JSON Web Token — a signed, self-contained credential. We chose it because it is stateless (no server-side session table), works trivially across services, and is easy to validate.

**43. What algorithm signs your JWTs and why?**
HS256 (HMAC-SHA256) via `python-jose`. It uses a single shared secret (`JWT_SECRET_KEY`), which is fine for a single backend. If we had multiple services verifying tokens we would switch to RS256 with public/private keys.

**44. How do you store passwords?**
With `passlib`'s `CryptContext(schemes=["bcrypt"])`. Bcrypt is a slow adaptive hash designed for passwords — adjustable cost factor, built-in salt, resistant to GPU brute force. We never store or log plaintext.

**45. What attacks does bcrypt protect against?**
Rainbow-table attacks (per-password salt), brute force (slow by design), and timing attacks (constant-time compare via `verify_password`).

**46. How long is a JWT valid?**
Default 60 minutes, configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`. Short enough to limit damage from theft, long enough to not annoy users.

**47. Do you use refresh tokens?**
Not in Sprint 1. The user re-logs in when the access token expires. Refresh tokens are on the Sprint 2 backlog.

**48. What if a JWT is stolen?**
Until expiry, the attacker has the user's privileges — that is the trade-off of stateless tokens. Mitigations: short expiry, HTTPS-only transport, `Secure` + `HttpOnly` cookies for browser flows, and a future denylist for revoked tokens.

**49. How do you protect admin routes?**
The `require_admin` dependency reads the `role` claim from the validated JWT and raises 403 if it is not `admin`. Applied via `Depends(require_admin)` on every admin endpoint.

**50. What is OWASP Top 10 and which items did you address?**
A list of the most critical web app risks. We address: A01 broken access control (role checks + ownership checks), A02 crypto failures (bcrypt + TLS + JWT signing), A03 injection (parameterized SQL + Pydantic validation), A05 misconfig (no debug in prod, non-root container), A07 auth failures (lockout-friendly design, expiring tokens), A09 logging (audit log table).

**51. How do you handle CORS?**
FastAPI's `CORSMiddleware` allows the configured frontend origin only, with credentials. Wildcard origins are explicitly avoided.

**52. Why is the Docker image non-root?**
A `appuser` is created in the Dockerfile and the process runs as that user. If the container is ever exploited, the attacker does not get root inside the container — and a host escape needs additional vulnerabilities.

**53. How are secrets kept out of git?**
A `.env` file is git-ignored. `JWT_SECRET_KEY`, `PROXMOX_TOKEN_SECRET`, and DB credentials live there. The repo only ships `.env.example` placeholders.

**54. What is CSRF and do you need protection?**
Cross-Site Request Forgery — a malicious site triggering authenticated actions on yours. With JWT in `Authorization` header (not cookies) the browser does not auto-attach it cross-origin, so CSRF risk is reduced. If we move to cookie-based auth we would add a CSRF token.

**55. How do audit logs help security?**
Every privileged action (`vm.create`, `user.login`, `admin.*`) writes a row with `user_id`, `action`, `target`, `details`, and timestamp. This gives a forensic trail for incident response and compliance.

---

## F. Proxmox Integration (56–65)

**56. Walk me through the Proxmox client.**
`ProxmoxClient` in `proxmox_client.py` wraps the Proxmox REST API. It supports two auth modes (API token preferred, ticket as fallback), exposes typed methods like `create_vm`, `clone_template`, `start_vm`, and centralizes URL building, error handling, and SSL verification.

**57. Why prefer API tokens over username/password?**
Tokens are scoped, revocable, and never expire automatically. They send a single `Authorization: PVEAPIToken=…` header — no login round-trip, no CSRF dance, no cookie state. Far simpler and safer than ticket auth.

**58. How does ticket-based auth work as fallback?**
POST credentials to `/access/ticket` → receive a ticket and CSRF token → store as cookie → include `Cookie: PVEAuthCookie=…` and `CSRFPreventionToken` on writes → re-auth every ~115 minutes before the 2-hour expiry.

**59. What is `get_next_vmid()`?**
A Proxmox helper that returns the next free integer VM ID across the cluster. We call it before creating a VM so we always allocate a unique ID, even with concurrent admins.

**60. What is the difference between `create_vm` and `clone_template`?**
`create_vm` builds a fresh VM and attaches an installer ISO — the user must run the OS installer. `clone_template` does a fast full-clone of a pre-baked cloud-init template and the VM boots ready-to-use in seconds.

**61. Why support both?**
Templates are faster and more reliable, but require pre-baking. ISO install is the universal fallback for any OS, including Windows where no template exists yet.

**62. What is cloud-init?**
A Linux-world standard for first-boot configuration: it injects SSH keys, hostname, network, and packages into a generic image. Proxmox templates use cloud-init so a clone instantly becomes a personalized VM.

**63. Explain the boot order logic.**
If an ISO is attached we set `boot=order=ide2;scsi0` so the VM tries the CD-ROM first to install the OS, then falls back to disk. Without an ISO it is `boot=order=scsi0` — disk only.

**64. How do you handle Proxmox failures?**
Two custom exceptions: `ProxmoxAuthError` (401/403 from Proxmox → mapped to 503) and `ProxmoxAPIError` (any other failure → mapped to 502 with the upstream message in the body).

**65. What is a UPID?**
Unique Process Identifier — the string Proxmox returns for every async task (`UPID:pve:00001234:…`). We can poll `get_task_status(node, upid)` to know when a clone or start has finished.

---

## G. Frontend (66–72)

**66. What is the frontend stack?**
React + TypeScript built with Vite, styled with Tailwind. Forms use controlled components, API calls go through a typed client in `frontend/src/api/`, and routing is via React Router.

**67. Why Vite over Create React App?**
Vite is dramatically faster on dev startup and HMR (uses native ESM), has first-class TypeScript support, and is the modern default — CRA was deprecated by the React team.

**68. How does the frontend store the JWT?**
In `localStorage` keyed by app name. On every API call an axios interceptor adds the `Authorization: Bearer …` header. On 401 it clears storage and redirects to login.

**69. Is `localStorage` safe for a JWT?**
It is vulnerable to XSS — any script on the page can read it. We mitigate with strict CSP, no untrusted third-party scripts, and React's automatic escaping. A more defensive design would be `HttpOnly` cookies, which we plan for Sprint 2.

**70. How is admin UI separated from user UI?**
Routes under `/admin/*` are wrapped in an `AdminRoute` guard component that checks the role from the decoded token. The backend independently enforces `require_admin`, so a tampered token cannot bypass server-side checks.

**71. How does the frontend show VM live status?**
The `/vms/` GET returns `VMEnrichedResponse` which includes `live_status`, `cpu_usage`, `mem_usage`, etc. — fetched server-side from Proxmox at request time. The dashboard polls this every few seconds.

**72. What about real-time updates — websockets?**
Not in Sprint 1; we poll. Sprint 2's plan is to add WebSockets for job status push so we stop hammering the backend.

---

## H. Docker, DevOps & Deployment (73–80)

**73. Why Docker?**
Reproducible environments, isolated dependencies (Python 3.12, system libs), one-command bring-up, and a clean upgrade path. Same image runs in dev and prod.

**74. Walk me through the Dockerfile.**
Multi-stage: a builder stage installs Python deps, a runtime stage copies them and the code into a `python:3.12-slim` image, creates a non-root `appuser`, exposes 8000, and runs `uvicorn app.main:app`.

**75. Why use Docker Compose?**
Compose orchestrates the backend + Postgres together with a single `docker compose up`, declares the network, volumes, healthchecks, and `depends_on` ordering — perfect for dev and small prod deployments.

**76. What is `depends_on: condition: service_healthy`?**
The backend will not start until Postgres's `pg_isready` healthcheck passes. Without it we got intermittent connection-refused errors at boot because the backend started faster than the DB.

**77. How are healthchecks defined?**
Postgres uses `pg_isready -U postgres`. The backend uses `curl -f http://localhost:8000/` against the `/` health endpoint that returns `{"status":"ok"}`.

**78. How would you scale this horizontally?**
Run multiple backend containers behind a load balancer (Nginx or Traefik). State lives in Postgres and Proxmox, so the backend itself is stateless. The DB scales vertically first; logical replication later if needed.

**79. How is Postgres data persisted?**
A named Docker volume `postgres_data` mounted at `/var/lib/postgresql/data`. Volume survives container restarts and image rebuilds.

**80. What CI/CD do you have?**
Sprint 1 is manual: run tests, build, push. Sprint 2 plan: GitHub Actions running pytest + ruff + type-check on PR, and an auto-deploy to staging on merge to `main`.

---

## I. Code Quality, Testing, Conventions (81–88)

**81. How do you ensure code quality?**
Conventions documented in `.claude/docs/conventions.md`: small files (<800 lines), small functions (<50 lines), no deep nesting, banner comments on each file, grouped imports, parameterized SQL only. Code review on every PR.

**82. What is your testing strategy?**
Unit tests for pure helpers (auth, validators), integration tests hitting a test Postgres for DB helpers and routes, and E2E tests (planned) using Playwright for the React frontend. Target ≥80% coverage.

**83. How do you test Proxmox interactions?**
Mock the `ProxmoxClient` in unit tests, then run a small set of integration tests against a real test Proxmox instance for confidence. We never mock the DB in integration tests.

**84. How do you avoid breaking the API?**
Pydantic schemas act as the contract. Changes to response models go through PR review, and additive changes (new optional fields) are preferred over breaking ones. OpenAPI diff would be a future addition.

**85. What is your branching strategy?**
Trunk-based with feature branches: `azams-branch`, etc. Branch off `main`, push, open PR, code review, squash-merge.

**86. What tools do you use for linting?**
Python: `ruff` for lint and format. TypeScript: `eslint` + `prettier`. Pre-commit hooks could enforce these but are not in place yet.

**87. How do you log significant events?**
`logger.info(...)` for VM created, user login, admin actions. `logger.error(...)` for failures with `exc_info=True`. Logs go to stdout — Docker captures them.

**88. How do you debug a production issue?**
Check the audit log table for the action, find the corresponding `vm_jobs` row for `proxmox_response` or `error_message`, then correlate with backend logs by timestamp and user ID. Reproduce locally with the same payload.

---

## J. Trade-offs, Improvements, Theory (89–100)

**89. What is the biggest weakness of the current design?**
Synchronous VM creation. A long ISO install blocks the request thread. Solution: enqueue a job and return 202; a worker processes it and updates `vm_jobs.status`.

**90. How would you add multi-tenancy properly?**
Introduce an `organizations` table, foreign-key `users` and `vm_jobs` to it, scope every query by `org_id`, and tag Proxmox VMs with an `org-` prefix or use Proxmox pools to isolate resources.

**91. How would you implement role-based access control beyond user/admin?**
Add a `roles` table and a `permissions` table linking actions to roles, then a single `has_permission(user, action)` check used in dependencies. Simpler is to keep a small enum and grow only when needed.

**92. How would you support live migration between Proxmox nodes?**
Use the existing Proxmox `migrate` API endpoint, expose it via `PATCH /vms/{id}` with `action=migrate`, and respect cluster constraints (shared storage required).

**93. What about high availability?**
Run Proxmox itself in cluster mode with HA groups. The backend can be deployed in two AZs behind a load balancer with a replicated Postgres (Patroni or managed RDS-equivalent).

**94. How would you add billing or chargeback?**
A periodic job summarizes VM uptime × CPU × RAM into a `usage_records` table, multiplied by a per-org price list. No real-time impact on the request path.

**95. How do you protect against a runaway user creating thousands of VMs?**
Hard limit via `daily_quota` per user (Sprint 1). Hard cluster-wide caps via Proxmox pools (planned). Rate limit on `/vms/` endpoint via a sliding-window counter (planned).

**96. How would you add observability?**
Structured JSON logs to Loki, Prometheus metrics from FastAPI middleware (request count, latency histograms), and Grafana dashboards. Distributed tracing via OpenTelemetry on the request → DB → Proxmox path.

**97. Why didn't you use Kubernetes?**
For the current scale (one backend, one DB, one Proxmox cluster) Kubernetes adds operational overhead without benefit. Compose covers it. We would migrate when we need autoscaling or multi-region.

**98. What is the difference between containers and VMs, and why use both?**
Containers (Docker) share the host kernel — lightweight, fast to start, ideal for stateless services like our backend. VMs (Proxmox/KVM) virtualize hardware — full kernel isolation, ideal for the user workloads we provision. We use containers for our app, VMs for what users build on top.

**99. What did you personally learn from this project?**
Designing a clean API contract first, the value of writing the `db/database.py` helpers as a single source of truth, why audit logs must never crash the main request, and how a thin abstraction over a complex external system (Proxmox) keeps the rest of the codebase sane.

**100. If you had two more weeks, what would you build?**
(1) Async job worker with status push, (2) Alembic migrations, (3) refresh tokens + token revocation, (4) basic billing/usage reporting, (5) end-to-end Playwright tests in CI. In that order — async jobs unblock everything else.

---

*Tip for the viva:* For each answer, be ready to point to the concrete file. The examiner will trust you more if you say "that's in `backend/app/auth.py`, the `get_current_user` function" than if you only describe it abstractly.
