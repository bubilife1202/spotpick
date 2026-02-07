"""Industry configuration loader — reads JSON config files per industry."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

INDUSTRIES_DIR = Path(__file__).parent.parent / "data" / "industries"
DEFAULT_INDUSTRY = "CS100010"


@lru_cache(maxsize=16)
def load_industry_config(code: str = DEFAULT_INDUSTRY) -> dict[str, Any]:
    """Load industry config JSON. Cached after first load."""
    config_path = INDUSTRIES_DIR / f"{code}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Industry config not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def get_available_industries() -> list[dict[str, str]]:
    """Return list of available industry codes and names."""
    industries = []
    for p in sorted(INDUSTRIES_DIR.glob("CS*.json")):
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        industries.append({
            "code": data["code"],
            "name": data["name"],
            "display_name": data.get("display_name", data["name"]),
        })
    return industries
