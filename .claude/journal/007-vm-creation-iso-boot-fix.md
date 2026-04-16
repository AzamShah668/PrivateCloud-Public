# 007 — VM Creation: ISO Boot Order Fix & use_template Flag

**Date:** 2026-04-12
**Sprint:** 2
**Author:** Azam (with Claude)

---

## What Was Done

### 1. Added `use_template` flag to VMCreateRequest

**Problem:** The `POST /vms/` endpoint always tried to clone template 9000 when `os_choice` was `"ubuntu-24.04"` (via `CLOUD_TEMPLATE_MAP`). Template 9000 didn't exist on the new Proxmox instance, causing a 403 error.

**Fix:** Added a `use_template: bool = False` field to `VMCreateRequest` in `models/vm.py`. The route logic in `vm_routes.py` now only checks `CLOUD_TEMPLATE_MAP` when `use_template=True`. Default behavior is ISO-based creation.

**Files changed:**
- `backend/app/models/vm.py` — added `use_template` field
- `backend/app/routes/vm_routes.py` — gated template lookup on `vm_request.use_template`

### 2. Fixed ISO boot order in create_vm

**Problem:** After fixing the template issue, VMs were created successfully (201 response) but wouldn't boot. The VM console showed "Boot failed: not a bootable disk" and "No bootable device." The Ubuntu ISO was attached on `ide2` as a CD-ROM, but the boot order was hardcoded to `"boot": "c"` (hard disk only via `scsi0`). The VM never tried booting from the ISO.

**Root cause:** In `proxmox_client.py`, the boot parameters were:
```python
"boot":     "c",        # only boot from hard disk
"bootdisk": "scsi0",    # hard disk is blank — no OS installed yet
```

The ISO on `ide2` was correctly attached but the boot order ignored it entirely.

**Fix:** Changed `proxmox_client.py` to set boot order dynamically:
```python
if config.get("iso"):
    proxmox_params["boot"] = "order=ide2;scsi0"   # CD-ROM first, then disk
else:
    proxmox_params["boot"] = "order=scsi0"         # no ISO, disk only
```

**File changed:** `backend/app/proxmox_client.py` — replaced static boot order with conditional logic

### 3. Updated ISO mapping for ubuntu-24.04

**Problem:** `_OS_MAP` in `vm_routes.py` had `ubuntu-24.04-live-server-amd64.iso` but Azam uploaded `ubuntu-24.04.4-desktop-amd64.iso`.

**Fix:** Updated the ISO path in `_OS_MAP` to match the actual uploaded file.

**File changed:** `backend/app/routes/vm_routes.py` — updated ISO filename in `_OS_MAP`

## Problems Encountered

1. **403 Permission check failed (VM.Clone):** First attempt used template clone path — template 9000 didn't exist on new Proxmox. Fixed by adding `use_template` flag.

2. **403 Permission check failed (POST /qemu):** API token `root@pam!proxmox` was created with "Privilege Separation" enabled, so it didn't inherit root permissions. Fixed by Azam recreating the token with Privilege Separation unchecked in Proxmox UI.

3. **No bootable device:** VM created successfully but ISO not in boot order. Fixed by changing boot order to prioritize `ide2` (CD-ROM) when ISO is attached.

4. **ISO filename mismatch:** `_OS_MAP` had wrong filename for ubuntu-24.04. Fixed by updating to match the actual uploaded ISO.

## Files Changed

- `backend/app/models/vm.py` — added `use_template: bool = False` field
- `backend/app/routes/vm_routes.py` — gated template logic on `use_template`, updated ISO filename
- `backend/app/proxmox_client.py` — fixed boot order to prioritize CD-ROM when ISO attached

## Key Decisions

- **`use_template` defaults to `False`:** ISO creation is the safe default. Template cloning is opt-in since it requires pre-configured templates.
- **Boot order is dynamic:** When ISO is present, boot CD-ROM first so the installer runs. When no ISO, boot hard disk only.

## Ready for Teacher Q&A

**Q: Why did the VM say "No bootable device"?**
A: The boot order was set to `"c"` (hard disk only). The ISO was attached as a CD-ROM on `ide2` but the VM never tried booting from it. I fixed it by setting `boot=order=ide2;scsi0` so the CD-ROM is tried first.

**Q: Why did you add `use_template` instead of just removing the template map?**
A: Because Azam wants both options — create fresh VMs from ISO and clone from templates. The flag lets the user choose per request. Template cloning is faster for production, but ISO creation is needed when no template exists yet.

**Q: What's the difference between `ide2` and `scsi0`?**
A: `scsi0` is the main hard disk (where the OS gets installed). `ide2` is the CD-ROM drive (where the ISO is mounted). During initial setup, you boot from `ide2` to run the installer, which writes the OS to `scsi0`. After installation, future boots use `scsi0`.
