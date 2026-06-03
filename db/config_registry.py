# =============================================================================
# db/config_registry.py
# =============================================================================
# Single source of truth for the runtime configuration that used to live in the
# root .env and is now stored in the system_settings table (editable in the
# admin UI / first-run setup wizard).
#
# Both layers read this list:
#   - db/database.py        seeds these keys into system_settings on init_db()
#   - backend/app/config.py resolves a value (DB first, then env fallback)
#
# IMPORTANT: this registry does NOT include bootstrap config that must exist
# before the DB is reachable (DB_*, CELERY_BROKER_URL, JWT_SECRET_KEY,
# SETTINGS_ENCRYPTION_KEY). Those stay in docker-compose / .env by necessity —
# a setting can't live inside the database it unlocks.
# =============================================================================

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigKey:
    """One configurable value: its setting key, env fallback, type and seed."""
    key: str          # system_settings primary key, e.g. "proxmox.host"
    env: str          # env var used for fallback / migration, e.g. "PROXMOX_HOST"
    value_type: str   # 'string' | 'integer' | 'boolean' | 'secret'
    default: str      # seed value stored in system_settings (TEXT). '' for secrets.
    description: str

    @property
    def is_secret(self) -> bool:
        return self.value_type == "secret"


# Order here is the order the setup wizard / admin UI will show them.
CONFIG_REGISTRY: list[ConfigKey] = [
    # ── Proxmox connector (Kanban #54) ───────────────────────────────────────
    ConfigKey("proxmox.host", "PROXMOX_HOST", "string", "",
              "Proxmox host or IP (e.g. 192.168.1.57)"),
    ConfigKey("proxmox.node", "PROXMOX_NODE", "string", "proxmox",
              "Proxmox node name (e.g. proxmox / pve)"),
    ConfigKey("proxmox.verify_ssl", "PROXMOX_VERIFY_SSL", "boolean", "false",
              "Verify the Proxmox TLS certificate (false for self-signed lab certs)"),
    ConfigKey("proxmox.token_id", "PROXMOX_TOKEN_ID", "string", "",
              "Proxmox API token id, e.g. root@pam!privatecloud (preferred auth)"),
    ConfigKey("proxmox.token_secret", "PROXMOX_TOKEN_SECRET", "secret", "",
              "Proxmox API token secret (UUID)"),
    ConfigKey("proxmox.user", "PROXMOX_USER", "string", "root@pam",
              "Proxmox username for legacy ticket auth (used if no token)"),
    ConfigKey("proxmox.password", "PROXMOX_PASSWORD", "secret", "",
              "Proxmox password for legacy ticket auth"),
    ConfigKey("proxmox.golden_image_vmid", "GOLDEN_IMAGE_VMID", "integer", "9000",
              "VMID of the Linux cloud-init golden template"),
    ConfigKey("proxmox.windows_template_vmid", "WINDOWS_TEMPLATE_VMID", "integer", "9001",
              "VMID of the Windows 11 golden template"),

    # ── VM guest credentials ─────────────────────────────────────────────────
    ConfigKey("vm.default_username", "VM_DEFAULT_USERNAME", "string", "ubuntu",
              "Default SSH username baked into the Linux golden image"),
    ConfigKey("vm.default_password", "VM_DEFAULT_PASSWORD", "secret", "",
              "Default SSH password for the Linux golden image"),
    ConfigKey("vm.windows_username", "VM_WINDOWS_USERNAME", "string", "",
              "Windows golden-image username (falls back to the Linux default)"),
    ConfigKey("vm.windows_password", "VM_WINDOWS_PASSWORD", "secret", "",
              "Windows golden-image password"),

    # ── LLM / AI ChatOps provider (Kanban #55) ───────────────────────────────
    ConfigKey("llm.api_key", "OPENAI_API_KEY", "secret", "",
              "OpenRouter / OpenAI API key for the AI ChatOps + RAG agent"),
    ConfigKey("llm.base_url", "OPENAI_BASE_URL", "string", "https://openrouter.ai/api/v1",
              "LLM API base URL (OpenAI-compatible)"),
    ConfigKey("llm.model", "OPENAI_MODEL", "string", "openai/gpt-4o-mini",
              "LLM model id"),

    # ── Apache Guacamole (remote desktop) ────────────────────────────────────
    ConfigKey("guacamole.public_url", "GUACAMOLE_PUBLIC_URL", "string",
              "http://localhost:9080/guacamole",
              "Browser-facing Guacamole URL (rewritten per-device on the frontend)"),
    ConfigKey("guacamole.admin_user", "GUACAMOLE_ADMIN_USER", "string", "guacadmin",
              "Guacamole admin username"),
    ConfigKey("guacamole.admin_password", "GUACAMOLE_ADMIN_PASSWORD", "secret", "",
              "Guacamole admin password"),

    # ── Misc ─────────────────────────────────────────────────────────────────
    ConfigKey("clone.lease_hours", "CLONE_LEASE_HOURS", "integer", "0",
              "Default lease (hours) for distributed clones; 0 = no expiry"),

    # ── Setup state (drives the first-run wizard) ────────────────────────────
    ConfigKey("setup.completed", "PRIVATECLOUD_SETUP_COMPLETED", "boolean", "false",
              "Whether an admin has completed the first-run setup wizard"),
]

# Fast lookups
REGISTRY_BY_KEY: dict[str, ConfigKey] = {ck.key: ck for ck in CONFIG_REGISTRY}
REGISTRY_BY_ENV: dict[str, ConfigKey] = {ck.env: ck for ck in CONFIG_REGISTRY}

# The subset the setup wizard must fill before the platform is usable.
REQUIRED_FOR_SETUP: tuple[str, ...] = (
    "proxmox.host",
    "proxmox.node",
)
