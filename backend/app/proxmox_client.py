# =============================================================================
# proxmox_client.py
# =============================================================================
# This file is the single bridge between your FastAPI app and the Proxmox
# server. All HTTP calls to Proxmox go through this class.
#
# How Proxmox authentication works (Ticket-based):
#   Proxmox has its own REST API at https://<host>:8006/api2/json/
#   Step 1: POST /access/ticket with username+password
#           → Proxmox returns a "ticket" (like a session cookie) and a
#             CSRFPreventionToken.
#   Step 2: All further requests must include:
#           - Cookie: PVEAuthCookie=<ticket>
#           - Header: CSRFPreventionToken: <csrf_token>   (for POST/PUT/DELETE)
#
# Class design:
#   ProxmoxClient is instantiated once (at app startup in main.py).
#   authenticate() is called to get the ticket.
#   After that: create_vm(), get_vm_status(), list_vms() can be called freely.
#
#   Tickets expire after ~2 hours. The _ensure_authenticated() helper
#   re-authenticates automatically if the ticket is stale.
# =============================================================================

import os
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
    """

    # Base URL of the Proxmox API. Port 8006 is the default.
    API_BASE = "https://{host}:8006/api2/json"

    # Tickets are valid for ~2 hours. We re-auth 5 minutes before expiry.
    TICKET_LIFETIME_MINUTES = 115

    def __init__(self):
        self.host     = os.getenv("PROXMOX_HOST",     "192.168.1.100")
        self.username = os.getenv("PROXMOX_USER",     "root@pam")
        self.password = os.getenv("PROXMOX_PASSWORD", "")
        self.default_node = os.getenv("PROXMOX_NODE", "pve")

        # Disable SSL verification if you're using a self-signed cert
        # (common in university labs). Set PROXMOX_VERIFY_SSL=true in
        # production when you have a proper certificate.
        self.verify_ssl: bool = (
            os.getenv("PROXMOX_VERIFY_SSL", "false").lower() == "true"
        )

        # These are populated by authenticate()
        self._ticket:      Optional[str] = None
        self._csrf_token:  Optional[str] = None
        self._ticket_expiry: Optional[datetime] = None

        # Suppress urllib3's "InsecureRequestWarning" when verify_ssl=False
        # (otherwise you get a warning for every single request)
        if not self.verify_ssl:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # =========================================================================
    # ── Authentication ────────────────────────────────────────────────────────
    # =========================================================================

    def authenticate(self) -> None:
        """
        Log in to Proxmox and store the ticket + CSRF token.
        Must be called before any other method.

        Raises:
            ProxmoxAuthError: if Proxmox rejects the credentials.
        """
        url = f"https://{self.host}:8006/api2/json/access/ticket"

        try:
            response = requests.post(
                url,
                data={"username": self.username, "password": self.password},
                verify=self.verify_ssl,
                timeout=10,  # seconds — don't hang forever
            )
            response.raise_for_status()  # raises if HTTP status >= 400

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
        logger.info("ProxmoxClient authenticated successfully.")

    def _ensure_authenticated(self) -> None:
        """
        Check whether the ticket is still valid; re-authenticate if not.
        Called automatically by all public methods.
        """
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
        """Return the auth cookie dict needed for every Proxmox request."""
        return {"PVEAuthCookie": self._ticket}

    def _get_headers(self) -> Dict[str, str]:
        """
        Return headers needed for state-changing requests (POST/PUT/DELETE).
        GET requests don't need the CSRF token.
        """
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
        node    = config.pop("node", self.default_node)
        vmid    = config["vmid"]

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

            # Root disk: e.g. "local-lvm:20" means 20GB on local-lvm storage
            "scsi0": f"{config.get('storage', 'local-lvm')}:{config.get('disk_size', '10')}",

            # Boot from the SCSI disk
            "boot": "c",
            "bootdisk": "scsi0",

            # Network interface (virtio = best performance on Linux guests)
            "net0": "virtio,bridge=vmbr0",
        }

        # Attach ISO if provided (for OS installation)
        if config.get("iso"):
            proxmox_params["ide2"] = f"{config['iso']},media=cdrom"

        logger.info(f"Creating VM {vmid} on node '{node}' with name '{config.get('name')}'")
        self._post(path, proxmox_params)

        logger.info(f"VM {vmid} created successfully on node '{node}'.")
        return vmid

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
        logger.debug(f"VM {vmid} status: {data.get('status')}")
        return data

    def start_vm(self, vmid: int, node: Optional[str] = None) -> str:
        """
        Start a stopped VM. Returns the Proxmox task ID (UPID).
        Proxmox tasks are asynchronous — the UPID lets you poll for completion.
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/status/start"
        task_id = self._post(path, {})
        logger.info(f"Start task for VM {vmid}: {task_id}")
        return task_id

    def stop_vm(self, vmid: int, node: Optional[str] = None) -> str:
        """Stop a running VM (hard stop). Returns the Proxmox task ID."""
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/status/stop"
        task_id = self._post(path, {})
        logger.info(f"Stop task for VM {vmid}: {task_id}")
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
        (Unique Process ID, returned by create/start/stop operations).

        Returns a dict with 'status' ('running' or 'stopped') and
        'exitstatus' ('OK' or an error message) when stopped.
        """
        path = f"nodes/{node}/tasks/{upid}/status"
        return self._get(path)
