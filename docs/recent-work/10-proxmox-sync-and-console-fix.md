# Proxmox VM Sync and Console Fixes

**Date**: 2026-06-03
**Focus**: UI/UX refinement, live Proxmox state synchronization, and Linux terminal connectivity.

## Overview
This work session focused on resolving discrepancies between the Proxmox hypervisor's actual state and the administrative UI, alongside critical fixes for Linux VM console accessibility.

## 1. Proxmox-UI Reconciliation (Stale VM Sync)

### The Problem
The Admin UI relied purely on database records (`vm_jobs` table). If an administrator deleted a VM directly inside the Proxmox UI, the PrivateCloud database was unaware, causing "stale" VMs to remain visible. This was particularly problematic in the "Publish Template" modal, where admins could attempt to create templates from deleted VMs.

### The Solution
We implemented an optional live-verification mechanism that cross-references the database with Proxmox.

*   **Backend (`admin_routes.py`)**: 
    *   Added a `verify_proxmox` boolean query parameter to the `GET /admin/vms` endpoint.
    *   When set to `true`, the backend calls `proxmox_client.list_vms()` and filters the database results, dropping any `vm_jobs` records whose `vmid` is no longer present on the hypervisor.
*   **Frontend API (`admin.ts` & `use-admin.ts`)**: 
    *   Updated the `listAllVMs` API call and the `useAdminVMs` React Query hook to accept the `verifyProxmox` flag.
*   **UI Integration (`AdminTemplatesPage.tsx`)**: 
    *   Configured the `PublishModal` to fetch verified VMs. Admins now only see a list of actual, running VMs that safely exist on the host when creating a new template.

## 2. Linux Terminal / Console Access Fixes

### The Problem
The "Console" button for Linux VMs was hidden, and even when forced visible, it failed to connect. The terminal modal was incorrectly pointing to `window.location.hostname` (typically `localhost`) instead of the VM's actual IP address, resulting in connection timeouts for the `ttyd` service running on port `7681`.

### The Solution
*   **Button Visibility (`VMDetailPage.tsx`)**: 
    *   Fixed a bug where the `showConsole` boolean prop was missing. Added `showConsole={!isWindows}` to ensure the "Console" button is visible for Linux VMs (while Windows VMs display the "Desktop" button).
*   **Connection URL Fix (`ConsoleModal.tsx`)**: 
    *   Changed the target URL for Linux consoles from `http://${window.location.hostname}:7681` to `http://${vmIP}:7681`. 
    *   This correctly routes the request to the `ttyd` terminal service running inside the cloned Linux VM.

## 3. Git Repository Sync

*   **Branch Alignment**: 
    *   Merged the working `azams-branch` into the `main` branch to align environments.
    *   After discovering that the recent unfinished changes were prematurely merged into `main`, performed a `git reset --hard` on `main` to restore its stable state (commit `83f8ace`).
    *   Kept the recent development work safely isolated on `azams-branch` (commit `d394317`), ready for further testing before a final production merge.
