# Golden Image Setup Guide

This guide walks you through creating the Ubuntu 24.04 golden image template (VMID 9000) on your Proxmox node. This template is what your PrivateCloud app clones every time a user creates a new VM.

---

## Before You Start

Make sure you have:
- SSH access to your Proxmox node (`192.168.0.xxx`)
- The `create_golden_image.sh` script copied to the node
- VMID 9000 free (if it exists, destroy it first)

---

## Step 1 — Open the Script and Change These Values

Open `create_golden_image.sh` in any text editor and find the config block at the top (lines 25–41). These are the only things you need to change:

```bash
DEFAULT_PASSWORD="PrivateCloud@2024"   # ← CHANGE THIS
```

Set it to whatever SSH password you want baked into every VM your app creates. Users will use this password to log in after their VM is provisioned.

```bash
DEFAULT_USER="ubuntu"   # leave this as-is unless you want a different username
```

You can also change these if your setup is different:

| Variable | Default | What it is |
|---|---|---|
| `VMID` | `9000` | Template VMID in Proxmox |
| `STORAGE` | `local-lvm` | Where the disk is stored |
| `BRIDGE` | `vmbr0` | Network bridge |
| `DISK_SIZE` | `20G` | Disk size of the template |
| `RAM_MB` | `2048` | RAM (only affects the template, clones can override) |
| `CPU_CORES` | `2` | CPU cores (same as above) |

---

## Step 2 — Update Your .env File

In your PrivateCloud project, open `.env` and make sure these three values match exactly what you set in the script:

```ini
GOLDEN_IMAGE_VMID=9000
VM_DEFAULT_USERNAME=ubuntu
VM_DEFAULT_PASSWORD=PrivateCloud@2024   # same as DEFAULT_PASSWORD in the script
```

The app reads these values and returns them to the user after VM creation so they know how to SSH in.

---

## Step 3 — Copy the Script to Your Proxmox Node

Run this from your local machine:

```bash
scp create_golden_image.sh root@192.168.0.xxx:/root/
```

---

## Step 4 — SSH Into Your Proxmox Node

```bash
ssh root@192.168.0.xxx
```

---

## Step 5 — Run the Script

```bash
chmod +x /root/create_golden_image.sh
./create_golden_image.sh
```

The script will go through 7 steps automatically. The only slow part is Step 4 (customising the image) which takes about 60 seconds. You will see output like this when it is done:

```
╔══════════════════════════════════════════════╗
║   Golden Image Created Successfully!         ║
╚══════════════════════════════════════════════╝
```

---

## Step 6 — Verify in Proxmox Web UI

Open `https://192.168.0.xxx:8006` and check:

- VMID 9000 appears in the left sidebar with a **template icon** (stack of papers)
- Click it → Hardware tab → confirm `QEMU Guest Agent` shows `enabled=1`

---

## What the Script Sets Up

| Feature | Details |
|---|---|
| OS | Ubuntu 24.04 LTS (cloud image, no installer) |
| SSH | Password authentication enabled on port 22 |
| User | `ubuntu` with sudo access, no password prompt for sudo |
| Guest Agent | `qemu-guest-agent` installed and enabled — this is how the app gets the VM's IP after boot |
| Console | Standard VGA — works normally in Proxmox web console |
| Cloud-init | Configured for DHCP — each clone gets its own IP automatically |

---

## If VMID 9000 Already Exists

Destroy it first, then re-run the script:

```bash
qm destroy 9000 --purge
./create_golden_image.sh
```

---

## If the Cloud Image Is Already Downloaded

The script checks for the file at `/root/noble-server-cloudimg-amd64.img` automatically. If it exists it skips the download. If you want a fresh download, delete it first:

```bash
rm /root/noble-server-cloudimg-amd64.img
./create_golden_image.sh
```

---

## Testing After Setup

Create a VM from your PrivateCloud app and check the API response. You should get back all three fields populated:

```json
{
  "vm_ip": "192.168.0.xxx",
  "vm_username": "ubuntu",
  "vm_password": "PrivateCloud@2024"
}
```

Then SSH in to confirm:

```bash
ssh ubuntu@192.168.0.xxx
# enter your DEFAULT_PASSWORD when prompted
```
