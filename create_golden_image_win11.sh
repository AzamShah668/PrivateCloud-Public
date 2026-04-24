#!/bin/bash
# =============================================================================
# create_golden_image_win11.sh
# Run directly on your Proxmox node as root.
#
# Creates a Windows 11 golden image template (VMID 9001) on Proxmox.
#
# What this script does:
#   - Auto-downloads Windows 11 ISO from Microsoft via Mido (if not present)
#   - Auto-downloads VirtIO drivers ISO (if not present)
#   - Creates a VM with correct Windows 11 hardware (UEFI, TPM 2.0, SecureBoot)
#   - Injects an autounattend.xml via floppy to automate Windows installation
#   - Bakes in the default username & password
#   - Installs QEMU guest agent automatically during Windows setup
#
# Prerequisites:
#   - Run this script as root on the Proxmox node
#   - Internet access required (~6GB Windows 11 ISO downloaded from Microsoft)
#
# Usage:
#   chmod +x create_golden_image_win11.sh
#   ./create_golden_image_win11.sh
# =============================================================================

set -euo pipefail

# =============================================================================
# ── CONFIGURE THESE BEFORE RUNNING ───────────────────────────────────────────
# =============================================================================
VMID=9001
VM_NAME="win11-golden"
NODE="home"
STORAGE="local-lvm"          # where to store the VM disk
BRIDGE="vmbr0"               # your Proxmox network bridge
DISK_SIZE="64G"              # Windows 11 needs at least 64G
RAM_MB=4096                  # Windows 11 minimum is 4096 MB
CPU_CORES=2

# Default credentials baked into Windows via autounattend.xml
# These must match VM_DEFAULT_USERNAME and VM_DEFAULT_PASSWORD in your .env
DEFAULT_USER="windows"
DEFAULT_PASSWORD="verventech123"   # ← must match VM_DEFAULT_PASSWORD in .env

# ISO storage paths
ISO_DIR="/var/lib/vz/template/iso"
WIN11_ISO="${ISO_DIR}/Win11.iso"
VIRTIO_ISO="${ISO_DIR}/virtio-win.iso"
VIRTIO_ISO_URL="https://fedorapeople.org/groups/virt/virtio-win/direct-downloads/stable-virtio/virtio-win.iso"

# Mido — downloads Windows ISOs directly from Microsoft
MIDO_URL="https://raw.githubusercontent.com/ElliotKillick/Mido/main/Mido.sh"
MIDO_SCRIPT="/tmp/Mido.sh"

# Floppy image that carries autounattend.xml into the Windows installer
FLOPPY_IMG="/tmp/autounattend.img"
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
echo -e "${BOLD}║   Windows 11 — VMID $VMID                    ║${NC}"
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
step "Step 1/8 — Checking VMID $VMID is free"
if qm status $VMID &>/dev/null 2>&1; then
    die "VMID $VMID already exists. Remove it first with: qm destroy $VMID --purge"
fi
success "VMID $VMID is free."

# ── Required tools ────────────────────────────────────────────────────────────
step "Step 2/8 — Checking required tools"
apt-get update -qq 2>/dev/null || true
for tool in wget curl mkdosfs mcopy; do
    if ! command -v "$tool" &>/dev/null; then
        warn "$tool not found — installing..."
        apt-get install -y -qq dosfstools mtools curl wget 2>/dev/null || true
    fi
    command -v "$tool" &>/dev/null && success "$tool OK" || warn "$tool still missing (non-fatal)"
done
mkdir -p "$ISO_DIR"

# ── Download Windows 11 ISO via Mido ─────────────────────────────────────────
step "Step 3/8 — Windows 11 ISO"
if [[ -f "$WIN11_ISO" ]]; then
    info "Windows 11 ISO already exists at $WIN11_ISO — skipping download."
    success "Windows 11 ISO found."
else
    info "Windows 11 ISO not found — downloading from Microsoft via Mido..."
    info "Mido downloads directly from Microsoft's official servers."
    info "This will download ~6GB — please be patient..."
    echo ""

    # Download Mido script
    if ! curl -fsSL "$MIDO_URL" -o "$MIDO_SCRIPT" 2>/dev/null; then
        die "Failed to download Mido. Check your internet connection.\nURL: $MIDO_URL"
    fi
    chmod +x "$MIDO_SCRIPT"
    success "Mido downloaded."

    # Run Mido to download Windows 11 — outputs to current directory
    # so we cd to ISO_DIR first then move the file
    cd "$ISO_DIR"
    bash "$MIDO_SCRIPT" win11x64 || die "Mido failed to download Windows 11 ISO.\nCheck your internet connection and try again."
    cd - > /dev/null

    # Mido saves as win11x64.iso — rename to Win11.iso
    if [[ -f "${ISO_DIR}/win11x64.iso" ]]; then
        mv "${ISO_DIR}/win11x64.iso" "$WIN11_ISO"
        success "Windows 11 ISO downloaded and saved as $WIN11_ISO"
    elif [[ -f "${ISO_DIR}/Win11.iso" ]]; then
        success "Windows 11 ISO already named correctly: $WIN11_ISO"
    else
        die "Mido ran but ISO file not found in $ISO_DIR. Check disk space and try again."
    fi

    rm -f "$MIDO_SCRIPT"
fi

# ── Download VirtIO drivers ISO ───────────────────────────────────────────────
step "Step 4/8 — VirtIO drivers ISO"
if [[ -f "$VIRTIO_ISO" ]]; then
    info "VirtIO ISO already exists at $VIRTIO_ISO — skipping download."
    success "VirtIO ISO found."
else
    info "Downloading VirtIO drivers ISO..."
    info "This may take a few minutes..."
    wget -q --show-progress -O "$VIRTIO_ISO" "$VIRTIO_ISO_URL" \
        || die "Failed to download VirtIO ISO. Check your internet connection."
    success "VirtIO ISO downloaded: $VIRTIO_ISO"
fi

# ── Create autounattend.xml floppy image ──────────────────────────────────────
step "Step 5/8 — Creating autounattend.xml floppy image"
info "Building unattended Windows install answer file..."

# Create a 1.44MB FAT floppy image
dd if=/dev/zero of="$FLOPPY_IMG" bs=1024 count=1440 2>/dev/null
mkdosfs "$FLOPPY_IMG" 2>/dev/null
success "Floppy image created."

# Write autounattend.xml to a temp file first (avoids heredoc variable issues)
cat > /tmp/autounattend.xml << XMLEOF
<?xml version="1.0" encoding="utf-8"?>
<unattend xmlns="urn:schemas-microsoft-com:unattend">

  <!-- ═══════════════════════════════════════════════════
       Windows PE phase
       - Load VirtIO storage drivers so installer sees the disk
       - Bypass TPM/SecureBoot/RAM checks for VM
       - Partition and format the disk
       ═══════════════════════════════════════════════════ -->
  <settings pass="windowsPE">

    <component name="Microsoft-Windows-PnpCustomizationsWinPE"
               processorArchitecture="amd64"
               publicKeyToken="31bf3856ad364e35"
               language="neutral"
               versionScope="nonSxS"
               xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
      <DriverPaths>
        <PathAndCredentials wcm:action="add" wcm:keyValue="1">
          <Path>E:\vioscsi\w11\amd64</Path>
        </PathAndCredentials>
        <PathAndCredentials wcm:action="add" wcm:keyValue="2">
          <Path>E:\NetKVM\w11\amd64</Path>
        </PathAndCredentials>
        <PathAndCredentials wcm:action="add" wcm:keyValue="3">
          <Path>E:\Balloon\w11\amd64</Path>
        </PathAndCredentials>
      </DriverPaths>
    </component>

    <component name="Microsoft-Windows-Setup"
               processorArchitecture="amd64"
               publicKeyToken="31bf3856ad364e35"
               language="neutral"
               versionScope="nonSxS"
               xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">

      <RunSynchronous>
        <RunSynchronousCommand wcm:action="add">
          <Order>1</Order>
          <Path>reg add "HKLM\SYSTEM\Setup\LabConfig" /v BypassTPMCheck /t REG_DWORD /d 1 /f</Path>
        </RunSynchronousCommand>
        <RunSynchronousCommand wcm:action="add">
          <Order>2</Order>
          <Path>reg add "HKLM\SYSTEM\Setup\LabConfig" /v BypassSecureBootCheck /t REG_DWORD /d 1 /f</Path>
        </RunSynchronousCommand>
        <RunSynchronousCommand wcm:action="add">
          <Order>3</Order>
          <Path>reg add "HKLM\SYSTEM\Setup\LabConfig" /v BypassRAMCheck /t REG_DWORD /d 1 /f</Path>
        </RunSynchronousCommand>
      </RunSynchronous>

      <DiskConfiguration>
        <Disk wcm:action="add">
          <DiskID>0</DiskID>
          <WillWipeDisk>true</WillWipeDisk>
          <CreatePartitions>
            <CreatePartition wcm:action="add">
              <Order>1</Order>
              <Type>EFI</Type>
              <Size>260</Size>
            </CreatePartition>
            <CreatePartition wcm:action="add">
              <Order>2</Order>
              <Type>MSR</Type>
              <Size>16</Size>
            </CreatePartition>
            <CreatePartition wcm:action="add">
              <Order>3</Order>
              <Type>Primary</Type>
              <Extend>true</Extend>
            </CreatePartition>
          </CreatePartitions>
          <ModifyPartitions>
            <ModifyPartition wcm:action="add">
              <Order>1</Order>
              <PartitionID>1</PartitionID>
              <Format>FAT32</Format>
              <Label>System</Label>
            </ModifyPartition>
            <ModifyPartition wcm:action="add">
              <Order>2</Order>
              <PartitionID>2</PartitionID>
            </ModifyPartition>
            <ModifyPartition wcm:action="add">
              <Order>3</Order>
              <PartitionID>3</PartitionID>
              <Format>NTFS</Format>
              <Label>Windows</Label>
              <Letter>C</Letter>
            </ModifyPartition>
          </ModifyPartitions>
        </Disk>
      </DiskConfiguration>

      <ImageInstall>
        <OSImage>
          <InstallTo>
            <DiskID>0</DiskID>
            <PartitionID>3</PartitionID>
          </InstallTo>
          <WillShowUI>OnError</WillShowUI>
        </OSImage>
      </ImageInstall>

      <UserData>
        <AcceptEula>true</AcceptEula>
        <FullName>WINUSER</FullName>
        <Organization>verventech</Organization>
      </UserData>

    </component>
  </settings>

  <!-- ═══════════════════════════════════════════════════
       Specialize phase — set computer name + timezone
       ═══════════════════════════════════════════════════ -->
  <settings pass="specialize">
    <component name="Microsoft-Windows-Shell-Setup"
               processorArchitecture="amd64"
               publicKeyToken="31bf3856ad364e35"
               language="neutral"
               versionScope="nonSxS"
               xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
      <ComputerName>*</ComputerName>
      <TimeZone>UTC</TimeZone>
    </component>
  </settings>

  <!-- ═══════════════════════════════════════════════════
       OOBE phase
       - Create local user with baked-in credentials
       - Skip Microsoft account prompts
       - Install QEMU guest agent from VirtIO ISO
       ═══════════════════════════════════════════════════ -->
  <settings pass="oobeSystem">

    <component name="Microsoft-Windows-Shell-Setup"
               processorArchitecture="amd64"
               publicKeyToken="31bf3856ad364e35"
               language="neutral"
               versionScope="nonSxS"
               xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">

      <OOBE>
        <HideEULAPage>true</HideEULAPage>
        <HideLocalAccountScreen>false</HideLocalAccountScreen>
        <HideOnlineAccountScreens>true</HideOnlineAccountScreens>
        <HideWirelessSetupInOOBE>true</HideWirelessSetupInOOBE>
        <SkipMachineOOBE>true</SkipMachineOOBE>
        <SkipUserOOBE>true</SkipUserOOBE>
        <ProtectYourPC>3</ProtectYourPC>
      </OOBE>

      <UserAccounts>
        <LocalAccounts>
          <LocalAccount wcm:action="add">
            <Name>WINUSER</Name>
            <DisplayName>WINUSER</DisplayName>
            <Password>
              <Value>WINPASSWORD</Value>
              <PlainText>true</PlainText>
            </Password>
            <Group>Administrators</Group>
          </LocalAccount>
        </LocalAccounts>
      </UserAccounts>

      <AutoLogon>
        <Username>WINUSER</Username>
        <Password>
          <Value>WINPASSWORD</Value>
          <PlainText>true</PlainText>
        </Password>
        <LogonCount>1</LogonCount>
        <Enabled>true</Enabled>
      </AutoLogon>

      <FirstLogonCommands>
        <SynchronousCommand wcm:action="add">
          <Order>1</Order>
          <CommandLine>cmd /c "E:\guest-agent\qemu-ga-x86_64.msi /quiet /norestart"</CommandLine>
          <Description>Install QEMU Guest Agent</Description>
          <RequiresUserInput>false</RequiresUserInput>
        </SynchronousCommand>
        <SynchronousCommand wcm:action="add">
          <Order>2</Order>
          <CommandLine>cmd /c "sc config QEMU-GA start= auto"</CommandLine>
          <Description>Set QEMU Guest Agent to auto-start</Description>
          <RequiresUserInput>false</RequiresUserInput>
        </SynchronousCommand>
        <SynchronousCommand wcm:action="add">
          <Order>3</Order>
          <CommandLine>cmd /c "net start QEMU-GA"</CommandLine>
          <Description>Start QEMU Guest Agent</Description>
          <RequiresUserInput>false</RequiresUserInput>
        </SynchronousCommand>
      </FirstLogonCommands>

    </component>

    <component name="Microsoft-Windows-International-Core"
               processorArchitecture="amd64"
               publicKeyToken="31bf3856ad364e35"
               language="neutral"
               versionScope="nonSxS"
               xmlns:wcm="http://schemas.microsoft.com/WMIConfig/2002/State">
      <InputLocale>en-US</InputLocale>
      <SystemLocale>en-US</SystemLocale>
      <UILanguage>en-US</UILanguage>
      <UserLocale>en-US</UserLocale>
    </component>

  </settings>

</unattend>
XMLEOF

# Substitute actual credentials into the XML (avoids heredoc variable expansion issues)
sed -i "s/WINUSER/${DEFAULT_USER}/g" /tmp/autounattend.xml
sed -i "s/WINPASSWORD/${DEFAULT_PASSWORD}/g" /tmp/autounattend.xml

# Write the XML into the floppy image
mcopy -i "$FLOPPY_IMG" /tmp/autounattend.xml ::autounattend.xml
rm -f /tmp/autounattend.xml

# Save floppy to ISO storage so Proxmox can attach it
cp "$FLOPPY_IMG" "${ISO_DIR}/autounattend.img"
success "autounattend.xml written to floppy image."
success "Floppy saved to ${ISO_DIR}/autounattend.img"

# ── Create the VM ─────────────────────────────────────────────────────────────
step "Step 6/8 — Creating Windows 11 VM $VMID in Proxmox"

qm create $VMID \
    --name "$VM_NAME" \
    --memory $RAM_MB \
    --cores $CPU_CORES \
    --cpu host \
    --net0 virtio,bridge=$BRIDGE \
    --ostype win11 \
    --agent enabled=1,fstrim_cloned_disks=1 \
    --machine q35 \
    --bios ovmf \
    --scsihw virtio-scsi-pci \
    --tpmstate0 ${STORAGE}:4,version=v2.0 \
    --efidisk0 ${STORAGE}:1,efitype=4m,pre-enrolled-keys=1 \
    --vga std \
    --ide0 local:iso/Win11.iso,media=cdrom \
    --ide1 local:iso/virtio-win.iso,media=cdrom \
    --ide2 local:iso/autounattend.img,media=cdrom

success "VM $VMID created."

# ── Create and attach main disk ───────────────────────────────────────────────
step "Step 7/8 — Creating and attaching disk"
info "Creating ${DISK_SIZE} disk in ${STORAGE}..."

qm set $VMID --scsi0 ${STORAGE}:${DISK_SIZE},discard=on,ssd=1
success "Disk created and attached."

# Boot from Windows ISO first, then disk
qm set $VMID --boot order="ide0;scsi0"
success "Boot order set: Windows ISO → Disk"

# ── Verify agent config is set ────────────────────────────────────────────────
AGENT_CHECK=$(qm config $VMID | grep "^agent:" || echo "")
if [[ -z "$AGENT_CHECK" ]]; then
    warn "Agent flag missing — setting it explicitly..."
    qm set $VMID --agent enabled=1,fstrim_cloned_disks=1
fi
success "QEMU guest agent flag: $(qm config $VMID | grep '^agent:')"

# ── Cleanup temp files ────────────────────────────────────────────────────────
info "Cleaning up temporary files..."
rm -f "$FLOPPY_IMG"
success "Cleanup done."

# ── Print final config + next steps ──────────────────────────────────────────
step "Step 8/8 — Done!"

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║   Windows 11 VM Created Successfully!        ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════╝${NC}"
echo ""
info "Final VM config:"
qm config $VMID
echo ""

echo -e "${YELLOW}${BOLD}⚠️  IMPORTANT — 3 manual steps required after this:${NC}"
echo ""
echo "  1. Start the VM and let Windows install automatically:"
echo "     qm start $VMID"
echo "     (Open Proxmox noVNC console to watch — takes ~15-20 minutes)"
echo ""
echo "  2. Once Windows boots to desktop, run sysprep to generalise:"
echo "     C:\Windows\System32\Sysprep\sysprep.exe /generalize /oobe /shutdown"
echo "     (VM will shut down automatically after sysprep)"
echo ""
echo "  3. Convert to template:"
echo "     qm template $VMID"
echo ""
echo "  Optional — remove ISOs to save space after templating:"
echo "     qm set $VMID --delete ide0,ide1,ide2"
echo ""
echo -e "${GREEN}${BOLD}Credentials baked in:${NC}"
echo "   Username : $DEFAULT_USER"
echo "   Password : $DEFAULT_PASSWORD"
echo ""
echo -e "${GREEN}${BOLD}Update your .env file:${NC}"
echo "   GOLDEN_IMAGE_VMID=$VMID"
echo "   VM_DEFAULT_USERNAME=$DEFAULT_USER"
echo "   VM_DEFAULT_PASSWORD=$DEFAULT_PASSWORD"
echo ""
success "Done. After sysprep + qm template, VMs cloned from VMID $VMID will have:"
success "  - Windows 11 with user '$DEFAULT_USER' and baked-in password"
success "  - QEMU guest agent running at boot (IP reported to your API)"
success "  - VirtIO drivers installed (disk + network + balloon)"
echo ""
