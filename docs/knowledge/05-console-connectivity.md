# Console Connectivity (ttyd)

## What is ttyd?
A terminal emulator that runs as a web server. Exposes a Linux shell via HTTP on port 7681.
Runs inside the Proxmox VM at 192.168.1.85:7681.

## The Cross-Device Problem
Phones on Wi-Fi (192.168.31.x) cannot reach the VM's internal IP (192.168.1.x).
The old code hardcoded `http://192.168.1.85:7681` which only worked from the host machine.

## Solution (Two Parts)

### 1. Network Layer (Windows host)
Port proxy forwards laptop:7681 -> VM:7681
See [[01-network-topology]] for the exact commands.

### 2. Frontend Layer (ConsoleModal.tsx)
Changed from: `const consoleURL = 'http://192.168.1.85:7681'`
Changed to: `const consoleURL = 'http://' + window.location.hostname + ':7681'`

This way:
- From laptop browser: hostname = localhost or 192.168.31.157 -> works
- From phone browser: hostname = 192.168.31.157 -> hits portproxy -> forwarded to VM

## Mobile Browser Gotcha
Mobile browsers block HTTP Basic Auth popups inside iframes.
ttyd requires authentication (username/password prompt).
**Solution**: The ConsoleModal has an 'Open in Tab' button that opens the URL in a new tab, where auth works normally.

## Credentials
- Username: verventech (or whatever the VM's Linux user is)
- Password: set during VM provisioning

## Related
- [[01-network-topology]] - Port proxy setup
- [[04-frontend-architecture]] - ConsoleModal component details
