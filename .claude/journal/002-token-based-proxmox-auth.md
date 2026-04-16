---
date: 2026-04-03
title: Token-Based Proxmox API Authentication
task: "#18 — token based proxmox api calls"
sprint: 2
---

### 2026-04-03 — Token-Based Proxmox API Authentication

**Task:** GitHub Issue #18 — token based proxmox api calls

**What was done:**
I refactored the ProxmoxClient to support Proxmox API token authentication alongside the existing ticket-based auth. The old ticket auth required POSTing username/password to get a session cookie that expired every 2 hours — we had auto-renewal logic but it was fragile for long-running services. API tokens never expire, need no cookies or CSRF tokens, and just use a single `Authorization` header on every request.

The implementation is backward-compatible: if `PROXMOX_TOKEN_ID` and `PROXMOX_TOKEN_SECRET` env vars are set, it uses token auth automatically. If they're not set, it falls back to the old ticket auth so nothing breaks for existing setups.

**Files changed:**
- `backend/app/proxmox_client.py` — Added token auth detection in `__init__()`, made `authenticate()` a no-op for token mode, updated `_ensure_authenticated()` to skip renewal for tokens, changed `_get_cookies()` to return empty dict for token auth, rewrote `_get_headers()` to return `Authorization: PVEAPIToken=<id>=<secret>` for token mode, added headers to `_get()` (previously GET requests didn't send headers — but token auth needs the Authorization header on every request including GETs)
- `.env.example` — Added `PROXMOX_TOKEN_ID` and `PROXMOX_TOKEN_SECRET` as the preferred auth method, commented out the old username/password vars as legacy fallback
- `.claude/docs/proxmox-integration.md` — Updated documentation to reflect both auth methods and the new `_delete()` helper Nashid added

**Problems encountered:**
1. **GET requests didn't pass headers**: The original `_get()` method only passed cookies, no headers. Ticket auth didn't need headers for GETs (only the cookie). But token auth requires the `Authorization` header on ALL requests including GETs.
   - *First attempt*: I initially only updated `_get_headers()` and `_post()`.
   - *Why it failed*: Realized `_get()` never called `_get_headers()` at all — GETs would silently fail with 401 in token mode.
   - *Solution*: Added `headers=self._get_headers()` to the `_get()` method so token auth works for read operations too.

2. **Partner's changes needed integration**: Before starting, I had to pull from GitHub first because my partner (Nashid) had pushed new commits adding `delete_vm()`, a `_delete()` HTTP helper, and the DELETE endpoint. I had to make sure my token auth changes worked with his new `_delete()` method too.
   - *Solution*: Updated `_delete()` comments to note it works with both auth methods. The actual code already called `_get_headers()` and `_get_cookies()`, so it inherited the token auth behavior automatically.

**Key decisions:**
- **Backward compatibility**: I kept both auth methods instead of ripping out ticket auth. Why — Nashid might still be using ticket auth in his environment. This way nobody's setup breaks. The code auto-detects which mode to use based on whether `PROXMOX_TOKEN_ID` is set.
- **No separate auth module**: Could have extracted auth into its own class/strategy pattern, but that's over-engineering for 2 auth methods. The if/else approach is readable and easy to follow.

**What I learned:**
- Proxmox API tokens use a specific format: `PVEAPIToken=user@realm!tokenname=uuid-secret`. The `!` separating the user from the token name is important — it's not a typo.
- Token auth is simpler in every way: no login endpoint, no cookies, no CSRF, no expiry timer. Should have been the default from the start.

**If asked "How did you do this?":**
> I modified the ProxmoxClient class to detect if API token environment variables are set. If they are, it skips the ticket login entirely and sends an Authorization header with every request instead. If they're not set, the old ticket auth still works as a fallback. I had to make sure GET requests also send headers now — they didn't before because ticket auth only needed cookies for GETs.

**If asked "Where did you get stuck?":**
> The tricky part was realizing that the GET helper method never passed headers — only cookies. Ticket auth doesn't need headers for GETs, but token auth does. If I hadn't caught that, all read operations (list VMs, get status) would have failed with 401 Unauthorized in token mode.
