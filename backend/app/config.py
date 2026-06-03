# =============================================================================
# app/config.py
# =============================================================================
# The single runtime-configuration resolver.
#
# Operational config (Proxmox connector, LLM provider, Guacamole, VM creds) used
# to be read straight from os.getenv scattered across the codebase. It now lives
# in the system_settings table so it can be configured from the admin UI /
# first-run setup wizard. This module is the one place that resolves a value:
#
#     DB (system_settings)  →  env var fallback  →  caller default
#
# The env fallback keeps everything working during migration (and lets the
# bootstrap .env still drive the app until the wizard is used). Secret values
# come back already DECRYPTED from database.get_setting().
#
# A short-TTL cache avoids a DB round-trip on every Proxmox/LLM call. A
# monotonically increasing "generation" counter lets long-lived clients (the
# shared ProxmoxClient) cheaply detect that config changed and rebuild
# themselves — invalidate_cache() is called whenever a setting is written.
# =============================================================================

import logging
import os
import threading
import time
from typing import Any, Optional

from db import database
from db.config_registry import REGISTRY_BY_KEY, REGISTRY_BY_ENV

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 30.0

_lock = threading.Lock()
_cache: dict[str, tuple[Any, float]] = {}   # setting_key -> (value, expiry_ts)
_generation = 0


def _resolve_key(name: str) -> tuple[str, str]:
    """
    Accept either a setting key ("proxmox.host") or its env name
    ("PROXMOX_HOST") and return (setting_key, env_name).
    """
    ck = REGISTRY_BY_KEY.get(name) or REGISTRY_BY_ENV.get(name)
    if ck is not None:
        return ck.key, ck.env
    return name, name  # unknown key — treat the name as both


def _db_value(setting_key: str) -> Any:
    """Read one setting from the DB through the TTL cache. None on any failure."""
    now = time.monotonic()
    with _lock:
        cached = _cache.get(setting_key)
        if cached is not None and cached[1] > now:
            return cached[0]
    # Miss — read outside the lock (DB call); tolerate the table not existing
    # yet (very early startup) by falling through to the env fallback.
    try:
        value = database.get_setting(setting_key)
    except Exception as exc:  # noqa: BLE001 - config must degrade, never crash
        logger.debug("config: DB read failed for %s (%s); using env fallback.",
                     setting_key, exc)
        value = None
    with _lock:
        _cache[setting_key] = (value, now + _CACHE_TTL_SECONDS)
    return value


def get_config(name: str, default: Optional[Any] = None) -> Any:
    """
    Resolve a config value: DB first, then env var, then `default`.

    `name` may be the setting key or the env var name. Empty strings count as
    "unset" and fall through (so an unconfigured secret falls back to env).
    """
    setting_key, env_name = _resolve_key(name)

    value = _db_value(setting_key)
    if value not in (None, ""):
        return value

    env_value = os.getenv(env_name)
    if env_value not in (None, ""):
        return env_value

    return default


def get_config_str(name: str, default: str = "") -> str:
    value = get_config(name, default)
    return default if value is None else str(value)


def get_config_int(name: str, default: int = 0) -> int:
    value = get_config(name, None)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_config_bool(name: str, default: bool = False) -> bool:
    value = get_config(name, None)
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def invalidate_cache() -> None:
    """
    Drop the cache and bump the generation counter. Call after writing any
    setting so the next read sees fresh data and config-dependent singletons
    (ProxmoxClient) rebuild. Cheap and safe to call often.
    """
    global _generation
    with _lock:
        _cache.clear()
        _generation += 1
    logger.debug("config cache invalidated (generation now %d).", _generation)


def config_generation() -> int:
    """Current config generation; changes whenever a setting is written."""
    with _lock:
        return _generation
