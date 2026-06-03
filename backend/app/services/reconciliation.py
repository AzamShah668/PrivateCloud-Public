# =============================================================================
# services/reconciliation.py
# =============================================================================
# DB <-> Proxmox state reconciliation.
#
# Why this exists:
#   Proxmox is the source of truth for whether a VM exists. Our vm_jobs table
#   is a cache of intent. If an admin deletes a VM directly in the Proxmox UI
#   (out-of-band, not through this app), the DB never finds out and the
#   dashboard keeps showing a VM that is gone -- the "hallucinated VM" problem
#   (see docs/knowledge debugging journal). Filtering the *response* against
#   live Proxmox (the old verify_proxmox flag) hid it for one endpoint but left
#   the DB permanently stale.
#
#   This module fixes it properly: it writes the truth back into the DB. When a
#   VM that *should* be live is absent from Proxmox, its row is soft-deleted
#   (status='deleted'), so it disappears from every read path that already
#   filters deleted rows -- the DB self-corrects and the UI then reads the
#   reconciled DB.
#
# Scope (deliberately narrow):
#   - Reconciles EXISTENCE / lifecycle only. Power state, CPU%, memory and
#     uptime are live telemetry and stay as live enrichment in the routes --
#     they are real-time data, not stale cache, so there is nothing to "fix".
# =============================================================================

import logging
from typing import Iterable

from db import database
from app.models.vm import VMStatus

logger = logging.getLogger(__name__)

# A job is only eligible for existence-reconciliation when we genuinely expect a
# live VM to back it. A 'queued' job has a reserved VMID that may not exist on
# Proxmox yet (guard G2); a 'failed' job is kept intentionally so the user can
# read the error; a 'deleted' job is already gone.
_ELIGIBLE_STATUSES = frozenset({VMStatus.running.value, VMStatus.done.value})

_RECONCILE_REASON = "Reconciled: VM not found on Proxmox (deleted out-of-band)."


def reconcile_vm_existence(
    jobs: Iterable[dict],
    live_vmids: set[int],
) -> set[int]:
    """
    Soft-delete vm_jobs whose VM has vanished from Proxmox.

    Args:
        jobs: vm_job dicts already loaded from the DB (each has 'id', 'vmid',
              'status', 'user_id').
        live_vmids: the set of VMIDs currently present on Proxmox. The CALLER
              must only pass this after a SUCCESSFUL live list_vms() call --
              never call this with a partial/empty set built from a failed
              Proxmox request, or it would mass-delete the whole inventory
              (guard G1 lives in the caller).

    Returns:
        The set of job_ids that were soft-deleted, so the caller can drop them
        from the response in-memory without re-querying.
    """
    deleted_ids: set[int] = set()

    for job in jobs:
        status = job.get("status")
        vmid = job.get("vmid")

        if status not in _ELIGIBLE_STATUSES:
            continue
        if vmid is None:
            continue
        if int(vmid) in live_vmids:
            continue

        # This job claims a live VM, but Proxmox doesn't have that VMID.
        row = database.mark_vm_job_deleted(job["id"], _RECONCILE_REASON)
        if row is None:
            # Already deleted by a concurrent request -- skip silently.
            continue

        deleted_ids.add(job["id"])
        logger.info(
            "Reconciliation soft-deleted vm_job id=%s (vmid=%s, was '%s') -- "
            "absent from Proxmox.",
            job["id"], vmid, status,
        )

        # Audit trail for the system-initiated delete, attributed to the VM's
        # owner. Best-effort: an audit failure must never abort reconciliation.
        try:
            database.add_audit_log(
                user_id=job["user_id"],
                action="vm.reconcile_deleted",
                target_type="vm_job",
                target_id=str(job["id"]),
                details={
                    "vmid": vmid,
                    "previous_status": status,
                    "reason": _RECONCILE_REASON,
                },
            )
        except Exception as exc:  # noqa: BLE001 - audit is non-critical
            logger.warning(
                "Failed to write reconcile audit for vm_job id=%s: %s",
                job["id"], exc,
            )

    if deleted_ids:
        logger.info(
            "Reconciliation pass soft-deleted %d stale vm_job(s): %s",
            len(deleted_ids), sorted(deleted_ids),
        )
    return deleted_ids
