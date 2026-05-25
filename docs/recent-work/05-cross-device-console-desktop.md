# 05 — Cross-Device Console & Remote Desktop Access

**Commit:** `dcbffd9` · **Date:** 2026-05-25 · **Sprint:** 4
**Files:** `frontend/src/components/vm-detail/GuacamoleModal.tsx`, `ActionBar.tsx`, `ConsoleModal.tsx`, `VMDetailPage.tsx`, `backend/app/services/guacamole_client.py`

## The problem

When you opened a VM's **Remote Desktop** from your laptop it worked, because the backend returned a Guacamole URL like `http://localhost:9080/#/client/...`. But opening the same portal from a **phone or another LAN device**, `localhost` meant *that phone* — which isn't running Guacamole. So remote desktop was effectively desktop-only, even though the ttyd console already worked cross-device.

## Fix 1 (frontend) — Rewrite `localhost` to the host you're actually on

A small pure helper in `GuacamoleModal.tsx` rewrites the hostname of the returned client URL to whatever host the browser is currently talking to:

```tsx
function rewriteGuacUrl(raw: string): string {
  try {
    const u = new URL(raw);
    if (u.hostname === "localhost" || u.hostname === "127.0.0.1") {
      u.hostname = window.location.hostname;   // e.g. 192.168.31.157
    }
    return u.toString();
  } catch {
    return raw;   // if it isn't a parseable URL, pass through untouched
  }
}
```

It's applied at **both** places the client URL is set — the initial session load and the manual reconnect:

```tsx
const session = await createDesktopSession(jobId);
if (!cancelled) setClientUrl(rewriteGuacUrl(session.client_url));   // initial
...
setClientUrl(rewriteGuacUrl(session.client_url));                   // reconnect
```

### Why client-side rewrite (not server-side)

The server doesn't reliably know *which* of its addresses the client reached it on (it could be `localhost`, a LAN IP, a VPN IP, or an ngrok host). The browser **does** know — it's in `window.location.hostname`. Rewriting on the client means the Guacamole iframe is always loaded from the exact same origin the user typed, so it works identically on laptop, phone, or over the VPN. This mirrors how the ttyd console was already made cross-device.

## Fix 2 (frontend) — `showConsole` gate on the action bar

`ActionBar.tsx` gained a `showConsole?: boolean` prop so the Console button can be shown/hidden per VM (e.g. Linux gets ttyd console, Windows gets Guacamole desktop). The button is now wrapped in a conditional instead of always rendered:

```tsx
{showConsole && (
  <Button
    variant="secondary" size="sm" onClick={onConsole}
    disabled={!isRunning || !vmIP || isPending}
    title={!vmIP ? "IP not yet available" : !isRunning ? "VM must be running" : "Open web console (ttyd)"}
  >
    <TerminalSquare className="h-3.5 w-3.5" /> Console
  </Button>
)}
```

The existing `showRemoteDesktop` gate already handled the Guacamole button; `showConsole` brings symmetry so `VMDetailPage.tsx` controls which access methods each OS exposes.

## Fix 3 (backend) — Generalize RDP-only into RDP **or** SSH

The Guacamole client helper was Windows/RDP-only. It was renamed and parameterized so the same code path can create either an **RDP** (Windows) or an **SSH** (Linux) connection.

### `create_rdp_connection` → `create_connection(..., protocol="rdp")`

```python
def create_connection(
    token: str, data_source: str, *,
    connection_name: str, hostname: str, port: int,
    username: str, password: str,
    protocol: str = "rdp",        # NEW
) -> str:
    """Create an RDP or SSH connection and return its opaque identifier."""
    params = {
        "hostname": hostname, "port": str(port),
        "username": username, "password": password,
    }
    if protocol == "rdp":
        params.update({
            "ignore-cert": "true", "security": "nla",
            "disable-auth": "false", "enable-wallpaper": "false",
            "create-drive-path": "false",
        })
    elif protocol == "ssh":
        params.update({
            "color-scheme": "green-black",
            "server-alive-interval": "30",
        })

    payload = {
        "parentIdentifier": "ROOT", "name": connection_name,
        "protocol": protocol, "parameters": params, "attributes": {},
    }
    resp = _session().post(url, headers=_headers(token), json=payload, timeout=30)
    if resp.status_code not in (200, 201):
        raise GuacamoleAPIError(
            f"Guacamole could not create {protocol.upper()} connection ({resp.status_code})",
            status_code=502,
        )
    ...
```

The protocol-specific parameter blocks are the meaningful part: RDP needs `security=nla` and cert handling; SSH needs keepalive + a terminal colour scheme. The shared connection params (host/port/credentials) are built once and merged.

### `create_windows_desktop_session` → `create_desktop_session`

The higher-level session builder was renamed to drop the Windows-specific name, since it now serves Linux SSH desktops too. **Note:** this rename left one call site stale in `desktop_routes.py`, which became a latent 500 — see [06](06-vm-ip-credential-self-heal.md), bonus bug #2.

## Deployment note

The frontend is baked into its Docker image, so these changes required a `docker compose build frontend && docker compose up -d frontend`. The backend hot-reloads.

## Teaching summary

| | |
|---|---|
| **Problem** | Guacamole URL hard-coded `localhost`, unreachable from other LAN/VPN devices. |
| **Frontend fix** | `rewriteGuacUrl()` swaps `localhost`/`127.0.0.1` → `window.location.hostname`. |
| **UI fix** | `showConsole` prop gates the Console button (symmetry with `showRemoteDesktop`). |
| **Backend fix** | `create_connection(protocol=...)` supports RDP **and** SSH; session builder renamed generic. |
| **Why client-side** | Only the browser knows which host the user actually reached. |

See also journal `017-cross-device-desktop-access.md`, [`docs/knowledge/06-guacamole-integration.md`](../knowledge/06-guacamole-integration.md).
