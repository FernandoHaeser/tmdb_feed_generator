"""Offline transport that answers from JSON files, for tests and for trying the stack without a TMDB key."""

import json
from pathlib import Path


class FixtureTransport:
    def __init__(self, directory: Path):
        self._directory = directory

    def __call__(self, path: str, params: dict[str, str]) -> dict:
        parts = path.strip("/").split("/")
        if parts[0] == "discover":
            providers = params.get("with_watch_providers", "")
            candidates = [f"discover_{parts[1]}_{providers}.json", f"discover_{parts[1]}.json"]
        elif parts[0] == "watch":
            candidates = [f"providers_{parts[2]}.json"]
        else:  # /{type}/{id}/watch/providers
            candidates = [f"watch_providers_{parts[0]}_{parts[1]}.json", "watch_providers_default.json"]

        for name in candidates:
            file = self._directory / name
            if file.is_file():
                return json.loads(file.read_text(encoding="utf-8"))
        raise FileNotFoundError(f"No fixture for {path} (tried {candidates})")

