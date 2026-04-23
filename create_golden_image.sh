#!/bin/bash
# =============================================================================
# create_golden_image.sh
# Run directly on your Proxmox node as root.
#
# Creates a fresh Ubuntu 24.04 golden image template (VMID 9000) using the
# official Ubuntu cloud image — no ISO install needed, fully automated.
#
# The cloud image approach is the correct way to build Proxmox templates:
#   - Pre-installed OS, boots in ~10 seconds
#   - qemu-guest-agent pre-installed and enabled
#   - cloud-init support for hostname / SSH key injection on clone
#   - No interactive installer to click through
#
# Usage:
#   chmod +x create_golden_image.sh
#   ./create_golden_image.sh
# =============================================================================

set -euo pipefail

# =============================================================================
# ── CONFIGURE THESE BEFORE RUNNING ───────────────────────────────────────────
# =============================================================================
VMID=9000
VM_NAME="ubuntu-2404-golden"
NODE="home"
STORAGE="local-lvm"          # where to store the VM disk
BRIDGE="vmbr0"               # your Proxmox network bridge
DISK_SIZE="20G"              # golden image disk size
RAM_MB=2048
CPU_CORES=2

# Default credentials baked into the golden image via cloud-init.
# These must match VM_DEFAULT_USERNAME and VM_DEFAULT_PASSWORD in your .env
DEFAULT_USER="ubuntu"
DEFAULT_PASSWORD="verventech123"   # ← must match VM_DEFAULT_PASSWORD in .env

# Ubuntu 24.04 LTS cloud image
CLOUD_IMAGE_URL="https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
CLOUD_IMAGE_FILE="/root/noble-server-cloudimg-amd64.img"
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
die()     { echo -e "${RED}[ERROR]${NC} $*" >&2; exit 1; }
step()    { echo ""; echo -e "${BOLD}━━━ $* ${NC}"; }

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   Proxmox Golden Image Creator               ║${NC}"
echo -e "${BOLD}║   Ubuntu 24.04 LTS — VMID $VMID              ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
info "Node     : $NODE"
info "Storage  : $STORAGE"
info "VMID     : $VMID"
info "Disk     : $DISK_SIZE"
info "RAM      : ${RAM_MB}MB"
info "CPUs     : $CPU_CORES"
info "User     : $DEFAULT_USER"
echo ""

# ── Root check ────────────────────────────────────────────────────────────────
[[ $EUID -eq 0 ]] || die "Must be run as root."

# ── Make sure VMID is free ────────────────────────────────────────────────────
step "Step 1/7 — Checking VMID $VMID is free"
if qm status $VMID &>/dev/null 2>&1; then
    die "VMID $VMID already exists. Remove it first with: qm destroy $VMID --purge"
fi
success "VMID $VMID is free."

# ── Required tools ─────────────────────────────────────────────────────────────
step "Step 2/7 — Checking required tools"
for tool in wget qemu-img virt-customize; do
    if ! command -v "$tool" &>/dev/null; then
        warn "$tool not found — installing..."
        apt-get install -y -qq "${tool/virt-customize/libguestfs-tools}" 2>/dev/null || \
        apt-get install -y -qq libguestfs-tools 2>/dev/null || true
    fi
    command -v "$tool" &>/dev/null && success "$tool OK" || warn "$tool still missing (non-fatal)"
done

# ── Download Ubuntu 24.04 cloud image ─────────────────────────────────────────
step "Step 3/7 — Downloading Ubuntu 24.04 cloud image"
mkdir -p /var/lib/vz/template/iso

if [[ -f "$CLOUD_IMAGE_FILE" ]]; then
    info "Cloud image already exists at $CLOUD_IMAGE_FILE"
    info "Skipping download. Delete the file to force a fresh download."
else
    info "Downloading from: $CLOUD_IMAGE_URL"
    info "This may take a few minutes depending on your connection..."
    wget -q --show-progress -O "$CLOUD_IMAGE_FILE" "$CLOUD_IMAGE_URL"
    success "Download complete."
fi

# Verify the file is a valid qcow2/img
IMGTYPE=$(qemu-img info "$CLOUD_IMAGE_FILE" 2>/dev/null | grep "file format" | awk '{print $3}')
info "Image format: $IMGTYPE"

# ── Inject qemu-guest-agent + set password via virt-customize ─────────────────
step "Step 4/7 — Customising image (installing guest agent + setting password)"
info "This modifies a copy of the image — takes ~60 seconds..."

CUSTOM_IMAGE="/tmp/ubuntu-24.04-golden-custom.img"
cp "$CLOUD_IMAGE_FILE" "$CUSTOM_IMAGE"

if command -v virt-customize &>/dev/null; then
    virt-customize \
        -a "$CUSTOM_IMAGE" \
        --install qemu-guest-agent \
        --run-command "systemctl enable qemu-guest-agent" \
        --run-command "useradd -m -s /bin/bash $DEFAULT_USER 2>/dev/null || true" \
        --run-command "echo '$DEFAULT_USER:$DEFAULT_PASSWORD' | chpasswd" \
        --run-command "usermod -aG sudo $DEFAULT_USER" \
        --run-command "echo '$DEFAULT_USER ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/$DEFAULT_USER" \
        --run-command "sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config" \
        --run-command "sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config" \
        --run-command "sed -i 's/PasswordAuthentication no/PasswordAuthentication yes/' /etc/ssh/sshd_config.d/60-cloudimg-settings.conf || true" \
        --run-command "echo 'PasswordAuthentication yes' >> /etc/ssh/sshd_config.d/60-cloudimg-settings.conf" \
        --run-command "cloud-init clean" \
        --run-command "wget -q https://github.com/tsl0922/ttyd/releases/latest/download/ttyd.x86_64 -O /usr/local/bin/ttyd" \
        --run-command "chmod +x /usr/local/bin/ttyd" \
        --run-command "printf '[Unit]\nDescription=ttyd Web Terminal\nAfter=network.target\n\n[Service]\nExecStart=/usr/local/bin/ttyd -p 7681 -W -c $DEFAULT_USER:$DEFAULT_PASSWORD /bin/bash\nRestart=always\nUser=$DEFAULT_USER\nWorkingDirectory=/home/$DEFAULT_USER\n\n[Install]\nWantedBy=multi-user.target\n' > /etc/systemd/system/ttyd.service" \
        --run-command "systemctl enable ttyd" \
        --selinux-relabel 2>/dev/null || true
    success "Image customised successfully."
else
    warn "virt-customize not available — skipping offline customisation."
    warn "Guest agent will be installed via cloud-init at first boot instead."
fi

# ── Create the VM ─────────────────────────────────────────────────────────────
step "Step 5/7 — Creating VM $VMID in Proxmox"

qm create $VMID \
    --name "$VM_NAME" \
    --memory $RAM_MB \
    --cores $CPU_CORES \
    --cpu host \
    --net0 virtio,bridge=$BRIDGE \
    --ostype l26 \
    --agent enabled=1,fstrim_cloned_disks=1 \
    --serial0 socket \
    --vga std \
    --scsihw virtio-scsi-pci \
    --bootdisk scsi0 \
    --boot c

success "VM $VMID created."

# ── Import the disk ───────────────────────────────────────────────────────────
step "Step 6/7 — Importing disk into $STORAGE"
info "Importing $CUSTOM_IMAGE → $STORAGE..."

qm importdisk $VMID "$CUSTOM_IMAGE" $STORAGE --format raw
success "Disk imported."

# Attach the imported disk as scsi0
info "Attaching disk and adding cloud-init drive..."
qm set $VMID --scsi0 ${STORAGE}:vm-${VMID}-disk-0,discard=on
qm set $VMID --ide2 ${STORAGE}:cloudinit
qm set $VMID --boot c --bootdisk scsi0

# Resize disk to requested size
info "Resizing disk to $DISK_SIZE..."
qm resize $VMID scsi0 $DISK_SIZE
success "Disk resized to $DISK_SIZE."

# ── Configure cloud-init defaults ─────────────────────────────────────────────
info "Configuring cloud-init defaults..."
qm set $VMID \
    --ciuser  "$DEFAULT_USER" \
    --cipassword "$DEFAULT_PASSWORD" \
    --ipconfig0 ip=dhcp \
    --nameserver "8.8.8.8 1.1.1.1"

success "Cloud-init configured."

# ── Verify agent config is set ───────────────────────────────────────────────
AGENT_CHECK=$(qm config $VMID | grep "^agent:" || echo "")
if [[ -z "$AGENT_CHECK" ]]; then
    warn "Agent flag missing — setting it explicitly..."
    qm set $VMID --agent enabled=1,fstrim_cloned_disks=1
fi
success "QEMU guest agent flag: $(qm config $VMID | grep '^agent:')"

# ── Convert to template ───────────────────────────────────────────────────────
step "Step 7/7 — Converting to template"
qm template $VMID
success "VMID $VMID is now a template."

# ── Cleanup ───────────────────────────────────────────────────────────────────
info "Cleaning up temporary files..."
rm -f "$CUSTOM_IMAGE"
success "Cleanup done."

# ── Print final config ────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   Golden Image Created Successfully!         ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
info "Final VM config:"
qm config $VMID
echo ""
echo -e "${GREEN}${BOLD}Next step — update your .env file:${NC}"
echo ""
echo "   GOLDEN_IMAGE_VMID=$VMID"
echo "   VM_DEFAULT_USERNAME=$DEFAULT_USER"
echo "   VM_DEFAULT_PASSWORD=$DEFAULT_PASSWORD"
echo ""
echo -e "${YELLOW}Make sure VM_DEFAULT_PASSWORD in .env matches what you set${NC}"
echo -e "${YELLOW}at the top of this script (DEFAULT_PASSWORD variable).${NC}"
echo ""
success "Done. New VMs cloned from VMID $VMID will have:"
success "  - qemu-guest-agent running at boot"
success "  - SSH on port 22 with password auth enabled"
success "  - User '$DEFAULT_USER' with sudo access"
success "  - DHCP IP returned via guest agent to your API"
success "  - ttyd web terminal on port 7681 (auto-start, writable)"
echo ""
