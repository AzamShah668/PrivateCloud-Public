# =============================================================================
# db/templates.py
# =============================================================================
# Data-access helpers for the Sprint 5 "Clone-from-Template" feature.
#
# Kept separate from db/database.py (which is already 1000+ lines) per the
# many-small-files convention. Reuses the same connection pool, cursor helper,
# and timestamp helper from database.py so there is a single source of truth
# for connection management.
#
# Tables owned here (created in database.init_db()):
#   vm_templates       — teacher's published golden VMs
#   class_groups       — reusable classes
#   class_enrollments  — student ↔ class membership
#   clone_batches      — one "distribute template to class" action
#   clone_jobs         — one clone per student (links to vm_jobs)
#
# See docs/design/clone-templates-architecture.md
# =============================================================================

import logging
from typing import Optional

from db.database import _conn, _dict_cursor, utc_now_iso

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# vm_templates
# ---------------------------------------------------------------------------

def create_template(
    owner_id: int,
    name: str,
    source_vmid: int,
    os_choice: str,
    *,
    description: Optional[str] = None,
    clone_mode: str = "full",
    default_cpu: int = 2,
    default_ram_mb: int = 2048,
    status: str = "draft",
) -> dict:
    """Insert a vm_templates row and return it."""
    now = utc_now_iso()
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                INSERT INTO vm_templates
                    (owner_id, name, description, source_vmid, os_choice,
                     clone_mode, default_cpu, default_ram_mb, status,
                     created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (owner_id, name, description, source_vmid, os_choice,
                 clone_mode, default_cpu, default_ram_mb, status, now, now),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def get_template(template_id: int) -> dict | None:
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM vm_templates WHERE id = %s", (template_id,))
            return cur.fetchone()


def list_templates(include_archived: bool = False, limit: int = 200) -> list[dict]:
    """List templates (newest first). Hides archived rows by default."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            if include_archived:
                cur.execute(
                    "SELECT * FROM vm_templates ORDER BY id DESC LIMIT %s",
                    (limit,),
                )
            else:
                cur.execute(
                    "SELECT * FROM vm_templates WHERE status != 'archived' "
                    "ORDER BY id DESC LIMIT %s",
                    (limit,),
                )
            return cur.fetchall()


def update_template(template_id: int, **fields) -> dict | None:
    """
    Patch a template. Only known, non-None columns are updated.
    Returns the updated row or None if the template does not exist.
    """
    # Static column → SQL fragment map. Using fixed strings (never the caller's
    # key) keeps this immune to SQL injection even if the call site changes.
    col_sql = {
        "name": "name = %s",
        "description": "description = %s",
        "clone_mode": "clone_mode = %s",
        "default_cpu": "default_cpu = %s",
        "default_ram_mb": "default_ram_mb = %s",
        "status": "status = %s",
    }
    sets: list[str] = []
    params: list = []
    for key, value in fields.items():
        if key in col_sql and value is not None:
            sets.append(col_sql[key])
            params.append(value)

    if not sets:
        return get_template(template_id)

    sets.append("updated_at = %s")
    params.append(utc_now_iso())
    params.append(template_id)

    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                f"UPDATE vm_templates SET {', '.join(sets)} WHERE id = %s RETURNING *",
                params,
            )
            row = cur.fetchone()
        conn.commit()
    return row


# ---------------------------------------------------------------------------
# class_groups + enrollments
# ---------------------------------------------------------------------------

def create_class(owner_id: int, name: str, description: Optional[str] = None) -> dict:
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                INSERT INTO class_groups (owner_id, name, description, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING *
                """,
                (owner_id, name, description, utc_now_iso()),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def get_class(class_id: int) -> dict | None:
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM class_groups WHERE id = %s", (class_id,))
            return cur.fetchone()


def list_classes(limit: int = 200) -> list[dict]:
    """List classes (newest first), each annotated with its enrollment count."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT cg.*,
                       (SELECT COUNT(*) FROM class_enrollments ce
                        WHERE ce.class_id = cg.id) AS student_count
                FROM class_groups cg
                ORDER BY cg.id DESC
                LIMIT %s
                """,
                (limit,),
            )
            return cur.fetchall()


def enroll_students(class_id: int, student_ids: list[int]) -> int:
    """
    Enroll a list of students into a class. Idempotent — duplicate
    (class_id, student_id) pairs are ignored via ON CONFLICT. Returns the
    number of NEW enrollments created.
    """
    if not student_ids:
        return 0
    now = utc_now_iso()
    created = 0
    with _conn() as conn:
        with conn.cursor() as cur:
            for sid in student_ids:
                cur.execute(
                    """
                    INSERT INTO class_enrollments (class_id, student_id, enrolled_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (class_id, student_id) DO NOTHING
                    """,
                    (class_id, sid, now),
                )
                created += cur.rowcount
        conn.commit()
    return created


def unenroll_student(class_id: int, student_id: int) -> int:
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM class_enrollments WHERE class_id = %s AND student_id = %s",
                (class_id, student_id),
            )
            deleted = cur.rowcount
        conn.commit()
    return deleted


def list_class_students(class_id: int) -> list[dict]:
    """Return enrolled students (id + username) for a class."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT u.id, u.username, ce.enrolled_at
                FROM class_enrollments ce
                JOIN users u ON u.id = ce.student_id
                WHERE ce.class_id = %s
                ORDER BY u.username
                """,
                (class_id,),
            )
            return cur.fetchall()


def get_enrolled_student_ids(class_id: int) -> list[int]:
    """Return just the student ids enrolled in a class (active users only)."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT ce.student_id
                FROM class_enrollments ce
                JOIN users u ON u.id = ce.student_id
                WHERE ce.class_id = %s AND u.status = 'active'
                ORDER BY ce.student_id
                """,
                (class_id,),
            )
            return [int(r["student_id"]) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# clone_batches + clone_jobs
# ---------------------------------------------------------------------------

def create_batch(
    template_id: int,
    class_id: int,
    initiated_by: int,
    clone_mode: str,
    cpu_cores: int,
    ram_mb: int,
    total: int,
) -> dict:
    now = utc_now_iso()
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                INSERT INTO clone_batches
                    (template_id, class_id, initiated_by, clone_mode,
                     cpu_cores, ram_mb, total, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'in_progress', %s, %s)
                RETURNING *
                """,
                (template_id, class_id, initiated_by, clone_mode,
                 cpu_cores, ram_mb, total, now, now),
            )
            row = cur.fetchone()
        conn.commit()
    return row


def get_active_batch(template_id: int, class_id: int) -> dict | None:
    """
    Return an in-progress batch for this (template, class) pair, if one exists.
    Used to block accidental double-distribution (e.g. a double-click) that
    would give every student a second identical clone.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT * FROM clone_batches
                WHERE template_id = %s AND class_id = %s AND status = 'in_progress'
                ORDER BY id DESC LIMIT 1
                """,
                (template_id, class_id),
            )
            return cur.fetchone()


def create_clone_job(batch_id: int, student_id: int) -> int:
    """Insert a queued clone_job and return its id."""
    now = utc_now_iso()
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                INSERT INTO clone_jobs
                    (batch_id, student_id, status, created_at, updated_at)
                VALUES (%s, %s, 'queued', %s, %s)
                RETURNING id
                """,
                (batch_id, student_id, now, now),
            )
            row = cur.fetchone()
        conn.commit()
    return int(row["id"])


def update_clone_job(
    clone_job_id: int,
    status: str,
    *,
    vm_job_id: Optional[int] = None,
    error_message: Optional[str] = None,
) -> None:
    """
    Update a clone_job's status. vm_job_id is written via COALESCE so it is
    only set once (when the underlying vm_jobs row is created) and never
    cleared by later status updates.
    """
    with _conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE clone_jobs
                SET status        = %s,
                    vm_job_id     = COALESCE(%s, vm_job_id),
                    error_message = %s,
                    updated_at    = %s
                WHERE id = %s
                """,
                (status, vm_job_id, error_message, utc_now_iso(), clone_job_id),
            )
        conn.commit()


def get_clone_job(clone_job_id: int) -> dict | None:
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM clone_jobs WHERE id = %s", (clone_job_id,))
            return cur.fetchone()


def rollup_batch_status(batch_id: int) -> str:
    """
    Recompute and persist a batch's status from its clone_jobs:
      - any still queued/cloning  → 'in_progress'
      - all done                  → 'completed'
      - all failed                → 'failed'
      - mix of done + failed      → 'partial'
    Returns the new status.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*)                                        AS total,
                    COUNT(*) FILTER (WHERE status = 'done')         AS done,
                    COUNT(*) FILTER (WHERE status = 'failed')       AS failed,
                    COUNT(*) FILTER (WHERE status IN ('queued','cloning')) AS pending
                FROM clone_jobs
                WHERE batch_id = %s
                """,
                (batch_id,),
            )
            c = cur.fetchone()

            if c["total"] == 0:
                new_status = "failed"  # nothing to do — treat as failed, not "completed"
            elif c["pending"] > 0:
                new_status = "in_progress"
            elif c["failed"] == 0:
                new_status = "completed"
            elif c["done"] == 0:
                new_status = "failed"
            else:
                new_status = "partial"

            cur.execute(
                "UPDATE clone_batches SET status = %s, updated_at = %s WHERE id = %s",
                (new_status, utc_now_iso(), batch_id),
            )
        conn.commit()
    return new_status


def get_batch_progress(batch_id: int) -> dict | None:
    """
    Return a batch with its per-student clone_jobs (joined to username and the
    underlying vm_jobs status/ip). Used by the admin batch-progress view.
    """
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            cur.execute("SELECT * FROM clone_batches WHERE id = %s", (batch_id,))
            batch = cur.fetchone()
            if batch is None:
                return None

            cur.execute(
                """
                SELECT cj.id, cj.student_id, cj.vm_job_id, cj.status,
                       cj.error_message, cj.updated_at,
                       u.username,
                       vj.vm_name, vj.vmid, vj.status AS vm_status, vj.vm_ip
                FROM clone_jobs cj
                JOIN users u ON u.id = cj.student_id
                LEFT JOIN vm_jobs vj ON vj.id = cj.vm_job_id
                WHERE cj.batch_id = %s
                ORDER BY u.username
                """,
                (batch_id,),
            )
            batch["clones"] = cur.fetchall()
    return batch
