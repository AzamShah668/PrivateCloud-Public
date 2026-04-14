# =============================================================================
# proxmox_client.py
# =============================================================================
# This file is the single bridge between your FastAPI app and the Proxmox
# server. All HTTP calls to Proxmox go through this class.
#
# Proxmox supports two authentication methods:
#
# 1. API Token (preferred — set PROXMOX_TOKEN_ID + PROXMOX_TOKEN_SECRET):
#    - Created in Proxmox UI: Datacenter → Permissions → API Tokens
#    - Every request includes: Authorization: PVEAPIToken=<id>=<secret>
#    - Tokens never expire — no renewal needed, no cookies, no CSRF
#    - Much simpler and more reliable for long-running services
#
# 2. Ticket-based (legacy fallback — used when token env vars are NOT set):
#    - POST /access/ticket with username+password → ticket + CSRF token
#    - Tickets expire after ~2 hours, auto-renewed by _ensure_authenticated()
#    - Requires cookies on every request + CSRF header on POST/PUT/DELETE
#
# Class design:
#   ProxmoxClient is instantiated once (at app startup in main.py).
#   If PROXMOX_TOKEN_ID is set → token auth, ready immediately.
#   If not set → ticket auth, authenticate() must be called first.
# =============================================================================

import os
import re
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

import requests
from requests.exceptions import RequestException
from dotenv import load_dotenv

load_dotenv()

# Set up a module-level logger so errors show up in your app logs.
logger = logging.getLogger(__name__)


# =============================================================================
# ── Exceptions ────────────────────────────────────────────────────────────────
# Custom exceptions make it easy for routes to catch Proxmox-specific errors
# and return the right HTTP status code to the client.
# =============================================================================

# =============================================================================
# ── Golden template map ───────────────────────────────────────────────────────
# Maps an OS choice string → Proxmox template VMID. When the user requests one
# of these OSes, the backend *clones* the matching template instead of running
# a slow ISO installer. The templates themselves are built on the Proxmox node
# by `scripts/proxmox/SETUP_GOLDEN_IMAGE.sh` (run once, as root).
#
# If an OS is NOT in this map, the create-VM route falls back to the legacy
# ISO install path (see `_OS_MAP` in routes/vm_routes.py).
# =============================================================================

CLOUD_TEMPLATE_MAP: Dict[str, int] = {
    "ubuntu-24.04": 9000,
}


class ProxmoxAuthError(Exception):
    """Raised when authentication with Proxmox fails (wrong credentials, etc.)"""
    pass


class ProxmoxAPIError(Exception):
    """Raised when a Proxmox API call returns an unexpected error."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.status_code = status_code


# =============================================================================
# ── ProxmoxClient ─────────────────────────────────────────────────────────────
# =============================================================================

class ProxmoxClient:
    """
    A thin wrapper around the Proxmox VE REST API.

    Usage:
        client = ProxmoxClient()
        client.authenticate()
        vmid = client.create_vm({...})
        status = client.get_vm_status(vmid, node="pve")
        client.delete_vm(vmid, node="pve")
    """

    # Base URL of the Proxmox API. Port 8006 is the default.
    API_BASE = "https://{host}:8006/api2/json"

    # Tickets are valid for ~2 hours. We re-auth 5 minutes before expiry.
    TICKET_LIFETIME_MINUTES = 115

    def __init__(self):
        self.host         = os.getenv("PROXMOX_HOST",     "192.168.1.100")
        self.default_node = os.getenv("PROXMOX_NODE",     "pve")

        # ── Auth method selection ────────────────────────────────────────
        # If PROXMOX_TOKEN_ID is set → use API token auth (preferred).
        # Otherwise → fall back to legacy ticket-based auth.
        self._token_id:       Optional[str] = os.getenv("PROXMOX_TOKEN_ID")
        self._token_secret:   Optional[str] = os.getenv("PROXMOX_TOKEN_SECRET")
        self._use_token_auth: bool = bool(self._token_id and self._token_secret)

        # Legacy ticket auth credentials (only needed if not using tokens)
        self.username = os.getenv("PROXMOX_USER",     "root@pam")
        self.password = os.getenv("PROXMOX_PASSWORD", "")

        # Disable SSL verification if you're using a self-signed cert
        # (common in university labs). Set PROXMOX_VERIFY_SSL=true in
        # production when you have a proper certificate.
        self.verify_ssl: bool = (
            os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"
        )

        # These are populated by authenticate() — only used for ticket auth
        self._ticket:        Optional[str]      = None
        self._csrf_token:    Optional[str]      = None
        self._ticket_expiry: Optional[datetime] = None

        # Suppress urllib3's "InsecureRequestWarning" when verify_ssl=False
        if not self.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        if self._use_token_auth:
            logger.info("ProxmoxClient using API token auth (no ticket renewal needed).")
        else:
            logger.info("ProxmoxClient using legacy ticket auth (PROXMOX_TOKEN_ID not set).")

    # =========================================================================
    # ── Authentication ────────────────────────────────────────────────────────
    # =========================================================================

    def authenticate(self) -> None:
        """
        Log in to Proxmox and store the ticket + CSRF token.

        With token auth this is a no-op — tokens are always valid.
        With ticket auth this POSTs to /access/ticket to get a session.

        Raises:
            ProxmoxAuthError: if Proxmox rejects the credentials (ticket mode only).
        """
        # Token auth needs no login step — the token is sent with every request
        if self._use_token_auth:
            logger.debug("Token auth active — authenticate() is a no-op.")
            return

        url = f"https://{self.host}:8006/api2/json/access/ticket"

        try:
            response = requests.post(
                url,
                data={"username": self.username, "password": self.password},
                verify=self.verify_ssl,
                timeout=10,
            )
            response.raise_for_status()

        except RequestException as exc:
            raise ProxmoxAuthError(
                f"Could not connect to Proxmox at {self.host}: {exc}"
            ) from exc

        data = response.json().get("data", {})
        if not data.get("ticket"):
            raise ProxmoxAuthError(
                "Proxmox returned no ticket. Check your PROXMOX_USER and PROXMOX_PASSWORD."
            )

        self._ticket     = data["ticket"]
        self._csrf_token = data["CSRFPreventionToken"]
        self._ticket_expiry = (
            datetime.now(timezone.utc) + timedelta(minutes=self.TICKET_LIFETIME_MINUTES)
        )
        logger.info("ProxmoxClient authenticated via ticket successfully.")

    def _ensure_authenticated(self) -> None:
        """
        Make sure we're ready to make API calls.
        - Token auth: always ready (tokens don't expire).
        - Ticket auth: re-authenticate if the ticket is missing or expired.
        """
        if self._use_token_auth:
            return  # tokens never expire

        if (
            self._ticket is None
            or self._ticket_expiry is None
            or datetime.now(timezone.utc) >= self._ticket_expiry
        ):
            logger.info("Proxmox ticket missing or expired. Re-authenticating...")
            self.authenticate()

    # =========================================================================
    # ── Internal HTTP helpers ─────────────────────────────────────────────────
    # =========================================================================

    def _get_cookies(self) -> Dict[str, str]:
        """Return the auth cookie dict for ticket-based requests."""
        if self._use_token_auth:
            return {}  # token auth uses headers, not cookies
        return {"PVEAuthCookie": self._ticket}

    def _get_headers(self) -> Dict[str, str]:
        """
        Return headers needed for API requests.
        - Token auth: Authorization header on ALL requests (GET, POST, DELETE, etc.)
        - Ticket auth: CSRFPreventionToken on state-changing requests only
        """
        if self._use_token_auth:
            # Proxmox token format: PVEAPIToken=user@realm!tokenname=uuid-secret
            return {
                "Authorization": f"PVEAPIToken={self._token_id}={self._token_secret}"
            }
        return {"CSRFPreventionToken": self._csrf_token}

    def _url(self, path: str) -> str:
        """Build the full API URL for a given path."""
        base = f"https://{self.host}:8006/api2/json"
        return f"{base}/{path.lstrip('/')}"

    def _get(self, path: str) -> Any:
        """Perform a GET request and return the 'data' field of the response."""
        self._ensure_authenticated()
        try:
            resp = requests.get(
                self._url(path),
                cookies=self._get_cookies(),
                headers=self._get_headers(),  # needed for token auth
                verify=self.verify_ssl,
                timeout=15,
            )
            resp.raise_for_status()
            return resp.json().get("data")
        except RequestException as exc:
            raise ProxmoxAPIError(f"GET {path} failed: {exc}") from exc

    def _post(self, path: str, data: Dict[str, Any]) -> Any:
        """Perform a POST request and return the 'data' field of the response."""
        self._ensure_authenticated()
        try:
            resp = requests.post(
                self._url(path),
                data=data,
                cookies=self._get_cookies(),
                headers=self._get_headers(),
                verify=self.verify_ssl,
                timeout=30,  # VM creation can take a few seconds
            )
            resp.raise_for_status()
            return resp.json().get("data")
        except RequestException as exc:
            raise ProxmoxAPIError(f"POST {path} failed: {exc}") from exc

    def _delete(self, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Perform a DELETE request and return the 'data' field of the response.
        Token auth: Authorization header. Ticket auth: CSRF token + cookie.

        Args:
            path:   the API path, e.g. "nodes/pve/qemu/101"
            params: optional query-string parameters (e.g. purge flags)
        """
        self._ensure_authenticated()
        try:
            resp = requests.delete(
                self._url(path),
                params=params or {},
                cookies=self._get_cookies(),
                headers=self._get_headers(),
                verify=self.verify_ssl,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("data")
        except RequestException as exc:
            raise ProxmoxAPIError(f"DELETE {path} failed: {exc}") from exc

    # =========================================================================
    # ── Public API Methods ────────────────────────────────────────────────────
    # =========================================================================

    def get_next_vmid(self) -> int:
        """
        Ask Proxmox for the next available VMID.
        Proxmox maintains a cluster-wide counter so IDs never collide.

        Returns:
            int: the next free VMID (e.g. 100, 101, 102, ...)
        """
        data = self._get("cluster/nextid")
        return int(data)

    def create_vm(self, config: Dict[str, Any]) -> int:
        """
        Create a VM on a Proxmox node.

        Args:
            config: dict with at minimum:
                {
                    "node":      "pve",           # Proxmox node name
                    "vmid":      101,              # unique VM ID
                    "name":      "my-web-server",
                    "ostype":    "l26",            # l26 = Linux 2.6+
                    "cores":     2,
                    "memory":    2048,             # MB
                    "storage":   "local-lvm",      # Proxmox storage pool
                    "disk_size": "20G",
                    "iso":       "local:iso/ubuntu-22.04.iso",  # optional
                }

        Returns:
            int: the vmid of the newly created VM.

        Raises:
            ProxmoxAPIError: if Proxmox returns an error.
        """
        node = config.pop("node", self.default_node)
        vmid = config["vmid"]

        # Proxmox qm create endpoint
        path = f"nodes/{node}/qemu"

        # Map our config keys to Proxmox API parameter names
        proxmox_params: Dict[str, Any] = {
            "vmid":    vmid,
            "name":    config.get("name"),
            "ostype":  config.get("ostype", "l26"),      # l26 = Linux 2.6+
            "cores":   config.get("cores", 1),
            "sockets": 1,
            "memory":  config.get("memory", 1024),       # MB

            # SCSI controller (virtio-scsi-pci is the modern recommended one)
            "scsihw": "virtio-scsi-pci",

            # Root disk: e.g. "local-lvm:20" means 20 GB on local-lvm storage
            "scsi0": f"{config.get('storage', 'local-lvm')}:{config.get('disk_size', '10')}",

            # Network interface (virtio = best performance on Linux guests)
            "net0": "virtio,bridge=vmbr0",
        }

        # Attach ISO if provided (for OS installation)
        if config.get("iso"):
            proxmox_params["ide2"] = f"{config['iso']},media=cdrom"
            # Boot from CD-ROM first (d), then hard disk (c)
            proxmox_params["boot"] = "order=ide2;scsi0"
        else:
            # No ISO — boot from hard disk only
            proxmox_params["boot"] = "order=scsi0"
            proxmox_params["bootdisk"] = "scsi0"

        logger.info("Creating VM %s on node '%s' with name '%s'", vmid, node, config.get("name"))
        self._post(path, proxmox_params)

        logger.info("VM %s created successfully on node '%s'.", vmid, node)
        return vmid

    def clone_template(
        self,
        template_vmid: int,
        new_vmid: int,
        name: str,
        node: Optional[str] = None,
        full: bool = True,
        storage: Optional[str] = None,
    ) -> str:
        """
        Clone a Proxmox template into a new VM.

        This is the fast-path replacement for ISO-based VM creation. The
        template must already exist on Proxmox (built by
        scripts/proxmox/SETUP_GOLDEN_IMAGE.sh). A full clone copies the
        template's disk into a brand-new independent VM — typically takes
        5-15 seconds because the disk is already sized small (~2 GB).

        Args:
            template_vmid: VMID of the existing template (e.g. 9000).
            new_vmid:      VMID to assign to the new cloned VM.
            name:          Display name for the new VM.
            node:          Proxmox node (defaults to self.default_node).
            full:          True → full clone (independent disk, slower but safe).
                           False → linked clone (faster but depends on template).
            storage:       Target storage pool for the clone's disk. Defaults
                           to the template's storage.

        Returns:
            str: Proxmox task ID (UPID). Poll get_task_status() to wait for
                 the clone to finish before configuring the new VM.

        Raises:
            ProxmoxAPIError: if the template is missing or the clone fails.
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{template_vmid}/clone"

        params: Dict[str, Any] = {
            "newid": new_vmid,
            "name":  name,
            "full":  1 if full else 0,
        }
        if storage:
            params["storage"] = storage

        logger.info(
            "Cloning template %s → VM %s (name='%s', full=%s) on node '%s'",
            template_vmid, new_vmid, name, full, node,
        )
        task_id = self._post(path, params)
        logger.info("Clone task for VM %s: %s", new_vmid, task_id)
        return task_id

    def resize_disk(
        self,
        vmid: int,
        size_gb: int,
        disk: str = "scsi0",
        node: Optional[str] = None,
    ) -> None:
        """
        Grow a VM's disk to the requested absolute size.

        Proxmox's resize API only supports GROWING a disk, not shrinking.
        The `size` parameter is absolute (e.g. "20G"), not an increment.

        Args:
            vmid:    the VM whose disk to resize.
            size_gb: new disk size in GiB (absolute).
            disk:    disk identifier — cloned templates use "scsi0" by default.
            node:    Proxmox node (defaults to self.default_node).
        """
        node = node or self.default_node

        # Guard: Proxmox only supports growing disks, not shrinking.
        config = self.get_vm_config(vmid=vmid, node=node)
        current_disk = config.get(disk, "")
        if current_disk:
            size_match = re.search(r"size=(\d+)G", str(current_disk))
            if size_match:
                current_size_gb = int(size_match.group(1))
                if size_gb < current_size_gb:
                    raise ProxmoxAPIError(
                        f"Cannot shrink disk '{disk}' from {current_size_gb}G "
                        f"to {size_gb}G. Proxmox only supports growing disks."
                    )

        path = f"nodes/{node}/qemu/{vmid}/resize"
        params = {"disk": disk, "size": f"{size_gb}G"}
        logger.info("Resizing VM %s disk %s → %sG", vmid, disk, size_gb)
        self._put(path, params)
        logger.info("VM %s disk %s resized to %sG", vmid, disk, size_gb)

    def set_cloudinit_user(
        self,
        vmid: int,
        ciuser: str,
        cipassword: str,
        node: Optional[str] = None,
        ipconfig: str = "ip=dhcp",
    ) -> None:
        """
        Configure cloud-init credentials on a cloned VM before it first boots.

        Cloud-init reads these settings from the VM config at boot and sets up
        the login user, password, and network automatically. This is how clones
        of the golden template get per-VM identity.

        Args:
            vmid:       the cloned VM to configure.
            ciuser:     Linux username to create (e.g. "ubuntu").
            cipassword: initial SSH password for that user.
            node:       Proxmox node (defaults to self.default_node).
            ipconfig:   cloud-init network config string, default DHCP.
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/config"
        params = {
            "ciuser":     ciuser,
            "cipassword": cipassword,
            "ipconfig0":  ipconfig,
        }
        logger.info("Setting cloud-init user on VM %s (user='%s')", vmid, ciuser)
        self._post(path, params)
        logger.info("VM %s cloud-init user set", vmid)

    def get_vm_status(self, vmid: int, node: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the current runtime status of a VM from Proxmox.

        Returns a dict like:
        {
            "status": "running",   # or "stopped", "paused"
            "cpus": 2,
            "maxmem": 2147483648,  # bytes
            "maxdisk": 21474836480,
            "uptime": 3600,        # seconds
            "pid": 12345,
            ...
        }

        Args:
            vmid: the Proxmox VM ID
            node: Proxmox node name (defaults to self.default_node)
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/status/current"
        data = self._get(path)
        logger.debug("VM %s status: %s", vmid, data.get("status"))
        return data

    def start_vm(self, vmid: int, node: Optional[str] = None) -> str:
        """
        Start a stopped VM. Returns the Proxmox task ID (UPID).
        Proxmox tasks are asynchronous — the UPID lets you poll for completion.
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/status/start"
        task_id = self._post(path, {})
        logger.info("Start task for VM %s: %s", vmid, task_id)
        return task_id

    def stop_vm(self, vmid: int, node: Optional[str] = None) -> str:
        """Stop a running VM (hard stop). Returns the Proxmox task ID."""
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/status/stop"
        task_id = self._post(path, {})
        logger.info("Stop task for VM %s: %s", vmid, task_id)
        return task_id

    def restart_vm(self, vmid: int, node: Optional[str] = None) -> str:
        """Reboot a running VM. Returns the Proxmox task ID (UPID)."""
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/status/reboot"
        task_id = self._post(path, {})
        logger.info("Reboot task for VM %s: %s", vmid, task_id)
        return task_id

    def get_vm_config(self, vmid: int, node: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the full configuration of a VM (cores, memory, disks, etc.).
        Useful for showing current state before/after a resize.
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/config"
        return self._get(path)

    def update_vm_config(self, vmid: int, node: Optional[str] = None, **config) -> None:
        """
        Update a VM's configuration (CPU, RAM, etc.).
        The VM should be stopped for most config changes to take effect.

        Args:
            vmid: the Proxmox VM ID
            node: Proxmox node name
            **config: key-value pairs to update, e.g. cores=4, memory=4096
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/config"
        logger.info("Updating VM %s config: %s", vmid, config)
        self._post(path, config)
        logger.info("VM %s config updated successfully.", vmid)

    def _put(self, path: str, data: Dict[str, Any]) -> Any:
        """Perform a PUT request and return the 'data' field of the response."""
        self._ensure_authenticated()
        try:
            resp = requests.put(
                self._url(path),
                data=data,
                cookies=self._get_cookies(),
                headers=self._get_headers(),
                verify=self.verify_ssl,
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json().get("data")
        except RequestException as exc:
            raise ProxmoxAPIError(f"PUT {path} failed: {exc}") from exc

    def delete_vm(self, vmid: int, node: Optional[str] = None) -> str:
        """
        Permanently delete (destroy) a VM from Proxmox, including its disk.
        This operation is IRREVERSIBLE.

        The VM should be stopped before calling this. If it is still running,
        Proxmox will refuse the request and a ProxmoxAPIError will be raised.
        Call stop_vm() first and wait for the stop task to complete.

        The query params passed to Proxmox:
          - purge=1                        removes the VM from all backup jobs /
                                           replication configs on the cluster
          - destroy-unreferenced-disks=1   wipes the actual disk image from
                                           the storage pool so you don't leak space

        Args:
            vmid: the Proxmox VM ID to destroy
            node: Proxmox node name (defaults to self.default_node)

        Returns:
            str: the Proxmox task ID (UPID). Poll get_task_status() to confirm
                 completion if you need to wait for it.

        Raises:
            ProxmoxAPIError: if Proxmox rejects the request (VM still running,
                             VM not found, permission denied, etc.)
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}"

        task_id = self._delete(
            path,
            params={
                "purge":                       1,
                "destroy-unreferenced-disks":  1,
            },
        )

        logger.info("Delete task for VM %s on node '%s': %s", vmid, node, task_id)
        return task_id

    def list_vms(self, node: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all VMs on a node. Returns a list of dicts, one per VM.
        Each dict includes: vmid, name, status, cpus, maxmem, etc.
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu"
        data = self._get(path)
        return data or []

    def get_task_status(self, node: str, upid: str) -> Dict[str, Any]:
        """
        Check the status of an async Proxmox task by its UPID
        (Unique Process ID, returned by create/start/stop/delete operations).

        Returns a dict with 'status' ('running' or 'stopped') and
        'exitstatus' ('OK' or an error message) when stopped.
        """
        path = f"nodes/{node}/tasks/{upid}/status"
        return self._get(path)