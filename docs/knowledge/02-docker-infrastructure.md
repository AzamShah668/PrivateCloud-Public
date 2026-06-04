# Docker Infrastructure

## Services (docker-compose.yml)
| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| postgres | proxmox_postgres | 5432 | App database (PostgreSQL 16) |
| redis | proxmox_redis | 6379 | Celery broker + result backend |
| backend | proxmox_backend | 8000 | FastAPI application |
| celery-worker | proxmox_celery_worker | - | Async VM provisioning |
| guacd | proxmox_guacd | - | Guacamole proxy daemon |
| mysql-guacamole | proxmox_mysql_guacamole | - | Guacamole auth DB |
| guacamole | proxmox_guacamole | 9080 | HTML5 RDP client |
| frontend | proxmox_frontend | 3000 | React UI (nginx) |

## Environment model (Iteration 6 — see [[13-config-and-setup-wizard]])
As of the setup wizard, env is split into **bootstrap** (must exist before the
app can reach its DB) vs **operational** (configured in the UI, stored in the DB).

**Bootstrap (stays in `.env` / docker-compose):**
- DB_HOST=postgres, DB_PORT=5432, DB_NAME/USER/PASSWORD
- CELERY_BROKER_URL=redis://redis:6379/0
- JWT_SECRET_KEY
- `SETTINGS_ENCRYPTION_KEY` — Fernet key encrypting secret settings at rest.
  Required by backend AND celery-worker. Do NOT change once secrets are saved.
- GUACAMOLE_API_URL=http://guacamole:8080/guacamole (internal Docker network)
- GUACAMOLE_MYSQL_* (consumed by docker-compose for the mysql-guacamole service)

**Operational (configured via the Setup Wizard → `system_settings`, env is fallback):**
- PROXMOX_* (host/node/verify_ssl/token_id/token_secret/user/password, golden VMIDs)
- OPENAI_* / llm.* (API key, base_url, model)
- VM_DEFAULT_* / VM_WINDOWS_* (guest credentials)
- GUACAMOLE_PUBLIC_URL, GUACAMOLE_ADMIN_USER/PASSWORD
- CLONE_LEASE_HOURS

Backend reads all of these through `app.config.get_config()` (DB-first, env
fallback). The backend `environment:` block in docker-compose still sets the
GUACAMOLE_* and CHROMA_PATH values as fallback defaults.

## Build & Deploy
- Full rebuild: `docker compose up --build -d`
- Frontend only: `docker compose up --build -d frontend`
- Hot reload: backend mounts ./backend/app as volume, uses --reload flag
- Frontend: NO hot reload in prod, requires full Docker rebuild for changes

## Common Build Errors
- TypeScript errors in frontend block the entire build (tsc runs before vite)
- ActionBar.tsx has been a recurring source of syntax errors during hot-patching
- Always verify build passes before assuming deployment worked

## Related
- [[03-celery-provisioning]] - Worker configuration
- [[01-network-topology]] - Port exposure and proxying
