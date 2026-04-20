# Database Schema Reference

PostgreSQL 16 — see `db/database.py` for full init_db() DDL.

## Tables

### users
User accounts with role-based access control and soft-delete support.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | SERIAL | PRIMARY KEY | Auto-increment |
| username | TEXT | UNIQUE NOT NULL | Login handle |
| password_hash | TEXT | NOT NULL | bcrypt(password) |
| role | TEXT | DEFAULT 'user' | 'user' \| 'admin' |
| daily_quota | INTEGER | DEFAULT 3 | Max VMs per day (UTC) |
| created_at | TIMESTAMPTZ | NOT NULL | Account creation time |
| deleted_at | TIMESTAMPTZ | NULL | Soft-delete timestamp (I3) |
| status | VARCHAR(20) | DEFAULT 'active' | 'active' \| 'suspended' \| 'deleted' (I3) |

**Indices:**
- idx_users_active: (id) WHERE status = 'active'

**Check Constraints:**
- users_status_check: status IN ('active', 'suspended', 'deleted')

**Use:**
- User authentication (username lookup, password validation)
- Admin user management (role/quota changes)
- Daily quota enforcement (count VMs created today, WHERE user_id = :id AND created_at::date = TODAY)

---

### vm_jobs
VM provisioning requests — one row per creation, tracked through full lifecycle.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | SERIAL | PRIMARY KEY | Job ID (returned immediately on create) |
| user_id | INTEGER | FK → users.id | Owner of this VM |
| vmid | INTEGER | NOT NULL | Proxmox VMID (assigned after clone) |
| vm_name | TEXT | NOT NULL | User-chosen display name |
| os_choice | TEXT | NOT NULL | Template name (ubuntu-22, rocky-9, etc.) |
| request_payload | JSONB | NOT NULL | Original POST /vms request body (audit) |
| status | TEXT | NOT NULL | 'queued' \| 'running' \| 'done' \| 'failed' |
| proxmox_response | JSONB | NULL | Raw Proxmox clone/start response (debugging) |
| error_message | TEXT | NULL | Populated only if status = 'failed' |
| created_at | TIMESTAMPTZ | NOT NULL | Job creation time |
| updated_at | TIMESTAMPTZ | NOT NULL | Last update (status change, credential fill) |
| vm_ip | TEXT | NULL | Filled once QEMU guest agent reports IP |
| vm_username | TEXT | NULL | Initial OS user credential (root, ubuntu, etc.) |
| vm_password | TEXT | NULL | Initial OS password credential |

**Indices:**
- idx_vm_jobs_user_created: (user_id, created_at) — speeds daily quota count + user's recent VMs

**Use:**
- VM lifecycle tracking (creation → provisioning → ready → deleted)
- Credential storage (IP, username, password returned to user once ready)
- Audit trail (request payload + responses stored for debugging)
- Admin dashboard (list all VMs across all users, with owner joined)

**Deletion Pattern:**
- Soft-delete: update status='deleted', don't remove row (audit preservation)
- Only admin DELETE /vms/{id} endpoint performs actual deletion

---

### audit_logs
Immutable append-only log of all significant system actions.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| id | SERIAL | PRIMARY KEY | Log entry ID |
| user_id | INTEGER | FK → users.id | Actor (who performed the action) |
| action | TEXT | NOT NULL | Human-readable action description |
| action_type | VARCHAR(40) | NOT NULL | Machine-readable category (I3) |
| target_type | TEXT | NOT NULL | Kind of object ('user', 'vm_job', 'setting') |
| target_id | TEXT | NULL | Identifier of affected object (user_id, vmid, setting key) |
| target_user_id | INTEGER | FK → users.id NULL | Affected user (if action targets a user) (I3) |
| details | JSONB | NOT NULL | Extra context (old/new values, reason, IP, etc.) |
| created_at | TIMESTAMPTZ | NOT NULL | Timestamp of action |

**Indices:**
- idx_audit_action_type: (action_type, created_at DESC) — fast filtering by action category
- idx_audit_target_user: (target_user_id, created_at DESC) WHERE target_user_id IS NOT NULL — fast "all actions ON user Y" queries

**Check Constraints:**
- audit_action_type_check: action_type IN (
  'user.create', 'user.role_change', 'user.quota_change',
  'user.suspend', 'user.delete', 'user.reactivate',
  'vm.create', 'vm.delete', 'vm.status_change',
  'settings.change', 'admin.login', 'system.unknown'
)

**Query Patterns:**
- All actions by admin X: `SELECT * FROM audit_logs WHERE user_id = :admin_id ORDER BY created_at DESC`
- All actions ON user Y: `SELECT * FROM audit_logs WHERE target_user_id = :user_id ORDER BY created_at DESC`
- Filter by action type: `SELECT * FROM audit_logs WHERE action_type = 'vm.create' ORDER BY created_at DESC`
- Join actor + subject names: `JOIN users AS actor ON audit.user_id = actor.id LEFT JOIN users AS subject ON audit.target_user_id = subject.id`

**Use:**
- Compliance / audit trail (non-repudiable record of who did what when)
- Admin dashboard audit page (filter by action type, show actor → action → target)
- Debugging (request payloads, error messages, proxmox responses stored in details)

---

### system_settings
Key-value store for admin-configurable platform settings (I3).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| key | VARCHAR(100) | PRIMARY KEY | Namespaced key (e.g., 'quota.default_daily', 'node.max_vms') |
| value | TEXT | NOT NULL | Always stored as text; cast via value_type |
| value_type | VARCHAR(10) | DEFAULT 'string' | 'string' \| 'integer' \| 'boolean' \| 'json' |
| description | TEXT | NULL | Human-readable label for admin UI |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | Last modification time |
| updated_by | INTEGER | FK → users.id NULL | Admin who last changed this setting |

**Check Constraints:**
- system_settings_type_check: value_type IN ('string', 'integer', 'boolean', 'json')

**Seed Data (on init_db):**
| key | value | type | description |
|-----|-------|------|-------------|
| quota.default_daily | 3 | integer | Default daily VM quota for new users |
| node.max_vms | 50 | integer | Maximum VMs per Proxmox node |
| platform.maintenance | false | boolean | If true, non-admin logins blocked (maintenance mode) |
| audit.retention_days | 90 | integer | Days to retain audit log entries |

**Use:**
- Admin Settings page: read all settings, display in table, allow updates
- Platform config without code redeploy (e.g., adjust quota limits, toggle maintenance mode)
- Frontend can query `/admin/settings` and cache/apply rules locally

**Casting:**
```python
# Backend helper (not yet implemented, but pattern):
def get_setting(key: str) -> str | int | bool | dict:
    row = cur.execute("SELECT value, value_type FROM system_settings WHERE key = %s", (key,))
    value, value_type = row
    if value_type == 'integer':
        return int(value)
    elif value_type == 'boolean':
        return value.lower() == 'true'
    elif value_type == 'json':
        return json.loads(value)
    return value  # string
```

---

## Relationships

```
users ──────────┬─── (1:N) ──→ vm_jobs
                │
                ├─── (1:N) ──→ audit_logs (user_id = actor)
                │
                └─── (1:N) ──→ audit_logs (target_user_id = affected user)
                │
                └─── (1:N) ──→ system_settings (updated_by)
```

---

## Migration Pattern

All schema changes use idempotent PostgreSQL patterns:

```python
# Safe to run multiple times (init_db is called on every startup)

# Add column (if not exists)
ALTER TABLE users
  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;

# Add constraint (wrapped in DO block since ADD CONSTRAINT IF NOT EXISTS doesn't exist)
DO $$ BEGIN
    ALTER TABLE users
        ADD CONSTRAINT users_status_check
        CHECK (status IN ('active', 'suspended', 'deleted'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

# Create index (if not exists)
CREATE INDEX IF NOT EXISTS idx_users_active
  ON users (id) WHERE status = 'active';

# Seed data (insert if not exists)
INSERT INTO system_settings (key, value, value_type, description) VALUES
  ('quota.default_daily', '3', 'integer', 'Default daily VM quota')
ON CONFLICT (key) DO NOTHING;
```

This ensures:
- Fresh databases get the full schema
- Existing databases can be upgraded safely
- No manual migration scripts needed (schema is code-driven)
- Multiple Kubernetes replicas can boot simultaneously without race conditions
