# Windows 11 Golden Image Setup

Before running the script you need to manually download the Windows 11 ISO and place it on the Proxmox node. The script cannot download it automatically because Microsoft blocks automated downloads.

---

## 1. Download the ISO

Go to this link and download the Windows 11 ISO:

https://www.microsoft.com/software-download/windows11

On that page scroll down to the section that says **Download Windows 11 Disk Image (ISO) for x64 devices**. Select Windows 11 multi-edition ISO, pick your language, and click the 64-bit download button. The file is around 6GB so it will take some time depending on your connection.

---

## 2. Rename the ISO

Once downloaded the file will have a name like `Win11_24H2_English_x64.iso`. Rename it to `Win11.iso` before copying it to the server.

On Linux or Mac:
```bash
mv Win11_24H2_English_x64.iso Win11.iso
```

On Windows just right-click the file and rename it to `Win11.iso`.

---

## 3. Copy the ISO to Proxmox

Copy the ISO to the Proxmox node using scp. Replace `192.168.0.200` with your actual Proxmox IP.

```bash
scp Win11.iso root@192.168.0.200:/var/lib/vz/template/iso/Win11.iso
```

Once copied SSH into the Proxmox node and confirm it is there:

```bash
ls -lh /var/lib/vz/template/iso/Win11.iso
```

You should see something like:
```
-rw-r--r-- 1 root root 6.2G ... /var/lib/vz/template/iso/Win11.iso
```

---

## 4. Copy the Script to Proxmox

```bash
scp create_golden_image_win11.sh root@192.168.0.200:/root/
```

---

## 5. Run the Script

SSH into the Proxmox node and run the script:

```bash
ssh root@192.168.0.200
chmod +x /root/create_golden_image_win11.sh
bash /root/create_golden_image_win11.sh
```

The script will detect the ISO automatically and skip the download. It will also download the VirtIO drivers ISO on its own so internet access is still needed for that part (~600MB). After that it creates the VM, sets up the hardware, and injects the unattended install configuration.

---

## 6. After the Script Finishes

The script only creates the VM. You still need to install Windows and convert it to a template manually.

**Start the VM:**
```bash
qm start 9001
```

Open the Proxmox web UI, click on VM 9001 and open the Console tab. Windows will install automatically without any input from you. This takes around 15 to 20 minutes on average.

**Run sysprep after Windows boots to desktop:**

Once you see the Windows desktop open Command Prompt as Administrator and run:
```
C:\Windows\System32\Sysprep\sysprep.exe /generalize /oobe /shutdown
```

The VM will shut down on its own after sysprep finishes. Wait for it to fully power off before the next step.

**Convert to template:**
```bash
qm template 9001
```

---

## Done

Your Windows 11 template is ready at VMID 9001. Every VM cloned from it will have Windows 11 installed with VirtIO drivers and the QEMU guest agent running at boot.

Credentials baked in:
- Username: `windows`
- Password: `verventech123`

Make sure these match your `.env` file when you run **only** Windows templates as the primary image:

```env
GOLDEN_IMAGE_VMID=9000
WINDOWS_TEMPLATE_VMID=9001
VM_DEFAULT_USERNAME=ubuntu
VM_DEFAULT_PASSWORD=your_linux_template_password
VM_WINDOWS_USERNAME=windows
VM_WINDOWS_PASSWORD=verventech123
```

If you use **both** Linux (9000) and Windows (9001) templates, keep `GOLDEN_IMAGE_VMID=9000` for Linux clones and set `WINDOWS_TEMPLATE_VMID=9001` for Windows. Set `VM_WINDOWS_*` to the logins baked into the Windows golden image.
