# 006 — Proxmox VM Rebuild & Environment Reconfiguration

**Date:** 2026-04-12
**Sprint:** 2
**Author:** Azam (with Claude)

---

## What Was Done

Azam deleted the old Proxmox VM and created a new one because the previous one was not working properly. This required a full environment reconfiguration to point the backend at the new Proxmox instance.

### 1. Environment Variable Updates (`.env`)

Updated all Proxmox-related credentials:

| Variable | Old Value | New Value |
|----------|-----------|-----------|
| `PROXMOX_HOST` | `192.168.31.112` | `192.168.31.155` |
| `PROXMOX_PASSWORD` | `verventech123` | `VERVENTECH123` |
| `PROXMOX_NODE` | `azam` | `pve` |
| `PROXMOX_TOKEN_ID` | `root@pam!proxmox-app` | `root@pam!proxmox` |
| `PROXMOX_TOKEN_SECRET` | `1932762e-...` | `7ccd2821-f91c-448b-b777-219a8e5b53f7` |

JWT secret was also regenerated earlier: `9e263e3a10e0d3db97d1c287291cf08ba84a4714102388103625168951b16eea` (32-byte hex via `openssl rand -hex 32`).

### 2. Docker Backend Restart

- Ran `docker compose up -d --force-recreate backend` to reload new env vars
- Verified PostgreSQL pool created (min=2, max=10)
- Verified DB schema intact
- Confirmed API responding at `http://localhost:8000/`

### 3. Proxmox Token Auth Verification

Tested the full auth flow via curl:
1. `POST /auth/register` — created test user (id=4)
2. `POST /auth/login` — received JWT token
3. `GET /vms/` — returned `[]` (empty array, no error)

The empty array confirms the backend successfully authenticated to Proxmox at 192.168.31.155 using the API token `root@pam!proxmox`. If the token were invalid or Proxmox unreachable, the endpoint would return an error, not an empty list.

### 4. Ubuntu ISO Upload to Proxmox

Azam uploaded `ubuntu-24.04.4-desktop-amd64.iso` (6.6 GB) to Proxmox storage via the web UI.

- **ISO path:** `local:iso/ubuntu-24.04.4-desktop-amd64.iso`
- **Target:** `/var/lib/vz/template/iso/ubuntu-24.04.4-desktop-amd64.iso`
- **Status:** TASK OK — upload completed successfully

### 5. Proxmox VM Crash (Paused-Critical)

During the ISO upload process, the Proxmox VM (running inside Hyper-V) entered **Paused-Critical** state with error: "Disk(s) encountered critical I/O errors".

**Root cause:** The virtual disk ran out of space while storing the 6.6 GB ISO file.

**Resolution:** Azam created a new Proxmox VM with more disk space allocated, which is why all credentials changed (new IP, new node name, new API token).

## Problems Encountered

1. **Docker Desktop daemon not responding:** Docker Desktop was installed but the daemon took multiple minutes to initialize. We set up a Monitor to poll every 5 seconds (30 attempts). Docker Desktop needed to be manually launched from the Start menu.

2. **Proxmox VM disk full:** The Hyper-V VM running Proxmox didn't have enough disk space for the Ubuntu ISO (6.6 GB). This caused a critical I/O error and paused the VM.

3. **Docker Desktop disconnecting repeatedly:** Between sessions, Docker Desktop would stop running and need to be relaunched manually.

## Files Changed

- `.env` — Updated PROXMOX_HOST, PROXMOX_PASSWORD, PROXMOX_NODE, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET, JWT_SECRET_KEY

## Key Decisions

- **Token auth over password auth:** We configured both password and API token credentials. The backend code in `proxmox_client.py` prefers token auth when `PROXMOX_TOKEN_ID` and `PROXMOX_TOKEN_SECRET` are set.
- **Proxmox node name `pve`:** The new VM uses the default Proxmox node name instead of the custom `azam` name used previously.

## Ready for Teacher Q&A

**Q: Why did you rebuild the Proxmox VM?**
A: The original VM had insufficient disk space, which caused a critical I/O error during ISO upload. The new VM has more storage allocated.

**Q: How do you verify the Proxmox connection is working?**
A: Hit `GET /vms/` with a valid JWT token. If Proxmox is reachable and the API token is valid, it returns an array (empty or with VMs). If not, it returns an error response.

**Q: What's the difference between password auth and token auth for Proxmox?**
A: Password auth sends username/password to get a temporary ticket (session cookie). Token auth uses a permanent API token (`PVEAPIToken=user!tokenid=secret`) in the Authorization header — no ticket exchange needed, more suitable for automation.
