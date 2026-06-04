# Config System & First-Run Setup Wizard

> Iteration 6 Phase 2 (Kanban #53–#57). Moves operational config out of `.env`
> into a DB-backed, UI-editable, encrypted-at-rest store with a first-run wizard.
> Phase 1 was [[12-state-reconciliation]].

## The problem

Operational config (Proxmox connector, OpenRouter/LLM key, Guacamole admin,
VM credentials, golden-image VMIDs) lived in the committed-template `.env` and
was read via `os.getenv` scattered across ~10 files. There was no way to
configure a deployment from the UI — every change meant editing `.env` and
restarting. Iteration 6 wants a first-run wizard instead.

## The hard constraint (what can't move)

A setting can't live inside the database it unlocks. So a **minimal bootstrap
stays in docker-compose / `.env`**: `DB_*`, `CELERY_BROKER_URL` (Redis),
`JWT_SECRET_KEY`, `SETTINGS_ENCRYPTION_KEY`, and the Guacamole MySQL infra
passwords. Everything else moves to the DB and the wizard. (This matches Kanban
#56 "DB credentials management in docker-compose".)

## Architecture

```
UI Setup Wizard / Admin→Settings
        │  PATCH /admin/settings/{key}  |  POST /setup
        ▼
system_settings table  (value_type: string|integer|boolean|json|secret)
  • secrets Fernet-encrypted at rest (enc:: prefix), masked in API responses
        ▲
        │ get_config(key)  (DB-first → env fallback → default, 30s cache)
        │
backend call sites (ProxmoxClient, llm_agent, guacamole_client, models/vm, …)
```

### Single source of truth: `db/config_registry.py`
`CONFIG_REGISTRY` lists every movable key as `ConfigKey(key, env, value_type,
default, description)`. Both layers use it: `init_db()` seeds the keys; the
config resolver maps a name (`proxmox.host` *or* `PROXMOX_HOST`) and knows the
env fallback. Add a new config value in ONE place here.

### Resolver: `backend/app/config.py`
`get_config(name, default)` (+ `get_config_str/int/bool`): reads
`database.get_setting()` first (secrets returned decrypted), falls back to
`os.getenv`, then `default`. 30s TTL cache. `invalidate_cache()` clears it and
bumps a **generation counter**; `config_generation()` lets long-lived clients
detect a change and rebuild.

### Encryption: `backend/app/services/secret_crypto.py`
Fernet using `SETTINGS_ENCRYPTION_KEY` (env). `encrypt()/decrypt()` with an
`enc::` prefix so legacy plaintext passes through during migration. Built lazily
so the app still boots without the key (only reading/writing a *non-empty*
secret needs it). **If the key changes, saved secrets become undecryptable.**

### Storage layer: `db/database.py`
- `system_settings` CHECK widened to include `'secret'` (+ ALTER migration).
- `get_setting()` decrypts secrets; `set_setting()` encrypts them (looks up the
  declared type first); `_present_setting_row()` masks secrets (`value=""`,
  `typed_value=null`, adds `is_secret` + `is_set`) for `list_settings()` and the
  `set_setting()` return. Secret plaintext is never returned or audit-logged.

### Picking up changes without a restart
`vm_routes`, `template_routes`, and the Celery tasks use a module-level
`proxmox` **proxy** (`app.proxmox_client._ProxmoxClientProxy`) that delegates to
`get_proxmox_client()`, which rebuilds the client when the config generation
changes. `llm_agent` builds its OpenAI client lazily via a `client` property
keyed on the generation. Guacamole helpers read config per call. (Celery is a
separate process: the worker reads DB config at first task; a later change needs
a worker restart — it already requires restarts for code changes.)

## First-run flow
1. First registered user is auto-promoted to admin (existing, Kanban #52).
2. `ProtectedRoute` queries `GET /setup/status`; if an admin and
   `completed=false`, it redirects to `/setup`.
3. `SetupWizardPage` collects Proxmox + LLM (+ optional VM/Guacamole) and calls
   `POST /setup`, which writes the settings, optionally **live-tests the Proxmox
   connection** (`list_vms()`), and sets `setup.completed=true` once the required
   connector fields are present.
4. Existing config can be edited any time in Admin → Settings (secrets show as
   `•••• (configured)` and accept a new value or blank-to-clear).

## Files
| Concern | File |
|---|---|
| Key registry | `db/config_registry.py` |
| Resolver | `backend/app/config.py` |
| Encryption | `backend/app/services/secret_crypto.py` |
| Settings storage | `db/database.py` (`get/set/list_settings`, `_present_setting_row`, seed) |
| Setup endpoints | `backend/app/routes/setup_routes.py` (`GET /setup/status`, `POST /setup`) |
| Settings API model | `backend/app/routes/admin_routes.py` (`SettingResponse` + masking + cache invalidate) |
| Client proxy / rebuild | `backend/app/proxmox_client.py` (`get_proxmox_client`, `_ProxmoxClientProxy`) |
| Frontend wizard | `frontend/src/pages/SetupWizardPage.tsx`, `api/setup.ts`, `hooks/use-setup.ts`, `components/shared/ProtectedRoute.tsx` |
| Bootstrap | `.env` / `.env.example` / `docker-compose.yml` (`SETTINGS_ENCRYPTION_KEY`) |

## Related
- [[02-docker-infrastructure]] (env split: bootstrap vs wizard)
- [[12-state-reconciliation]] (Phase 1)
- [[10-rag-knowledge-base]] (LLM/OpenAI config now via this resolver)
- [[06-guacamole-integration]] (admin login now via this resolver)
