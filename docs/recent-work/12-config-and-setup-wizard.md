# DB-Backed Setup Wizard & Encrypted Settings

**Date**: 2026-06-04
**Focus**: Infrastructure configuration, database-backed settings, secrets encryption-at-rest, and onboarding UX.

## Overview
This work session migrated all operational configuration (Proxmox IP/credentials, LLM API keys, Guacamole logins, VM credentials) from the static root `.env` file into a UI-manageable, DB-backed settings store. We built a first-run setup wizard for initial deployment.

## 1. The Bootstrap vs. Operational Config Split
You cannot store database credentials inside the database they unlock. Therefore, a minimal bootstrap configuration remains in `.env` and `docker-compose.yml`:
*   PostgreSQL & MySQL connection settings
*   Redis connection settings
*   JWT secret key
*   **`SETTINGS_ENCRYPTION_KEY`** (new key for Fernet encryption)

All other settings (Proxmox connection, OpenRouter settings, default VM credentials, and Guacamole administration) were migrated to the database.

## 2. Encrypted Settings Store
We utilized the existing `system_settings` table to house configuration, but introduced several key security and architectural enhancements:

*   **At-Rest Encryption (`secret_crypto.py`)**: 
    *   Sensitive settings (passwords, API tokens) are Fernet-encrypted with the `SETTINGS_ENCRYPTION_KEY` and prefixed with `enc::`.
*   **Data Masking**:
    *   When fetching or updating settings, secret values are fully masked in API responses and audit logs (`••••` or `is_set=true`, `value=""`) to prevent leaks to logs or browser consoles.
*   **Single Source of Truth (`config_registry.py`)**:
    *   A single `CONFIG_REGISTRY` contains all keys, descriptions, value types, and env-fallbacks. The database is seeded automatically from this registry during startup.
*   **Resolution and Caching (`config.py`)**:
    *   A resolver `get_config()` reads database settings first, falls back to env variables, and then defaults. It includes a 30-second cache TTL.

## 3. Dynamic Configuration Reloading
Under the old architecture, singletons initialized at module import froze their configuration. To allow updates to apply immediately without restarting the Docker containers:
*   We added a global config **generation counter** that increments whenever settings are saved.
*   We created a client proxy (`_ProxmoxClientProxy`) that intercepts calls to the Proxmox client and rebuilds the underlying connection if the local generation is out of sync with the global settings generation.
*   The LLM Agent was updated to initialize its client lazily, checking the generation counter on every run.

## 4. Frontend First-Run Setup Wizard
*   **Onboarding Route (`ProtectedRoute.tsx`)**:
    *   If the first user (automatically promoted to admin) logs in and settings are incomplete, they are redirected to `/setup`.
*   **Setup Wizard (`SetupWizardPage.tsx`)**:
    *   A multi-step, cyberpunk-themed setup wizard that guides the admin through configuring Proxmox credentials and LLM keys.
    *   Includes a "Test Connection" step that validates Proxmox reachability in real-time before completing setup.
*   **Admin Panel Settings (`AdminSettingsPage.tsx`)**:
    *   Updated the administrative dashboard to support managing and editing the new `secret` setting types securely.
