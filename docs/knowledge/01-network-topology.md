# Network Topology

> **⚠️ NEEDS REVIEW (2026-05-25)**: User clarified that Proxmox actually runs on a
> **separate physical server at 192.168.1.57** reached over **VPN** from the laptop —
> NOT nested inside Hyper-V on the laptop as this file previously assumed.
> The subnet table below describes the OLD/INCORRECT model. The `netsh portproxy`
> workaround may no longer be necessary depending on VPN routing for other devices.
> Re-verify before relying on anything here.

## Subnet Layout
| Network | Subnet | Purpose |
|---------|--------|---------|
| Host Wi-Fi (LAN) | 192.168.31.x | Laptop + phones + lab devices |
| Hyper-V VM Bridge | 192.168.1.x | Proxmox VMs internal network |
| Host IP on Wi-Fi | 192.168.31.157 | Laptop's LAN-facing address |
| Proxmox VM (ttyd) | 192.168.1.85 | Linux VM running ttyd on port 7681 |

## Key Constraint
Devices on 192.168.31.x **cannot** directly reach 192.168.1.x. The Hyper-V virtual switch creates an isolated bridge. Phones/tablets on Wi-Fi see 192.168.31.157 (the laptop) but NOT 192.168.1.85.

## Solution: Windows Port Proxy
`netsh interface portproxy add v4tov4 listenport=7681 listenaddress=0.0.0.0 connectport=7681 connectaddress=192.168.1.85`

This makes the laptop listen on 0.0.0.0:7681 and forward traffic to the VM at 192.168.1.85:7681.

## Firewall Rule
`netsh advfirewall firewall add rule name="ttyd-proxy" dir=in action=allow protocol=TCP localport=7681`

## Important Notes
- These rules are **persistent across reboots** on Windows
- Verify with: `netsh interface portproxy show all`
- If host IP changes (different Wi-Fi network), the proxy still works because it listens on 0.0.0.0
- For Guacamole (port 9080), Docker already exposes it on the host, so no extra proxy needed

## Related
- [[05-console-connectivity]] - How the frontend uses this proxy
- [[06-guacamole-integration]] - Guacamole uses Docker port mapping instead
