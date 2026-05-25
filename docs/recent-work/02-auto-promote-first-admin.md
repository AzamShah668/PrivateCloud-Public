# 02 — Auto-Promote First User to Admin

**Commit:** `d6d7988` · **Date:** 2026-05-24 · **File:** `db/database.py`

## What it does

The **very first** account ever created on a fresh PrivateCloud install is automatically given the `admin` role. Every subsequent registration gets the normal default role. This solves a bootstrap chicken-and-egg problem: the admin portal needs an admin to exist, but there's no way to create one through the UI before any admin exists.

## Where it lives

It's a 6-line guard inside `create_user()` in `db/database.py` — the single function every registration funnels through. Putting it at the data layer (not in a route) means it applies no matter how the user is created (API, seed script, ChatOps).

## The code

```python
def create_user(...):
    """..."""
    with _conn() as conn:
        with _dict_cursor(conn) as cur:
            # Auto-promote the very first user to admin
            cur.execute("SELECT COUNT(*) AS c FROM users")
            user_count = cur.fetchone()["c"]
            if user_count == 0:
                role = "admin"

            cur.execute(
                """
                INSERT INTO users (username, password_hash, role, daily_quota, created_at)
                ...
                """
            )
```

## How it works, step by step

1. Before inserting the new row, count existing users: `SELECT COUNT(*) FROM users`.
2. If the count is `0`, this is the founding account → overwrite the incoming `role` parameter with `"admin"`.
3. Proceed with the normal `INSERT`, now carrying `role = 'admin'` for that first user only.
4. The second user onward sees `user_count > 0`, so the guard does nothing and their requested/default role is preserved.

## Why this design

- **Idempotent by construction.** It can only ever fire once — the moment one user exists the count is never `0` again.
- **No new migration, no new column, no env var.** It reuses the existing `role` column and `users` table.
- **Atomic with the insert.** The `COUNT` and `INSERT` run on the same connection inside the same `with` block, so there's no separate "promote" step that could be skipped.

## Edge cases & caveats

- **Race condition (theoretical):** two simultaneous registrations on a brand-new DB could both read `count == 0` and both become admin. In practice the very first signup is a single manual action, so this is acceptable. Hardening would wrap it in a transaction with `SELECT ... FOR UPDATE` or a unique partial index.
- **Deleting all users** then registering again would re-promote — correct behaviour for a true reset.

## Teaching summary

| | |
|---|---|
| **Goal** | Make the platform usable on first boot without a manual SQL `UPDATE`. |
| **Mechanism** | Count users inside `create_user`; if zero, force `role='admin'`. |
| **Why the data layer** | Applies to every creation path, stays atomic with the insert. |
