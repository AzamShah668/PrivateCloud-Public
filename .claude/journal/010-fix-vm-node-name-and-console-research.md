# 010 — Fix VM Node Name Bug & Console Access Research

**Date:** 2026-04-14
**Sprint:** 2
**Author:** Azam (with Claude Code)

## What was done

### 1. Fixed VM Start 502 Error (node name mismatch)

When clicking "Start" on VM job #1 (VMID 100) in the frontend, the backend returned 502 Bad Gateway. The backend logs showed:

```
POST nodes/azam/qemu/100/status/start failed: 500 Server Error:
hostname lookup 'azam' failed - failed to get address info for: azam
```

**Root cause:** VM job #1 was created early in Sprint 1 when the Proxmox node was named `azam`. The node name was stored in `request_payload.node` in the `vm_jobs` table. Later the Proxmox node was renamed/rebuilt as `pve` (and `.env` updated to `PROXMOX_NODE=pve`), but the old DB record still had `"node": "azam"`.

The PATCH endpoint in `vm_routes.py:451` reads the node from the stored payload:
```python
node = job["request_payload"].get("node", proxmox.default_node)
```

**Fix:** Updated the `request_payload` JSON in the `vm_jobs` table for job #1, changing `node` from `"azam"` to `"pve"`. After the fix, the Start button worked and returned "VM startup initialized".

**Files changed:** Database only (no code changes needed).

### 2. Console Access Research

After successfully starting the VM, the user expected to see the VM's desktop/interface in the PrivateCloud web app. Investigated whether this was planned.

**Findings from GitHub Kanban (verventech/PrivateCloud project board):**
- VM console access (noVNC integration) is NOT mentioned in any sprint
- Sprint 3 Issue #24 plans to "return VM details after creation" including name, IP, and SSH/RDP credentials
- The intended UX is: user gets credentials from the app, then connects via their own SSH/RDP client
- A built-in web console (noVNC) would be a separate future feature

**Current workaround:** Users can access VM consoles through the Proxmox Web UI at `https://<proxmox-host>:8006`.

## Problems encountered

1. `psql` not available on Windows PATH — used `backend/venv/Scripts/python` with psycopg2 instead
2. Python encoding issue with cp1252 — added `encoding='utf-8'` to file reads
3. Database `users` table has no `email` column — adjusted queries accordingly

## Key decisions

- DB-only fix was appropriate here (no code change needed since the root cause was stale data, not a bug)
- noVNC console integration deferred — not in current sprint scope, and Sprint 3 plans SSH/RDP credential display instead

## Lessons learned

- When Proxmox node names change, stored `request_payload` in `vm_jobs` becomes stale. Consider using `proxmox.default_node` as the authoritative source rather than the stored value, or at least falling back to it.
