# 009 — Fix Login Case-Sensitivity Bug

**Date:** 2026-04-13
**Sprint:** 2
**Type:** Bug Fix

## What Was Done

Fixed a bug where users could not log in to accounts they had already registered.

## The Problem

The registration flow in `UserCreate` (models/user.py:63) normalises the username to lowercase via a Pydantic validator:

```python
return v.lower()  # normalise to lowercase for consistency
```

So registering as "Azam" stores `azam` in the database.

However, the login route in `auth_routes.py:178` passed `form_data.username` directly to the DB lookup **without** lowercasing. So logging in as "Azam" searched for "Azam" in the database, found nothing (because it was stored as "azam"), and returned 401 Unauthorized.

## The Fix

Added `.strip().lower()` normalisation to the login username before the DB lookup:

```python
username = form_data.username.strip().lower()
user_dict = database.get_user_by_username(username)
```

## Files Changed

| File | Change |
|------|--------|
| `backend/app/routes/auth_routes.py` | Normalise `form_data.username` to lowercase before DB lookup |

## Root Cause

Registration and login had inconsistent username normalisation. Registration lowercased via Pydantic validator; login used raw input.

## Lesson Learned

When normalising data on write (registration), always apply the same normalisation on read (login). This is a classic case where the write path and read path diverged.
