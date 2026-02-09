"""독립창업 vs 프랜차이즈 비용 산출 서비스."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

COSTS_PATH = Path(__file__).resolve().parent.parent / "data" / "independent_startup_costs.json"

_costs_cache: dict[str, Any] | None = None


def _load_costs() -> dict[str, Any]:
    global _costs_cache
    if _costs_cache is not None:
        return _costs_cache
    try:
        with open(COSTS_PATH, encoding="utf-8") as f:
            _costs_cache = json.load(f)
            return _costs_cache
    except Exception:
        return {}


def calc_independent_cost(
    industry_code: str,
    area_pyeong: int = 15,
    deposit: int = 0,
    monthly_rent: int = 0,
) -> dict[str, Any]:
    """독립창업 총 비용을 산출합니다."""
    costs = _load_costs()
    data = costs.get(industry_code, costs.get("CS100010", {}))

    interior = data.get("interior_per_pyeong", 2_000_000) * area_pyeong
    equipment_list = data.get("equipment", [])
    equipment_total = sum(e.get("cost", 0) for e in equipment_list)
    initial_inventory = data.get("initial_inventory", 3_000_000)
    signage = data.get("signage", 2_000_000)
    misc = data.get("misc", 2_000_000)

    total = interior + equipment_total + initial_inventory + signage + misc + deposit

    return {
        "type": "independent",
        "industry_name": data.get("name", ""),
        "area_pyeong": area_pyeong,
        "breakdown": {
            "interior": interior,
            "equipment": equipment_total,
            "equipment_detail": equipment_list,
            "initial_inventory": initial_inventory,
            "signage": signage,
            "misc": misc,
            "deposit": deposit,
        },
        "total_initial_cost": total,
        "monthly_rent": monthly_rent,
        "monthly_fixed_cost": monthly_rent,
    }


def calc_franchise_cost(
    franchise_data: dict[str, Any],
    area_pyeong: int = 15,
    deposit: int = 0,
    monthly_rent: int = 0,
    interior_per_pyeong: int = 0,
) -> dict[str, Any]:
    """프랜차이즈 총 비용을 산출합니다.

    franchise_data는 공정위 benchmark API 응답의 startup_costs 부분.
    """
    franchise_fee = franchise_data.get("franchise_fee", 0)
    education_fee = franchise_data.get("education_fee", 0)
    other_fee = franchise_data.get("other_fee", 0)
    joining_total = franchise_data.get("total_joining_cost", 0) or (
        franchise_fee + education_fee + other_fee
    )

    interior = interior_per_pyeong * area_pyeong if interior_per_pyeong else 0

    total = joining_total + interior + deposit

    return {
        "type": "franchise",
        "breakdown": {
            "franchise_fee": franchise_fee,
            "education_fee": education_fee,
            "other_fee": other_fee,
            "joining_total": joining_total,
            "interior": interior,
            "deposit": deposit,
        },
        "total_initial_cost": total,
        "monthly_rent": monthly_rent,
        "monthly_fixed_cost": monthly_rent,
    }
