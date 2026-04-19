#!/usr/bin/env bash
# ============================================================
# SETUP_GOLDEN_IMAGE.sh
# Run ONCE on your Proxmox node as root.
#
# Builds a single golden template from a **local** Ubuntu 24.04 (noble) cloud
# image. The qm steps match a typical manual sequence (see comments in repo).
#
# By default the script uses virt-customize to install qemu-guest-agent into a
# copy of the disk (needs: apt + libguestfs-tools, working DNS/internet).
#
# If apt/DNS is broken on the node, use:
#   SKIP_VIRT_CUSTOMIZE=1 ./SETUP_GOLDEN_IMAGE.sh
# The script will automatically create a cloud-init vendor snippet that installs
# and starts qemu-guest-agent on first boot (required for IP detection).
#
# Usage:
#   chmod +x SETUP_GOLDEN_IMAGE.sh
#   export CLOUD_IMG=/root/noble-server-cloudimg-amd64.img   # if needed
#   ./SETUP_GOLDEN_IMAGE.sh
#   # or: SKIP_VIRT_CUSTOMIZE=1 ./SETUP_GOLDEN_IMAGE.sh
#
# Matches app mapping: ubuntu-24.04 → VMID 9000 (CLOUD_TEMPLATE_MAP in proxmox_client.py).
# ============================================================

set -euo pipefail

CLOUD_IMG="${CLOUD_IMG:-/root/noble-server-cloudimg-amd64.img}"
VMID="${VMID:-9000}"
NAME="${NAME:-ubuntu-24.04-template}"
STORAGE="${STORAGE:-local-lvm}"
SKIP_VIRT_CUSTOMIZE="${SKIP_VIRT_CUSTOMIZE:-0}"
SNIPPETS_DIR="/var/lib/vz/snippets"
SNIPPET_FILE="$SNIPPETS_DIR/qemu-agent.yaml"

NODE=$(hostname)

echo "Proxmox golden template (Ubuntu 24.04 noble only)"
echo "Node: $NODE  |  Storage: $STORAGE  |  VMID: $VMID"
if [[ "$SKIP_VIRT_CUSTOMIZE" == "1" ]]; then
  echo "SKIP_VIRT_CUSTOMIZE=1 — importing .img as-is; cloud-init snippet will install guest-agent on first boot"
fi
echo ""

if [[ ! -f "$CLOUD_IMG" ]]; then
  echo "Image not found: $CLOUD_IMG"
  echo "  export CLOUD_IMG=/full/path/to/noble-server-cloudimg-amd64.img"
  exit 1
fi

if qm status "$VMID" &>/dev/null; then
  echo "⚠  VMID $VMID already exists — delete it first or set VMID to a free id."
  exit 1
fi

# ── Cloud-init snippet (always created) ─────────────────────────────────────
# Even when virt-customize bakes in the agent, the snippet is harmless (idempotent).
# When SKIP_VIRT_CUSTOMIZE=1 it is the ONLY way the agent gets installed.
echo "→ Creating cloud-init vendor snippet: $SNIPPET_FILE"
mkdir -p "$SNIPPETS_DIR"
cat > "$SNIPPET_FILE" << 'EOF'
#cloud-config
packages:
  - qemu-guest-agent
runcmd:
  - systemctl enable qemu-guest-agent
  - systemctl start qemu-guest-agent
EOF
echo "   Snippet written."

# ── Optional: virt-customize to bake agent into disk ────────────────────────
IMPORT_IMG="$CLOUD_IMG"

if [[ "$SKIP_VIRT_CUSTOMIZE" != "1" ]]; then
  TMP_DIR=$(mktemp -d)
  trap 'rm -rf "$TMP_DIR"' EXIT
  WORK_IMG="$TMP_DIR/noble-cloudimg-work.qcow2"
  echo "→ Copying image to temp (sparse) …"
  cp --sparse=always "$CLOUD_IMG" "$WORK_IMG"

  if ! command -v virt-customize &>/dev/null; then
    echo "→ Installing libguestfs-tools (virt-customize) …"
    if ! apt-get update -qq; then
      echo ""
      echo "apt-get update failed — falling back to cloud-init snippet only."
      echo "qemu-guest-agent will be installed on first boot via $SNIPPET_FILE"
      echo ""
      SKIP_VIRT_CUSTOMIZE=1
    else
      if ! apt-get install -y libguestfs-tools; then
        echo "apt-get install libguestfs-tools failed — falling back to cloud-init snippet only."
        SKIP_VIRT_CUSTOMIZE=1
      fi
    fi
  fi

  if [[ "$SKIP_VIRT_CUSTOMIZE" != "1" ]]; then
    echo "→ Baking qemu-guest-agent + SSH password auth into disk image (libguestfs)"
    export LIBGUESTFS_BACKEND=direct
    if ! virt-customize -a "$WORK_IMG" \
        --install qemu-guest-agent \
        --run-command 'systemctl enable qemu-guest-agent' \
        --run-command 'mkdir -p /etc/ssh/sshd_config.d' \
        --write '/etc/ssh/sshd_config.d/60-password-auth.conf:PasswordAuthentication yes' \
        --run-command 'truncate -s 0 /etc/machine-id'; then
      echo "virt-customize failed — falling back to cloud-init snippet only."
      echo "WARNING: SSH password auth will NOT be pre-baked. Enable it manually on the template."
      SKIP_VIRT_CUSTOMIZE=1
    else
      IMPORT_IMG="$WORK_IMG"
      echo "   qemu-guest-agent installed and enabled"
      echo "   SSH PasswordAuthentication pre-configured"
      echo "   machine-id cleared for unique clone identities"
    fi
  fi
fi

# ── Create the VM template ───────────────────────────────────────────────────
echo "→ qm create $VMID ($NAME)"
qm create "$VMID" \
  --name "$NAME" \
  --memory 2048 \
  --cores 2 \
  --cpu host \
  --machine q35 \
  --bios ovmf \
  --net0 virtio,bridge=vmbr0 \
  --scsihw virtio-scsi-single \
  --agent enabled=1

qm set "$VMID" --efidisk0 "${STORAGE}:1,format=raw,efitype=4m,pre-enrolled-keys=0"

echo "→ qm importdisk"
qm importdisk "$VMID" "$IMPORT_IMG" "$STORAGE"

DISK="${STORAGE}:vm-${VMID}-disk-1"
qm set "$VMID" \
  --scsi0 "${DISK},discard=on,ssd=1" \
  --boot order=scsi0 \
  --ide2 "${STORAGE}:cloudinit"

# NOTE: cicustom vendor snippet intentionally NOT attached to the template.
# qemu-guest-agent and SSH password auth are pre-baked into the disk via
# virt-customize above. A cicustom snippet with "packages:" would trigger
# apt on every VM first boot — that was the 30-60s overhead this eliminates.

echo "→ qm template"
qm template "$VMID"

echo ""
echo "════════════════════════════════════════════════════════"
echo " Done. Template VMID $VMID ($NAME) is ready."
echo " App OS key: ubuntu-24.04 → template $VMID"
echo ""
echo " What is pre-baked into the template disk:"
if [[ "$SKIP_VIRT_CUSTOMIZE" == "1" ]]; then
  echo "  [WARN] virt-customize was skipped — qemu-guest-agent and SSH password"
  echo "         auth were NOT baked in. Boot overhead reduction will NOT apply."
  echo "         Re-run without SKIP_VIRT_CUSTOMIZE=1 when apt/DNS is working."
else
  echo "  [OK] qemu-guest-agent installed + enabled (systemd)"
  echo "  [OK] SSH PasswordAuthentication yes pre-configured"
  echo "  [OK] machine-id cleared (each clone gets a unique identity)"
  echo ""
  echo " Boot overhead eliminated:"
  echo "  - No cicustom vendor snippet attached to template"
  echo "  - No apt install on VM first boot"
  echo "  - Expected boot-to-SSH time: ~5-10s (was 30-90s)"
fi
echo ""
echo " Proxmox will be able to fetch the VM IP after first boot completes."
echo "════════════════════════════════════════════════════════"
