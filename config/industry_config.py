"""Industry configuration loader — reads JSON config files per industry."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

INDUSTRIES_DIR = Path(__file__).parent.parent / "data" / "industries"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
DEFAULT_INDUSTRY = "CS100010"


@lru_cache(maxsize=16)
def load_industry_config(code: str = DEFAULT_INDUSTRY) -> dict[str, Any]:
    """Load industry config JSON. Cached after first load."""
    config_path = INDUSTRIES_DIR / f"{code}.json"
    if not config_path.exists():
        raise FileNotFoundError(f"Industry config not found: {config_path}")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def get_available_industries() -> list[dict[str, Any]]:
    """Return list of available industry codes and names.

    NOTE: This endpoint is used by the frontend to decide what to enable.
    We treat an industry as "data_available" when its processed districts file exists.
    """
    industries: list[dict[str, Any]] = []
    for p in sorted(INDUSTRIES_DIR.glob("CS*.json")):
        with open(p, encoding="utf-8") as f:
            data = json.load(f)

        code = str(data.get("code") or "")
        districts_file = PROCESSED_DIR / f"{code}_districts.json"
        data_available = districts_file.exists() and districts_file.stat().st_size > 10

        industries.append(
            {
                "code": code,
                "name": str(data.get("name") or ""),
                "display_name": str(data.get("display_name") or data.get("name") or code),
                "icon": str(data.get("icon") or "🏪"),
                "color": str(data.get("color") or "blue"),
                "data_available": bool(data_available),
            }
        )
    return industries
