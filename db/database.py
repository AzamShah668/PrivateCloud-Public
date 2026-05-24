import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras          # provides RealDictCursor
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

load_dotenv()  # reads .env if present; environment variables always win

# Build the DSN from individual env vars so each piece can be overridden
# independently (e.g. injecting secrets via Docker / Kubernetes).
_DSN = (
    f"host={os.environ.get('DB_HOST', 'localhost')} "
    f"port={os.environ.get('DB_PORT', '5432')} "
    f"dbname={os.environ.get('DB_NAME', 'proxmox_app')} "
    f"user={os.environ.get('DB_USER', 'postgres')} "
    f"password={os.environ.get('DB_PASSWORD', '')} "
    f"sslmode={os.environ.get('DB_SSLMODE', 'prefer')}"
)

# Pool size can also be tuned via env vars
_POOL_MIN = int(os.environ.get("DB_POOL_MIN", 2))
_POOL_MAX = int(os.environ.get("DB_POOL_MAX", 10))

logger = logging.getLogger(__name__)

# Module-level pool — created once when this module is first imported.
# Call init_db() early in your app startup to both create the pool
# and ensure the schema exists.
_pool: ThreadedConnectionPool | None = None


def _get_pool() -> ThreadedConnectionPool:
    """Return the module-level connection pool, raising if init_db() was not called."""
    if _pool is None:
        raise RuntimeError("Database pool is not initialised — call init_db() first.")
    return _pool


@contextmanager
def _conn():
    """
    Context manager that borrows a connection from the pool, yields it,
    and always returns it afterwards (even on error).

    Usage:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(...)
            conn.commit()
    """
    pool = _get_pool()
    conn = pool.getconn()
    try:
        yield conn
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def _dict_cursor(conn):
    """Return a cursor whose rows come back as plain dicts (like sqlite3.Row)."""
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def utc_now_iso() -> str:
    """Current UTC time as an ISO-8601 string — stored in every timestamp column."""
    return datetime.now(tz=timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Schema initialisation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Create the connection pool and apply the schema (CREATE TABLE IF NOT EXISTS).

    Call this **once** at application startup before any other DB function.
    It is safe to call multiple times — existing tables are never dropped.
    """
    global _pool
    _pool = ThreadedConnectionPool(_POOL_MIN, _POOL_MAX, dsn=_DSN)
    logger.info("PostgreSQL connection pool created (min=%d, max=%d)", _POOL_MIN, _POOL_MAX)

    with _conn() as conn:
        with conn.cursor() as cur:

            # ----------------------------------------------------------
            # users
            # Stores app accounts.  role is either 'user' or 'admin'.
            # daily_quota limits how many VMs a user can create per day.
            # ----------------------------------------------------------
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id            SERIAL PRIMARY KEY,
                    username      TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role          TEXT NOT NULL DEFAULT 'user',
                    daily_quota   INTEGER NOT NULL DEFAULT 3,
                    created_at    TIMESTAMPTZ NOT NULL
                )
                """
            )

            # ----------------------------------------------------------
            # vm_jobs
            # Every VM creation request is tracked here so we can report
            # status back to the user and audit what happened.
            # ----------------------------------------------------------
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS vm_jobs (
                    id                SERIAL PRIMARY KEY,
                    user_id           INTEGER NOT NULL REFERENCES users(id),
                    vmid              INTEGER NOT NULL,
                    vm_name           TEXT NOT NULL,
                    os_choice         TEXT NOT NULL,
                    request_payload   JSONB NOT NULL,
                    status            TEXT NOT NULL,          -- queued | running | done | failed
                    proxmox_response  JSONB,
                    error_message     TEXT,
                    created_at        TIMESTAMPTZ NOT NULL,
                    updated_at        TIMESTAMPTZ NOT NULL
                )
                """
            )

            # Index speeds up the daily-quota count query run on every job creation.
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_vm_jobs_user_created
                ON vm_jobs (user_id, created_at)
                """
            )

            # ----------------------------------------------------------
            # vm_jobs credential columns (added after initial schema)
            # ALTER TABLE … ADD COLUMN IF NOT EXISTS is idempotent —
            # safe to run on an already-initialised database.
            # ----------------------------------------------------------
            for column_def in (
                "vm_ip       TEXT",
                "vm_username TEXT",
                "vm_password TEXT",
                "expires_at  TIMESTAMPTZ",   # i4: 2-hour auto-expire timer
            ):
                col_name = column_def.split()[0]
                cur.execute(
                    f"ALTER TABLE vm_jobs ADD COLUMN IF NOT EXISTS {column_def}"
                )
                logger.debug("Ensured column vm_jobs.%s exists.", col_name)

            # ----------------------------------------------------------
            # audit_logs
            # Immutable record of every significant action in the system.
            # ----------------------------------------------------------
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id          SERIAL PRIMARY KEY,
                    user_id     INTEGER NOT NULL REFERENCES users(id),
                    action      TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id   TEXT,
                    details     JSONB NOT NULL,
                    created_at  TIMESTAMPTZ NOT NULL
                )
                """
            )

            # ----------------------------------------------------------
            # I3 admin-portal schema extensions
            # ----------------------------------------------------------
            # Four non-breaking additions (see Proxmox_Admin_DB_Design.docx):
            #   1. users.deleted_at + users.status  (soft-delete)
            #   2. audit_logs.action_type           (controlled vocabulary)
            #   3. audit_logs.target_user_id        (admin-action attribution)
            #   4. system_settings                  (platform-wide key/value)
            #
            # PostgreSQL supports ADD COLUMN IF NOT EXISTS but NOT
            # ADD CONSTRAINT IF NOT EXISTS — CHECK constraints are wrapped
            # in DO $$ ... EXCEPTION WHEN duplicate_object blocks so the
            # whole block stays idempotent.
            # ----------------------------------------------------------

            # --- users: soft-delete ---
            cur.execute(
                """
                ALTER TABLE users
                  ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL,
                  ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'active'
                """
            )
            cur.execute(
                """
                DO $$ BEGIN
                    ALTER TABLE users
                        ADD CONSTRAINT users_status_check
                        CHECK (status IN ('active', 'suspended', 'deleted'));
                EXCEPTION WHEN duplicate_object THEN NULL;
                END $$;
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_users_active
                  ON users (id) WHERE status = 'active'
                """
            )

            # --- audit_logs: action taxonomy ---
            cur.execute(
                """
                ALTER TABLE audit_logs
                  ADD COLUMN IF NOT EXISTS action_type VARCHAR(40)
                        NOT NULL DEFAULT 'system.unknown'
                """
            )
            cur.execute(
                """
                DO $$ BEGIN
                    ALTER TABLE audit_logs
                        ADD CONSTRAINT audit_action_type_check
                        CHECK (action_type IN (
                            'user.create','user.role_change','user.quota_change',
                            'user.suspend','user.delete','user.reactivate',
                            'vm.create','vm.delete','vm.status_change',
                            'settings.change','admin.login','system.unknown'
                        ));
                EXCEPTION WHEN duplicate_object THEN NULL;
                END $$;
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_action_type
                  ON audit_logs (action_type, created_at DESC)
                """
            )

            # --- audit_logs: target user attribution ---
            cur.execute(
                """
                ALTER TABLE audit_logs
                  ADD COLUMN IF NOT EXISTS target_user_id INTEGER
                        REFERENCES users(id) ON DELETE SET NULL
                """
            )
            cur.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_audit_target_user
                  ON audit_logs (target_user_id, created_at DESC)
                  WHERE target_user_id IS NOT NULL
                """
            )

            # --- system_settings (NEW) ---
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS system_settings (
                    key         VARCHAR(100) PRIMARY KEY,
                    value       TEXT         NOT NULL,
                    value_type  VARCHAR(10)  NOT NULL DEFAULT 'string',
                    description TEXT,
                    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
                    updated_by  INTEGER      REFERENCES users(id) ON DELETE SET NULL,
                    CONSTRAINT system_settings_type_check
                        CHECK (value_type IN ('string','integer','boolean','json'))
                )
                """
            )
            cur.execute(
                """
                INSERT INTO system_settings (key, value, value_type, description) VALUES
                    ('quota.default_daily',  '3',     'integer', 'Default daily VM quota for new users'),
                    ('node.max_vms',         '50',    'integer', 'Maximum VMs allowed per Proxmox node'),
                    ('platform.maintenance', 'false', 'boolean', 'If true, non-admin logins are blocked'),
                    ('audit.retention_days', '90',    'integer', 'Days to retain audit log entries')
                ON CONFLICT (key) DO NOTHING
                """
            )

        conn.commit()
    logger.info("Database schema verified / created successfully.")


# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def create_user(
    username: str,
    password_hash: str,
    role: str = "user",
    daily_quota: int = 3,
) -> int:
    """
    Insert a new user row and return its generated id.

    Raises psycopg2.errors.UniqueViolation if the username already exists —
    callers should catch this and return a 409 HTTP response.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                INSERT INTO users (username, password_hash, role, daily_quota, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (username, password_hash, role, daily_quota, utc_now_iso()),
            )
            row = cur.fetchone()
        conn.commit()
    return int(row["id"])


def get_user_by_username(username: str) -> dict | None:
    """Return a user dict or None if the username does not exist."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            return cur.fetchone()


def get_user_by_id(user_id: int) -> dict | None:
    """Return a user dict or None if the id does not exist."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return cur.fetchone()


def update_user_credentials(
    user_id: int,
    *,
    username: str | None = None,
    password_hash: str | None = None,
    daily_quota: int | None = None,
) -> None:
    """
    Update one or more fields on a user row.

    Only the keyword arguments that are not None are included in the SET clause,
    so the caller can change just the username, just the password, or both at once
    without touching other columns.

    Raises:
        psycopg2.errors.UniqueViolation  — if the new username is already taken.
        ValueError                       — if no fields were provided (nothing to update).
    """
    # Build the SET clause dynamically from whichever fields were supplied
    updates: list[str]  = []
    params:  list       = []

    if username is not None:
        updates.append("username = %s")
        params.append(username)

    if password_hash is not None:
        updates.append("password_hash = %s")
        params.append(password_hash)

    if daily_quota is not None:
        updates.append("daily_quota = %s")
        params.append(daily_quota)

    if not updates:
        raise ValueError("update_user_credentials() called with nothing to update.")

    params.append(user_id)   # for the WHERE clause

    sql = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"

    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
        conn.commit()

    logger.info(
        "User id=%d updated: fields=%s",
        user_id,
        [u.split(" =")[0] for u in updates],
    )


# ---------------------------------------------------------------------------
# VM job helpers
# ---------------------------------------------------------------------------

def count_user_jobs_today(user_id: int) -> int:
    """
    Count how many VM jobs the user has created today (UTC date).
    Used to enforce the daily_quota limit before accepting a new request.
    """
    today = datetime.now(tz=timezone.utc).date().isoformat()  # "YYYY-MM-DD"
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS c
                FROM vm_jobs
                WHERE user_id = %s
                  AND created_at::date = %s::date
                """,
                (user_id, today),
            )
            row = cur.fetchone()
    return int(row["c"]) if row else 0


def create_vm_job(
    user_id: int,
    vmid: int,
    vm_name: str,
    os_choice: str,
    request_payload: dict,
    expiry_hours: int = 2,
) -> int:
    """
    Insert a new VM job in 'queued' status and return its generated id.

    request_payload is stored as JSONB so it can be queried efficiently
    from PostgreSQL if needed later.

    expires_at is set to (now + expiry_hours) so a background task can
    auto-stop the VM after its lease elapses. Default 2 hours per i4 spec.
    """
    from datetime import timedelta
    now_dt = datetime.now(tz=timezone.utc)
    now_iso = now_dt.isoformat()
    expires_iso = (now_dt + timedelta(hours=expiry_hours)).isoformat()
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                INSERT INTO vm_jobs
                    (user_id, vmid, vm_name, os_choice, request_payload,
                     status, created_at, updated_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, 'queued', %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    vmid,
                    vm_name,
                    os_choice,
                    json.dumps(request_payload),
                    now_iso,
                    now_iso,
                    expires_iso,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return int(row["id"])


def extend_vm_expiry(job_id: int, hours: int = 2) -> str | None:
    """
    Push a VM's expires_at forward by `hours` hours from NOW (not from current
    expiry — prevents stacking large extensions). Returns the new ISO timestamp
    or None if the job does not exist.
    """
    from datetime import timedelta
    new_expires = (datetime.now(tz=timezone.utc) + timedelta(hours=hours)).isoformat()
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                UPDATE vm_jobs
                SET expires_at = %s, updated_at = %s
                WHERE id = %s AND status = 'done'
                RETURNING expires_at
                """,
                (new_expires, utc_now_iso(), job_id),
            )
            row = cur.fetchone()
        conn.commit()
    return row["expires_at"].isoformat() if row else None


def list_expired_vm_jobs() -> list[dict]:
    """
    Return all 'done' VM jobs whose expires_at is in the past.
    Used by the background scheduler to auto-stop expired VMs.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT id, vmid, vm_name, user_id, request_payload, expires_at
                FROM vm_jobs
                WHERE status = 'done'
                  AND expires_at IS NOT NULL
                  AND expires_at <= NOW()
                """
            )
            return cur.fetchall()


def update_vm_job(
    job_id: int,
    status: str,
    proxmox_response: dict | None = None,
    error_message: str | None = None,
    vm_ip: str | None = None,
    vm_username: str | None = None,
    vm_password: str | None = None,
) -> None:
    """
    Update the status (and optional response/error/credentials) of an existing VM job.

    Typical status flow:  queued → running → done
                                           → failed

    vm_ip / vm_username / vm_password are populated once the VM boots and the
    guest agent reports its IP address.  The SQL uses COALESCE so that passing
    None for a credential field leaves the existing DB value untouched —
    callers that don't have credential info won't accidentally overwrite
    previously stored values.
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE vm_jobs
                SET status           = %s,
                    proxmox_response = %s,
                    error_message    = %s,
                    vm_ip            = COALESCE(%s, vm_ip),
                    vm_username      = COALESCE(%s, vm_username),
                    vm_password      = COALESCE(%s, vm_password),
                    updated_at       = %s
                WHERE id = %s
                """,
                (
                    status,
                    json.dumps(proxmox_response) if proxmox_response is not None else None,
                    error_message,
                    vm_ip,
                    vm_username,
                    vm_password,
                    utc_now_iso(),
                    job_id,
                ),
            )
        conn.commit()


def get_vm_job(job_id: int) -> dict | None:
    """Return a VM job dict by its id, or None if it does not exist."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM vm_jobs WHERE id = %s", (job_id,))
            return cur.fetchone()


def list_user_vm_jobs(user_id: int, limit: int = 50) -> list[dict]:
    """Return the most recent VM jobs for a given user (newest first)."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                "SELECT * FROM vm_jobs WHERE user_id = %s ORDER BY id DESC LIMIT %s",
                (user_id, limit),
            )
            return cur.fetchall()


# ---------------------------------------------------------------------------
# Audit log helpers
# ---------------------------------------------------------------------------

def add_audit_log(
    user_id: int,
    action: str,
    target_type: str,
    target_id: str,
    details: dict,
) -> None:
    """
    Append an immutable audit record.

    action      — what happened, e.g. "vm.create", "user.login"
    target_type — the kind of object, e.g. "vm_job", "user"
    target_id   — the string PK/identifier of that object
    details     — arbitrary dict with extra context (stored as JSONB)
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_logs
                    (user_id, action, target_type, target_id, details, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, action, target_type, target_id, json.dumps(details), utc_now_iso()),
            )
        conn.commit()


def list_audit_logs(limit: int = 100) -> list[dict]:
    """Return the most recent audit log entries (newest first). Admin use only."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                "SELECT * FROM audit_logs ORDER BY id DESC LIMIT %s",
                (limit,),
            )
            return cur.fetchall()


# ---------------------------------------------------------------------------
# Admin helpers
# ---------------------------------------------------------------------------

def list_all_users(limit: int = 200) -> list[dict]:
    """Return all users (newest first), excluding password_hash. Admin use only."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT id, username, role, daily_quota, created_at
                FROM users
                ORDER BY id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def list_all_vm_jobs(limit: int = 200) -> list[dict]:
    """Return all VM jobs across all users (newest first). Admin use only."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT vj.*, u.username AS owner_username
                FROM vm_jobs vj
                JOIN users u ON u.id = vj.user_id
                ORDER BY vj.id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def get_admin_stats() -> dict:
    """
    Return aggregate statistics for the admin dashboard.
    All counts come from existing tables — no new schema required.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM users)                               AS total_users,
                    (SELECT COUNT(*) FROM users WHERE role = 'admin')          AS total_admins,
                    (SELECT COUNT(*) FROM vm_jobs)                              AS total_vms,
                    (SELECT COUNT(*) FROM vm_jobs WHERE status = 'done')        AS active_vms,
                    (SELECT COUNT(*) FROM vm_jobs WHERE status = 'failed')      AS failed_vms,
                    (SELECT COUNT(*) FROM vm_jobs WHERE status = 'queued')      AS queued_vms,
                    (SELECT COUNT(*) FROM vm_jobs WHERE status = 'deleted')     AS deleted_vms,
                    (SELECT COUNT(*) FROM audit_logs)                           AS total_audit_entries,
                    (SELECT COUNT(*)
                     FROM vm_jobs
                     WHERE created_at::date = CURRENT_DATE)                    AS vms_created_today
                """
            )
            return cur.fetchone()


def update_user_role(user_id: int, role: str) -> dict | None:
    """Update a user's role and return the updated user (without password_hash)."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                UPDATE users SET role = %s WHERE id = %s
                RETURNING id, username, role, daily_quota, created_at
                """,
                (role, user_id),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def update_user_quota(user_id: int, daily_quota: int) -> dict | None:
    """Update a user's daily VM quota and return the updated user."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                UPDATE users SET daily_quota = %s WHERE id = %s
                RETURNING id, username, role, daily_quota, created_at
                """,
                (daily_quota, user_id),
            )
            row = cur.fetchone()
        conn.commit()
    return row


# ---------------------------------------------------------------------------
# I3: User soft-delete helpers
# ---------------------------------------------------------------------------

def suspend_user(user_id: int) -> dict | None:
    """
    Set a user's status to 'suspended'. Does NOT populate deleted_at —
    suspension is recoverable, deletion is a separate action.

    Returns the updated user row (without password_hash) or None if the
    user does not exist.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                UPDATE users
                SET status = 'suspended'
                WHERE id = %s
                RETURNING id, username, role, daily_quota, created_at,
                          deleted_at, status
                """,
                (user_id,),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def soft_delete_user(user_id: int) -> dict | None:
    """
    Soft-delete a user: status='deleted', deleted_at=NOW().
    Preserves all historical data (vm_jobs, audit_logs) through FK.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                UPDATE users
                SET status = 'deleted',
                    deleted_at = %s
                WHERE id = %s
                RETURNING id, username, role, daily_quota, created_at,
                          deleted_at, status
                """,
                (utc_now_iso(), user_id),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def reactivate_user(user_id: int) -> dict | None:
    """
    Reverse a suspend or soft-delete: status='active', deleted_at=NULL.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                UPDATE users
                SET status = 'active',
                    deleted_at = NULL
                WHERE id = %s
                RETURNING id, username, role, daily_quota, created_at,
                          deleted_at, status
                """,
                (user_id,),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def list_all_users_extended(
    include_deleted: bool = False,
    limit: int = 200,
) -> list[dict]:
    """
    Admin-facing user list with the I3 soft-delete columns.
    By default excludes soft-deleted rows (status='deleted').
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            if include_deleted:
                cur.execute(
                    """
                    SELECT id, username, role, daily_quota, created_at,
                           deleted_at, status
                    FROM users
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            else:
                cur.execute(
                    """
                    SELECT id, username, role, daily_quota, created_at,
                           deleted_at, status
                    FROM users
                    WHERE status != 'deleted'
                    ORDER BY id DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            return cur.fetchall()


# ---------------------------------------------------------------------------
# I3: Audit log extended helper (with action_type + target_user_id)
# ---------------------------------------------------------------------------

# Canonical action_type values (must match CHECK constraint in init_db)
AUDIT_ACTION_TYPES = frozenset({
    "user.create",
    "user.role_change",
    "user.quota_change",
    "user.suspend",
    "user.delete",
    "user.reactivate",
    "vm.create",
    "vm.delete",
    "vm.status_change",
    "settings.change",
    "admin.login",
    "system.unknown",
})


def log_action(
    user_id: int,
    action_type: str,
    action: str,
    target_type: str,
    target_id: str,
    details: dict,
    target_user_id: int | None = None,
) -> None:
    """
    I3 replacement for add_audit_log() — records action_type (enum) and
    optional target_user_id for admin action attribution.

    Falls back to 'system.unknown' if action_type is not in the canonical
    set, so a typo doesn't break the request.
    """
    if action_type not in AUDIT_ACTION_TYPES:
        logger.warning(
            "log_action: unknown action_type=%r; falling back to 'system.unknown'",
            action_type,
        )
        action_type = "system.unknown"

    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO audit_logs
                    (user_id, action, action_type, target_type, target_id,
                     target_user_id, details, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    action,
                    action_type,
                    target_type,
                    target_id,
                    target_user_id,
                    json.dumps(details),
                    utc_now_iso(),
                ),
            )
        conn.commit()


def list_audit_logs_filtered(
    action_type: str | None = None,
    target_user_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """
    Admin audit log list with optional filters.

    - action_type: only return rows matching this enum value
    - target_user_id: only rows where this user was the subject
    - offset/limit: pagination

    Joins to users twice so the UI can render "actor → action → subject".
    """
    where: list[str] = []
    params: list = []

    if action_type is not None:
        where.append("al.action_type = %s")
        params.append(action_type)

    if target_user_id is not None:
        where.append("al.target_user_id = %s")
        params.append(target_user_id)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""
    params.extend([limit, offset])

    sql = f"""
        SELECT al.id, al.user_id, al.action, al.action_type,
               al.target_type, al.target_id, al.target_user_id,
               al.details, al.created_at,
               actor.username   AS actor_username,
               subject.username AS target_username
        FROM audit_logs al
        LEFT JOIN users actor   ON actor.id   = al.user_id
        LEFT JOIN users subject ON subject.id = al.target_user_id
        {where_sql}
        ORDER BY al.id DESC
        LIMIT %s OFFSET %s
    """

    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


# ---------------------------------------------------------------------------
# I3: System settings helpers
# ---------------------------------------------------------------------------

def _cast_setting_value(value: str, value_type: str):
    """Convert the TEXT-stored value to its declared type."""
    if value_type == "integer":
        return int(value)
    if value_type == "boolean":
        return value.lower() in ("true", "1", "yes")
    if value_type == "json":
        return json.loads(value)
    return value  # 'string' or unknown → raw text


def get_setting(key: str):
    """
    Return the cast value for a setting key, or None if the key is unknown.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                "SELECT value, value_type FROM system_settings WHERE key = %s",
                (key,),
            )
            row = cur.fetchone()
    if row is None:
        return None
    return _cast_setting_value(row["value"], row["value_type"])


def list_settings() -> list[dict]:
    """
    Return every settings row, with the cast value pre-computed in
    a 'typed_value' field so the frontend doesn't need to cast.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT s.key, s.value, s.value_type, s.description,
                       s.updated_at, s.updated_by,
                       u.username AS updated_by_username
                FROM system_settings s
                LEFT JOIN users u ON u.id = s.updated_by
                ORDER BY s.key
                """
            )
            rows = cur.fetchall()

    for r in rows:
        r["typed_value"] = _cast_setting_value(r["value"], r["value_type"])
    return rows


def prune_old_audit_logs() -> int:
    """
    Delete audit_log rows older than `audit.retention_days`.

    Reads the retention window from system_settings at call time so admins
    can shorten/extend retention without a redeploy. Returns the number of
    rows actually deleted, so the caller can log it.

    Called from the FastAPI lifespan handler on startup. Running it once
    per process is enough for a coursework-scale deployment — a real
    product would put this on a cron/APScheduler job.
    """
    retention_days = get_setting("audit.retention_days")
    if retention_days is None:
        logger.warning("prune_old_audit_logs: retention setting missing, skipping.")
        return 0

    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM audit_logs
                WHERE created_at < NOW() - (%s || ' days')::interval
                """,
                (retention_days,),
            )
            deleted = cur.rowcount
        conn.commit()

    if deleted:
        logger.info(
            "Pruned %d audit_log rows older than %d days.", deleted, retention_days
        )
    return deleted


def set_setting(key: str, value: str, admin_id: int) -> dict | None:
    """
    Upsert a setting. The value_type is NOT changed here — setting types
    are defined by the seed INSERT in init_db() and are considered stable.

    Returns the updated row (with typed_value), or None if the key does
    not exist (we refuse to create new settings at runtime).
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                UPDATE system_settings
                SET value      = %s,
                    updated_at = NOW(),
                    updated_by = %s
                WHERE key = %s
                RETURNING key, value, value_type, description,
                          updated_at, updated_by
                """,
                (value, admin_id, key),
            )
            row = cur.fetchone()
        conn.commit()

    if row is not None:
        row["typed_value"] = _cast_setting_value(row["value"], row["value_type"])
    return row
