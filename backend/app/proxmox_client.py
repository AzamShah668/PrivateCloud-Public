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
import time
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
        client.delete_vm(vmid, node="pve")
    """

    # Base URL of the Proxmox API. Port 8006 is the default.
    API_BASE = "https://{host}:8006/api2/json"

    # Tickets are valid for ~2 hours. We re-auth 5 minutes before expiry.
    TICKET_LIFETIME_MINUTES = 115

    def __init__(self):
        self.host         = os.getenv("PROXMOX_HOST",     "192.168.1.100")
        self.default_node = os.getenv("PROXMOX_NODE",     "home")

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

        # ── Golden image config ──────────────────────────────────────────
        # VMID of the golden image template to clone new VMs from.
        # Set GOLDEN_IMAGE_VMID in your .env (default: 9000).
        self.golden_image_vmid: int = int(os.getenv("GOLDEN_IMAGE_VMID", "9000"))

        # Default SSH credentials baked into the golden image.
        # These are returned to the user after VM creation so they can log in.
        self.vm_default_username: str = os.getenv("VM_DEFAULT_USERNAME", "ubuntu")
        self.vm_default_password: str = os.getenv("VM_DEFAULT_PASSWORD", "")

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

            # Boot from the SCSI disk
            "boot":     "c",
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

    def restart_vm(self, vmid: int, node: Optional[str] = None) -> str:
        """Reboot a running VM. Returns the Proxmox task ID (UPID)."""
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/status/reboot"
        task_id = self._post(path, {})
        logger.info(f"Reboot task for VM {vmid}: {task_id}")
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
        logger.info(f"Updating VM {vmid} config: {config}")
        self._post(path, config)
        logger.info(f"VM {vmid} config updated successfully.")

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

        logger.info(f"Delete task for VM {vmid} on node '{node}': {task_id}")
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

    # =========================================================================
    # ── Golden-image clone + IP retrieval ─────────────────────────────────────
    # =========================================================================

    def clone_vm(
        self,
        template_vmid: int,
        new_vmid: int,
        name: str,
        node: Optional[str] = None,
        storage: Optional[str] = None,
    ) -> str:
        """
        Clone a VM template to a new, fully independent VM (full clone).

        Args:
            template_vmid : VMID of the source template (e.g. 9000).
            new_vmid      : VMID to assign to the new VM.
            name          : Display name for the new VM.
            node          : Proxmox node name (defaults to self.default_node).
            storage       : Target storage pool (e.g. "local-lvm"). If None,
                            Proxmox uses the same storage as the template.

        Returns:
            str: The UPID (task ID) of the async clone operation.
                 Pass this to wait_for_task() to block until the clone finishes.

        Raises:
            ProxmoxAPIError: if Proxmox rejects the clone request.
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{template_vmid}/clone"

        params: Dict[str, Any] = {
            "newid":  new_vmid,
            "name":   name,
            "full":   1,       # full clone — independent disk, not linked
            "target": node,
        }
        if storage:
            params["storage"] = storage

        upid = self._post(path, params)
        logger.info(
            "Clone task started: template vmid=%d → new vmid=%d  (upid=%s)",
            template_vmid, new_vmid, upid,
        )
        return upid

    def wait_for_task(
        self,
        node: str,
        upid: str,
        timeout: int = 180,
        poll_interval: int = 3,
    ) -> None:
        """
        Block until a Proxmox async task reaches status='stopped'.

        Proxmox tasks (clone, start, stop, delete) are asynchronous — the API
        returns a UPID immediately and the work happens in the background.
        This helper polls get_task_status() until the task either succeeds
        or fails, so callers don't need to manage their own polling loops.

        Args:
            node          : Proxmox node where the task is running.
            upid          : Task ID returned by clone_vm / start_vm / etc.
            timeout       : Max seconds to wait before giving up (default 180).
            poll_interval : Seconds between each status check (default 3).

        Raises:
            ProxmoxAPIError: if the task fails or the timeout is reached.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                task = self.get_task_status(node, upid)
            except ProxmoxAPIError as exc:
                logger.warning("Could not poll task %s: %s", upid, exc)
                time.sleep(poll_interval)
                continue

            if task.get("status") == "stopped":
                exit_status = task.get("exitstatus", "")
                if exit_status == "OK":
                    logger.info("Task %s completed OK.", upid)
                    return
                raise ProxmoxAPIError(
                    f"Task {upid} failed with exitstatus='{exit_status}'"
                )

            time.sleep(poll_interval)

        raise ProxmoxAPIError(
            f"Task {upid} timed out after {timeout}s — still not 'stopped'."
        )

    def get_vm_ip_from_agent(
        self,
        vmid: int,
        node: Optional[str] = None,
        timeout: int = 120,
        poll_interval: int = 5,
    ) -> Optional[str]:
        """
        Poll the QEMU guest agent until a non-loopback IPv4 address appears.

        After a VM boots, it takes a few seconds for the OS to fully start and
        for the guest agent to respond.  This method retries automatically until
        `timeout` seconds have elapsed, then returns None if no IP was found.

        Prerequisites (must be true for this to work):
          - `qemu-guest-agent` package installed and running inside the VM.
          - `agent: 1` set in the VM's Proxmox hardware config (the golden
            image template should have this pre-configured).

        Args:
            vmid          : VMID of the running VM.
            node          : Proxmox node name (defaults to self.default_node).
            timeout       : Max seconds to poll before giving up (default 120).
            poll_interval : Seconds between each attempt (default 5).

        Returns:
            str | None: The first non-loopback IPv4 address found, or None.
        """
        node = node or self.default_node
        path = f"nodes/{node}/qemu/{vmid}/agent/network-get-interfaces"
        deadline = time.time() + timeout

        logger.info(
            "Polling QEMU guest agent for IP of vmid=%d (timeout=%ds)…",
            vmid, timeout,
        )

        while time.time() < deadline:
            try:
                data = self._get(path)

                # The agent endpoint returns { "result": [ { "name": "eth0",
                #   "ip-addresses": [ {"ip-address-type": "ipv4",
                #                      "ip-address": "192.168.0.x", ...} ] } ] }
                if data and "result" in data:
                    for iface in data["result"]:
                        # Skip loopback and docker bridge
                        if iface.get("name") in ("lo", "docker0"):
                            continue
                        for addr_info in iface.get("ip-addresses", []):
                            if addr_info.get("ip-address-type") != "ipv4":
                                continue
                            ip = addr_info.get("ip-address", "")
                            # Skip loopback even if interface name was different
                            if ip and not ip.startswith("127."):
                                logger.info(
                                    "Got IP %s for vmid=%d via guest agent.", ip, vmid
                                )
                                return ip

            except Exception as exc:
                # Agent not ready yet — this is expected right after boot
                logger.debug(
                    "Guest agent not ready for vmid=%d (%s), retrying in %ds…",
                    vmid, exc, poll_interval,
                )

            time.sleep(poll_interval)

        logger.warning(
            "IP polling timed out for vmid=%d after %ds.", vmid, timeout
        )
        return None
