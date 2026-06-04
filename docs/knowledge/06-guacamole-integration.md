# Guacamole Integration (RDP/SSH)

## Architecture
- **guacd**: Protocol proxy daemon (converts RDP/SSH -> Guacamole protocol)
- **guacamole**: Java web app (HTML5 client + REST API, port 9080 external, 8080 internal)
- **mysql-guacamole**: Auth + connection metadata storage

## How Desktop Sessions Work
1. Frontend calls `POST /api/desktop/{job_id}/session`
2. Backend (desktop_routes.py) calls guacamole_client.py
3. guacamole_client.py:
   - Authenticates with Guacamole REST API (guacadmin)
   - Deletes stale connections for this job
   - Creates a new RDP connection (hostname=VM IP, port=3389, credentials)
   - Builds a client URL with auth token baked in
4. Returns `{ client_url, connection_name, data_source }`
5. Frontend loads client_url in an iframe

## The Cross-Device Problem (same as console)
Backend env: `GUACAMOLE_PUBLIC_URL=http://localhost:9080/guacamole`
This means client_url = `http://localhost:9080/guacamole/#/client/xxx?token=yyy`
On a phone, localhost = the phone itself. Fails.

## Solution: Frontend URL Rewriting
`GuacamoleModal.tsx` has a `rewriteGuacUrl()` function:
- Takes the raw URL from backend
- If hostname is localhost or 127.0.0.1, replaces with window.location.hostname
- Result: phone hits 192.168.31.157:9080 which Docker exposes directly

## Key Files
- `backend/app/services/guacamole_client.py` - REST API client (auth, CRUD connections, URL builder)
- `backend/app/routes/desktop_routes.py` - API endpoint
- `frontend/src/components/vm-detail/GuacamoleModal.tsx` - UI + URL rewriting
- `frontend/src/api/vms.ts` - createDesktopSession() API call

## Environment Variables
- GUACAMOLE_API_URL: http://guacamole:8080/guacamole (Docker internal)
- GUACAMOLE_PUBLIC_URL: http://localhost:9080/guacamole (browser-facing base)
- GUACAMOLE_ADMIN_USER: guacadmin
- GUACAMOLE_ADMIN_PASSWORD: from .env

## Related
- [[01-network-topology]] - Why localhost fails from phones
- [[04-frontend-architecture]] - GuacamoleModal component
- [[05-console-connectivity]] - Same pattern used for ttyd
