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
) -> int:
    """
    Insert a new VM job in 'queued' status and return its generated id.

    request_payload is stored as JSONB so it can be queried efficiently
    from PostgreSQL if needed later.
    """
    now = utc_now_iso()
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                INSERT INTO vm_jobs
                    (user_id, vmid, vm_name, os_choice, request_payload,
                     status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, 'queued', %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    vmid,
                    vm_name,
                    os_choice,
                    json.dumps(request_payload),  # psycopg2 accepts a JSON string for JSONB
                    now,
                    now,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    return int(row["id"])


def update_vm_job(
    job_id: int,
    status: str,
    proxmox_response: dict | None = None,
    error_message: str | None = None,
) -> None:
    """
    Update the status (and optional response/error) of an existing VM job.

    Typical status flow:  queued → running → done
                                           → failed
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE vm_jobs
                SET status           = %s,
                    proxmox_response = %s,
                    error_message    = %s,
                    updated_at       = %s
                WHERE id = %s
                """,
                (
                    status,
                    json.dumps(proxmox_response) if proxmox_response is not None else None,
                    error_message,
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
