---
date: 2026-04-03
title: Enhanced VM List with Live Proxmox Status
task: "#20 — enhance vmList"
sprint: 2
---

### 2026-04-03 — Enhanced VM List with Live Proxmox Status

**Task:** GitHub Issue #20 — enhance vmList

**What was done:**
I upgraded the `GET /vms/` endpoint to return live data from Proxmox alongside the database records. Previously it only returned what was stored in the DB (the job record) — so you'd see the VM was "done" but had no idea if it was actually running, stopped, how much CPU it's using, or how long it's been up. Now each VM in the list includes `live_status`, `cpu_usage`, `mem_usage`, `max_mem`, `uptime`, `netin`, and `netout` pulled in real-time from Proxmox.

The key optimization: I make ONE bulk API call to Proxmox (`list_vms()`) which returns all VMs on the node, then match by vmid. This avoids making N separate API calls (one per VM), which would be painfully slow if a user has 10+ VMs.

**Files changed:**
- `backend/app/models/vm.py` — Added `VMEnrichedResponse` model extending `VMJobResponse` with 7 new live fields (live_status, cpu_usage, mem_usage, max_mem, uptime, netin, netout)
- `backend/app/routes/vm_routes.py` — Rewrote `GET /vms/` endpoint: fetch jobs from DB, fetch all VMs from Proxmox in one call, build a vmid→status lookup dict, merge the two datasets, return enriched responses
- `.claude/docs/api-routes.md` — Updated endpoint catalog: added PATCH and DELETE endpoints, VMUpdateRequest, VMEnrichedResponse, VMStatus/VMAction enums, new error codes

**Problems encountered:**
1. **Performance: N+1 API call problem**: The naive approach would be to loop through each user's VM and call `get_vm_status(vmid)` individually. With 10 VMs that's 10 separate HTTP requests to Proxmox.
   - *Solution*: Used the existing `list_vms()` method which returns ALL VMs on the node in one call, then built a dict keyed by vmid for O(1) lookups. One API call regardless of how many VMs the user has.

2. **Graceful degradation when Proxmox is down**: If Proxmox is unreachable, the old endpoint would just return DB data silently. The new endpoint needed the same behavior — never crash just because Proxmox is down.
   - *Solution*: Wrapped the Proxmox call in try/except. If it fails, `live_status_map` stays empty, all VMs get `live_status: "unknown"`, and the remaining DB fields still render correctly.

3. **Response model inheritance**: Needed the enriched response to include all the same fields as VMJobResponse plus the new live fields.
   - *Solution*: Made `VMEnrichedResponse` extend `VMJobResponse` using Python class inheritance. Pydantic v2 handles this cleanly — all parent fields are inherited, new fields get default values (None for optional, "unknown" for live_status).

**Key decisions:**
- **One model, not two endpoints**: Could have made a separate `/vms/live` endpoint. Instead, I replaced the response model of the existing `GET /vms/` from `VMJobResponse` to `VMEnrichedResponse`. Since the enriched model extends the base one, it's backward-compatible — all the old fields are still there.
- **Default live_status is "unknown"**: Not "offline" or "error" — because we genuinely don't know. Could be running fine, we just can't reach Proxmox to check. "unknown" is the most honest answer.

**What I learned:**
- Proxmox's `list_vms()` endpoint (`GET /nodes/{node}/qemu`) returns different fields than `get_vm_status()` (`GET /nodes/{node}/qemu/{vmid}/status/current`). The list endpoint includes `cpu`, `mem`, `maxmem`, `uptime`, `netin`, `netout` — exactly what we need for a dashboard view. Lucky — no extra API call needed.
- Pydantic model inheritance in v2 is clean: child models inherit all parent fields + validation, and `model_validate()` works on both the parent dict and extra fields.

**If asked "How did you do this?":**
> I modified the GET /vms/ endpoint to make one bulk call to Proxmox that returns all VMs on the node, then match each user's VM by its vmid to get live stats like running/stopped, CPU usage, memory, and uptime. If Proxmox is down, it still works — you just see "unknown" for the live status.

**If asked "Where did you get stuck?":**
> The main challenge was avoiding the N+1 query problem. Instead of calling Proxmox once per VM, I use one bulk call and build a lookup dictionary. This keeps the endpoint fast even with many VMs.
