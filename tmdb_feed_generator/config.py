"""Per-client settings, one JSON file per client in `clients/`."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from tmdb_feed_generator.providers import PROVIDERS, Provider

CLIENT_ID_PATTERN = re.compile(r"^[a-z0-9_-]+$")


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ClientConfig:
    client_id: str
    providers: tuple[Provider, ...]
    region: str = "BR"
    language: str = "pt-BR"
    hero_count: int = 5
    row_size: int = 12
    per_provider_rows: bool = True
    # The hero favours titles released within this many days; 0 turns that off (most popular of all time).
    hero_max_age_days: int = 730


def load_client(path: Path) -> ClientConfig:
    client_id = path.stem
    if not CLIENT_ID_PATTERN.match(client_id):
        raise ConfigError(f"Invalid client id '{client_id}' (use a-z, 0-9, '-' and '_')")

    raw = json.loads(path.read_text(encoding="utf-8"))
    keys = raw.get("providers") or []
    unknown = [key for key in keys if key not in PROVIDERS]
    if not keys or unknown:
        raise ConfigError(f"{path.name}: 'providers' must be non-empty and known; unknown: {unknown}")

    return ClientConfig(
        client_id=client_id,
        providers=tuple(PROVIDERS[key] for key in keys),
        region=_text(raw, "region", "BR", r"^[A-Z]{2}$"),
        language=_text(raw, "language", "pt-BR", r"^[a-z]{2}-[A-Z]{2}$"),
        hero_count=_bounded(raw, "heroCount", 5, 1, 10),
        row_size=_bounded(raw, "rowSize", 12, 4, 20),
        per_provider_rows=bool(raw.get("perProviderRows", True)),
        hero_max_age_days=_bounded(raw, "heroMaxAgeDays", 730, 0, 3650),
    )


def load_clients(directory: Path) -> list[ClientConfig]:
    return [load_client(path) for path in sorted(directory.glob("*.json"))]


def _text(raw: dict, key: str, default: str, pattern: str) -> str:
    value = raw.get(key, default)
    if not isinstance(value, str) or not re.match(pattern, value):
        raise ConfigError(f"'{key}' is invalid: {value!r}")
    return value


def _bounded(raw: dict, key: str, default: int, low: int, high: int) -> int:
    value = raw.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ConfigError(f"'{key}' must be an integer between {low} and {high}")
    return value
