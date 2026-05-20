# Proxmox setup scripts

Scripts that prepare the Proxmox node so the PrivateCloud backend can provision VMs quickly by **cloning** a pre-built template instead of installing from an ISO every time.

## SETUP_GOLDEN_IMAGE.sh

**What it does:** builds a Proxmox template (VMID `9000`, name `ubuntu-24.04-template`) from a local Ubuntu 24.04 cloud image. The template has `qemu-guest-agent` and SSH password auth pre-baked, so cloned VMs boot to SSH in ~5-10 seconds instead of 30-90 seconds.

**When to run it:** one time only, on the Proxmox node, as root. Re-run only if you deleted the template or need to rebuild it.

**Where the template is used in the backend:** `GOLDEN_IMAGE_VMID` (default `9000`) in [backend/app/proxmox_client.py](../../backend/app/proxmox_client.py). The create-VM flow clones that template for Linux OS choices (`ubuntu-*`, `debian-12`, `centos-9`). For **Windows 11**, set `WINDOWS_TEMPLATE_VMID` (default `9001`) and follow [Setup_win11_iso.md](../../Setup_win11_iso.md).

## How to run

On the Proxmox node (as root):

```bash
# 1. Make sure you have the Ubuntu 24.04 cloud image locally
#    (download from https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img)
export CLOUD_IMG=/root/noble-server-cloudimg-amd64.img

# 2. Make the script executable
chmod +x SETUP_GOLDEN_IMAGE.sh

# 3. Run it (defaults: VMID=9000, STORAGE=local-lvm, NAME=ubuntu-24.04-template)
./SETUP_GOLDEN_IMAGE.sh

# If apt/DNS is broken on the node, use the snippet-only fallback:
SKIP_VIRT_CUSTOMIZE=1 ./SETUP_GOLDEN_IMAGE.sh
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `CLOUD_IMG` | `/root/noble-server-cloudimg-amd64.img` | Path to the Ubuntu cloud image |
| `VMID` | `9000` | Template VMID (must match `GOLDEN_IMAGE_VMID` in backend `.env`) |
| `NAME` | `ubuntu-24.04-template` | Template display name |
| `STORAGE` | `local-lvm` | Proxmox storage pool |
| `SKIP_VIRT_CUSTOMIZE` | `0` | Set to `1` to skip baking agent into disk (uses cloud-init snippet instead) |

## Verify it worked

After the script finishes, on the Proxmox node:

```bash
qm status 9000
# Expected: status: stopped  (templates cannot run)

qm config 9000 | grep template
# Expected: template: 1
```

If both succeed, the backend can clone this template for Linux VMs.

## Windows 11 template

Build a Windows template (e.g. VMID **9001**) using [Setup_win11_iso.md](../../Setup_win11_iso.md). Set `WINDOWS_TEMPLATE_VMID=9001` in the backend environment so `os_choice: windows-11` clones that template.
