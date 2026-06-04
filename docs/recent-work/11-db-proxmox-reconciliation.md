# DB ↔ Proxmox State Reconciliation (Reconcile-on-Read with Write-Back)

**Date**: 2026-06-04
**Focus**: Database integrity, state synchronization, and hypervisor-first truth mapping.

## Overview
This work session resolved the "hallucinated VM" issue. Previously, if an administrator deleted a VM directly inside the Proxmox Web UI, the app database remained unaware, continuing to display the VM on the student's dashboard. 

We replaced a temporary, read-only endpoint filter with an active, write-back reconciliation service.

## 1. The Design: Reconcile-on-Read with Write-Back

Instead of querying Proxmox on every single render or depending on it for basic dashboard page loads, the app now uses the database as the primary read target, but reconciles the database to match the hypervisor's state whenever a list request is made:

*   **Reconciliation Service (`reconciliation.py`)**:
    *   Exposes `reconcile_vm_existence(jobs, live_vmids)`.
    *   Compares active VM jobs (status `running` or `done`) against the set of live VMIDs returned by Proxmox.
    *   If a VM is missing from Proxmox, the service marks it as `deleted` in the database and logs a `vm.reconcile_deleted` audit trail entry attributed to the VM's owner.
*   **Database Integration (`database.py`)**:
    *   Added `mark_vm_job_deleted(job_id, reason)`.
    *   Updates the VM status to `deleted` and appends the reason to the `error_message`, while preserving the historical `proxmox_response` data.
*   **Router Wiring**:
    *   Integrated into `GET /vms` (`list_user_vms`) and `GET /admin/vms` (`list_all_vms`). The user VM list automatically filters out deleted records, meaning out-of-band deleted VMs disappear from student dashboards immediately upon page refresh.

## 2. Critical Safety Guards

We implemented two mandatory guards to protect the database against false positives:

*   **Guard 1 (Proxmox Reachability)**:
    *   Reconciliation only triggers when the live `list_vms()` call to Proxmox succeeds. If Proxmox is unreachable or down, the app retains database state as-is, preventing a network blip from mass-deleting the app's inventory.
*   **Guard 2 (Pending-State Guard)**:
    *   Only VMs in `running` or `done` states are eligible for reconciliation. VMs in `queued` or provisioning states are ignored, as they have reserved VMIDs but do not yet exist on the hypervisor.

## 3. Impact
*   The database is now self-correcting and remains a truthful cache of active VMs.
*   Deleted VMs vanish from student dashboards automatically without any extra frontend complexity.
*   Admin template pickers and VM managers are guaranteed to see only valid, existing VMs.
