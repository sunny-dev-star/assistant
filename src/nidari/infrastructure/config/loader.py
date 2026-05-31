"""Load YAML configuration from config.yaml."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

# Maps flat Settings field names to dotted paths inside merged module config.
_FIELD_PATHS: dict[str, str] = {
    "APP_NAME": "app.name",
    "APP_VERSION": "app.version",
    "ENV": "app.env",
    "DEBUG": "app.debug",
    "DATABASE_URL": "database.url",
    "DATABASE_POOL_SIZE": "database.pool_size",
    "REDIS_URL": "redis.url",
    "DEEPSEEK_API_URL": "llm.deepseek.api_url",
    "DEEPSEEK_API_KEY": "llm.deepseek.api_key",
    "DEEPSEEK_MODEL": "llm.deepseek.model",
    "DEEPSEEK_MAX_TOKENS": "llm.deepseek.max_tokens",
    "DEEPSEEK_TEMPERATURE": "llm.deepseek.temperature",
    "DIFY_API_URL": "llm.dify.api_url",
    "DIFY_API_KEY": "llm.dify.api_key",
    "MCP_ENABLED": "mcp.enabled",
    "MCP_SERVERS": "mcp.servers",
    "AUTH_ENABLED": "auth.enabled",
    "SECRET_KEY": "auth.secret_key",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "auth.access_token_expire_minutes",
    "CORE_API_URL": "bff.core_api_url",
    "INTERNAL_TOKEN": "bff.internal_token",
    "BFF_JWT_SECRET": "bff.jwt_secret",
    "BFF_ACCESS_TOKEN_TTL": "bff.access_token_ttl",
    "BFF_REFRESH_TOKEN_TTL": "bff.refresh_token_ttl",
    "PROMETHEUS_ENABLED": "monitoring.prometheus_enabled",
    "LOG_LEVEL": "logging.level",
    "LOG_FORMAT": "logging.format",
    "LOG_DIR": "logging.dir",
    "LOG_FILE": "logging.file",
    "LOG_MAX_BYTES": "logging.max_bytes",
    "LOG_BACKUP_COUNT": "logging.backup_count",
    "LOG_TO_CONSOLE": "logging.to_console",
    "LOG_TO_FILE": "logging.to_file",
    "FEISHU_WEBHOOK_URL": "alerting.feishu_webhook_url",
}

CONFIG_FILENAME = "config.yaml"

_config_path: Path | None = None


def project_root() -> Path:
    """Repository root (parent of src/ in dev layout)."""
    here = Path(__file__).resolve()
    return here.parents[4]


def default_config_path() -> Path:
    """Resolve default config.yaml for dev (src/) and Docker (/app) layouts."""
    here = Path(__file__).resolve()
    candidates = (
        here.parents[3] / "res" / "conf" / CONFIG_FILENAME,
        here.parents[4] / "res" / "conf" / CONFIG_FILENAME,
    )
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def set_config_path(config_path: str | Path | None) -> Path:
    """Set active configuration file path (call before loading settings)."""
    global _config_path
    if config_path is None:
        _config_path = default_config_path()
    else:
        _config_path = Path(config_path).expanduser().resolve()
    return _config_path


def get_config_path() -> Path:
    """Return active configuration file path."""
    global _config_path
    if _config_path is None:
        return set_config_path(None)
    return _config_path


def load_yaml_modules(config_path: Path | None = None) -> dict[str, Any]:
    """Load module sections from config.yaml."""
    path = config_path or get_config_path()
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle) or {}
    if not isinstance(document, dict):
        return {}
    return document


def _get_by_path(data: dict[str, Any], dotted: str) -> Any:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def flatten_to_settings_fields(modules: dict[str, Any]) -> dict[str, Any]:
    """Convert nested module config to flat Settings field names."""
    flat: dict[str, Any] = {}
    for field_name, path in _FIELD_PATHS.items():
        value = _get_by_path(modules, path)
        if value is not None:
            flat[field_name] = value
    return flat


def normalize_mcp_servers(value: Any) -> str | list:
    """Keep list in YAML; accept JSON string from env override."""
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        try:
            parsed = json.loads(stripped)
            return parsed if isinstance(parsed, list) else value
        except json.JSONDecodeError:
            return value
    return value


def load_flat_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load YAML and return flat dict for Settings initialization."""
    modules = load_yaml_modules(config_path)
    flat = flatten_to_settings_fields(modules)
    if "MCP_SERVERS" in flat:
        flat["MCP_SERVERS"] = normalize_mcp_servers(flat["MCP_SERVERS"])
    flat["_modules"] = modules
    return flat


def get_module_config(module: str, config_path: Path | None = None) -> dict[str, Any]:
    """Return raw config dict for a single module (e.g. 'logging', 'bff')."""
    modules = load_yaml_modules(config_path)
    value = modules.get(module, {})
    return value if isinstance(value, dict) else {}
