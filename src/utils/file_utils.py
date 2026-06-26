from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_parent_dir(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    target = ensure_parent_dir(path)
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")

