# =============================================================================
# backend/app/services/guacamole_client.py
# =============================================================================
# Thin client for the Apache Guacamole REST API (MySQL auth backend).
# Used to mint short-lived browser sessions (RDP) for Windows VMs.
# =============================================================================

from __future__ import annotations

import base64
import logging
import os
import uuid
from typing import Any, Dict, List
from urllib.parse import quote

import requests

logger = logging.getLogger(__name__)


class GuacamoleConfigurationError(Exception):
    """Raised when Guacamole integration is disabled or misconfigured."""


class GuacamoleAPIError(Exception):
    """Raised when Guacamole returns an unexpected HTTP status or body."""

    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message)
        self.status_code = status_code


def _b64url_client_id(data_source: str, connection_id: str) -> str:
    """
    Build the opaque client path segment for /#/client/{id}?token=...

    Must match Apache Guacamole's ClientIdentifier.toString() (see
    guacamole/src/main/frontend/src/app/navigation/types/ClientIdentifier.js):
    base64url( connection_id + NUL + type + NUL + data_source )
    where type is the literal 'c' (CONNECTION).
    """
    inner = "\0".join([str(connection_id), "c", str(data_source)])
    raw = inner.encode("utf-8")
    # Standard base64, then translate to unpadded base64url (same as Guacamole JS)
    b = base64.b64encode(raw).decode("ascii")
    return b.replace("+", "-").replace("/", "_").replace("=", "")


def _api_base() -> str:
    base = os.getenv("GUACAMOLE_API_URL", "").rstrip("/")
    if not base:
        raise GuacamoleConfigurationError(
            "GUACAMOLE_API_URL is not set (e.g. http://guacamole:8080/guacamole)"
        )
    return base


def _public_base() -> str:
    base = os.getenv("GUACAMOLE_PUBLIC_URL", "").rstrip("/")
    if not base:
        raise GuacamoleConfigurationError(
            "GUACAMOLE_PUBLIC_URL is not set (browser-reachable base, e.g. http://localhost:9080/guacamole)"
        )
    return base


def _admin_user() -> str:
    return os.getenv("GUACAMOLE_ADMIN_USER", "guacadmin")


def _admin_password() -> str:
    return os.getenv("GUACAMOLE_ADMIN_PASSWORD", "guacadmin")


def _mysql_datasource() -> str:
    """JDBC MySQL auth extension data source key used in REST paths."""
    return os.getenv("GUACAMOLE_DATASOURCE", "mysql")


def _session(timeout: int = 30) -> requests.Session:
    s = requests.Session()
    s.verify = os.getenv("GUACAMOLE_TLS_VERIFY", "true").lower() == "true"
    return s


def obtain_auth_token() -> tuple[str, str]:
    """
    Log in to Guacamole as the API admin user.

    Returns:
        (auth_token, data_source) e.g. ("...", "mysql")
    """
    base = _api_base()
    url = f"{base}/api/tokens"
    resp = _session().post(
        url,
        data={"username": _admin_user(), "password": _admin_password()},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if resp.status_code != 200:
        logger.error("Guacamole token request failed: %s %s", resp.status_code, resp.text[:500])
        raise GuacamoleAPIError(
            f"Guacamole authentication failed ({resp.status_code})",
            status_code=502,
        )
    body = resp.json()
    token = body.get("authToken")
    data_source = body.get("dataSource") or _mysql_datasource()
    if not token:
        raise GuacamoleAPIError("Guacamole token response missing authToken", status_code=502)
    return str(token), str(data_source)


def _headers(token: str) -> Dict[str, str]:
    return {
        "Guacamole-Token": token,
        "Content-Type": "application/json",
    }


def _collect_connections(node: Dict[str, Any], out: List[Dict[str, Any]]) -> None:
    for c in node.get("childConnections") or []:
        out.append(c)
    for g in node.get("childGroups") or []:
        _collect_connections(g, out)


def list_all_connections(token: str, data_source: str) -> List[Dict[str, Any]]:
    base = _api_base()
    url = f"{base}/api/session/data/{data_source}/connectionGroups/ROOT/tree"
    resp = _session().get(url, headers=_headers(token), timeout=60)
    if resp.status_code != 200:
        raise GuacamoleAPIError(
            f"Guacamole tree listing failed ({resp.status_code})",
            status_code=502,
        )
    tree = resp.json()
    conns: List[Dict[str, Any]] = []
    _collect_connections(tree, conns)
    return conns


def delete_connection(token: str, data_source: str, identifier: str) -> None:
    base = _api_base()
    safe_id = quote(identifier, safe="")
    url = f"{base}/api/session/data/{data_source}/connections/{safe_id}"
    resp = _session().delete(url, headers=_headers(token), timeout=30)
    if resp.status_code not in (200, 204):
        logger.warning(
            "Guacamole delete connection %s failed: %s %s",
            identifier,
            resp.status_code,
            resp.text[:300],
        )


def delete_stale_privatecloud_connections(token: str, data_source: str, job_id: int) -> None:
    """Remove prior auto-created connections for this job (name prefix pc-job-{id}-)."""
    prefix = f"pc-job-{job_id}-"
    try:
        for c in list_all_connections(token, data_source):
            name = c.get("name") or ""
            ident = c.get("identifier")
            if ident and name.startswith(prefix):
                delete_connection(token, data_source, str(ident))
    except GuacamoleAPIError:
        raise
    except Exception as exc:
        logger.warning("Could not prune stale Guacamole connections: %s", exc)


def create_rdp_connection(
    token: str,
    data_source: str,
    *,
    connection_name: str,
    hostname: str,
    port: int,
    username: str,
    password: str,
) -> str:
    """
    Create an RDP connection and return its opaque identifier (for client URL / deletes).
    """
    base = _api_base()
    url = f"{base}/api/session/data/{data_source}/connections"
    payload: Dict[str, Any] = {
        "parentIdentifier": "ROOT",
        "name": connection_name,
        "protocol": "rdp",
        "parameters": {
            "hostname": hostname,
            "port": str(port),
            "username": username,
            "password": password,
            "ignore-cert": "true",
            "security": "nla",
            "disable-auth": "false",
            "enable-wallpaper": "false",
            "create-drive-path": "false",
        },
        "attributes": {},
    }
    resp = _session().post(url, headers=_headers(token), json=payload, timeout=30)
    if resp.status_code != 200:
        logger.error(
            "Guacamole create connection failed: %s %s",
            resp.status_code,
            resp.text[:800],
        )
        raise GuacamoleAPIError(
            f"Guacamole could not create RDP connection ({resp.status_code})",
            status_code=502,
        )
    body = resp.json()
    ident = body.get("identifier")
    if not ident:
        raise GuacamoleAPIError("Guacamole create response missing identifier", status_code=502)
    return str(ident)


def build_desktop_client_url(auth_token: str, data_source: str, connection_identifier: str) -> str:
    """Full URL to load the HTML5 RDP client (fragment + token query)."""
    public = _public_base()
    enc = _b64url_client_id(data_source, connection_identifier)
    tok = quote(auth_token, safe="")
    return f"{public}/#/client/{enc}?token={tok}"


def create_windows_desktop_session(
    *,
    job_id: int,
    vm_ip: str,
    vm_username: str,
    vm_password: str,
    rdp_port: int = 3389,
) -> Dict[str, str]:
    """
    Prune old connections for this job, create a fresh RDP connection, return URLs.

    Returns dict with keys: client_url, connection_name, data_source
    """
    token, data_source = obtain_auth_token()
    delete_stale_privatecloud_connections(token, data_source, job_id)

    suffix = uuid.uuid4().hex[:10]
    name = f"pc-job-{job_id}-{suffix}"
    conn_id = create_rdp_connection(
        token,
        data_source,
        connection_name=name,
        hostname=vm_ip,
        port=rdp_port,
        username=vm_username,
        password=vm_password,
    )
    client_url = build_desktop_client_url(token, data_source, conn_id)
    return {
        "client_url": client_url,
        "connection_name": name,
        "data_source": data_source,
    }
