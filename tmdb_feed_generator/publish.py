import json
import os
import tempfile
from pathlib import Path


def write_feed(out_dir: Path, client_id: str, feed: dict) -> Path:
    """Atomic write, so the web server never serves a half-written file and a failed run keeps the last good feed."""
    target_dir = out_dir / client_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "recommendations.json"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=target_dir, suffix=".tmp", delete=False) as handle:
        json.dump(feed, handle, ensure_ascii=False, indent=2)
        temp_name = handle.name
    os.chmod(temp_name, 0o644)
    os.replace(temp_name, target)
    return target
