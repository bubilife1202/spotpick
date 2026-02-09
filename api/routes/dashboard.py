"""Dashboard recommendations endpoint — filtered TOP N without chat."""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Query

from api.services.data_service import get_data_service, estimate_rent

router = APIRouter()

logger = logging.getLogger(__name__)


def _verdict(prob: float) -> str:
    if prob >= 0.65:
        return "추천"
    if prob >= 0.45:
        return "주의"
    return "비추천"


def _budget_to_rent(
    budget_min: int,
    budget_max: int,
    industry_code: str,
) -> tuple[int | None, int | None]:
    """Convert total budget (만원) to affordable monthly rent range (원).

    Uses KREI startup investment data when available, falls back to
    simulation-service defaults.
    """
    # Try KREI data first
    startup_costs_man: int | None = None
    try:
        from api.services.krei_data_service import get_startup_investment
        inv = get_startup_investment(industry_code)
        if inv and inv.get("total"):
            startup_costs_man = int(inv["total"])  # already in 만원
    except Exception:
        pass

    # Fallback: simulation service defaults (원 -> 만원)
    if startup_costs_man is None:
        from api.services.simulation_service import (
            EQUIPMENT_COST,
            INITIAL_INVENTORY,
            PERMITS_AND_MISC,
            DISTRICT_TYPE_FACTORS,
        )
        # Use 골목상권 mid-range as default
        factors = DISTRICT_TYPE_FACTORS.get("골목상권", {})
        deposit = factors.get("deposit_mult", 10) * 100  # ~100만 * 10 = 1000만
        interior = factors.get("interior_per_pyeong", 1_800_000) * 15 / 10_000  # 15평
        equip = sum(
            (lo + hi) / 2 for lo, hi in EQUIPMENT_COST.values()
        ) / 10_000
        inventory = sum(INITIAL_INVENTORY) / 2 / 10_000
        misc = sum(PERMITS_AND_MISC) / 2 / 10_000
        startup_costs_man = int(deposit + interior + equip + inventory + misc)

    # remaining budget / 12 months = affordable rent
    remaining_min = max(0, budget_min - startup_costs_man)
    remaining_max = max(0, budget_max - startup_costs_man)

    # Convert 만원/month to 원/month
    rent_min_won = int(remaining_min / 12 * 10_000) if remaining_min > 0 else None
    rent_max_won = int(remaining_max / 12 * 10_000) if remaining_max > 0 else None

    logger.info(
        "Budget %d~%d만 → startup %d만 → rent %s~%s원",
        budget_min, budget_max, startup_costs_man,
        rent_min_won, rent_max_won,
    )

    return rent_min_won, rent_max_won


@router.get("/recommendations/dashboard")
async def dashboard_recommendations(
    industry_code: str = Query("CS100010", description="업종 코드"),
    rent_min: Optional[int] = Query(None, description="최소 임대료 (만원 단위, 예: 150)"),
    rent_max: Optional[int] = Query(None, description="최대 임대료 (만원 단위, 예: 300)"),
    budget_min: Optional[int] = Query(None, description="최소 총예산 (만원 단위, 예: 5000)"),
    budget_max: Optional[int] = Query(None, description="최대 총예산 (만원 단위, 예: 10000)"),
    district_filter: Optional[str] = Query(None, description="상권명 부분 검색 (예: 강남, 마포)"),
    area_type: Optional[str] = Query(None, description="상권 유형 (골목상권, 발달상권, 전통시장, 관광특구)"),
    limit: int = Query(5, ge=1, le=20, description="결과 수 (최대 20)"),
):
    """
    대시보드용 추천 상권 목록.

    채팅 없이 필터 조건에 맞는 TOP N 상권을 반환합니다.
    rent_min/rent_max는 만원 단위입니다 (예: 150 = 150만원).
    budget_min/budget_max가 제공되면 총예산에서 창업비용을 빼고 월세로 변환합니다.
    """
    svc = get_data_service(industry_code=industry_code)

    # Scorecard service (lazy init with districts)
    from api.services.scorecard_service import get_scorecard_service
    sc_svc = get_scorecard_service(industry_code)
    if not sc_svc._districts:
        sc_svc.set_districts(svc.districts)

    # Budget-to-rent conversion if budget params provided
    if budget_min is not None or budget_max is not None:
        b_min = budget_min if budget_min is not None else 3000
        b_max = budget_max if budget_max is not None else 20000
        converted_rent_min, converted_rent_max = _budget_to_rent(b_min, b_max, industry_code)
        # Use converted values (override any rent params)
        rent_min_won = converted_rent_min
        rent_max_won = converted_rent_max
    else:
        # Convert 만원 to 원
        rent_min_won = rent_min * 10_000 if rent_min is not None else None
        rent_max_won = rent_max * 10_000 if rent_max is not None else None

    candidates: list[dict[str, Any]] = []

    for d in svc.districts:
        # Area type filter
        if area_type and d.get("district_type") != area_type:
            continue

        # District name filter (partial match)
        if district_filter and district_filter not in d.get("district_name", ""):
            continue

        # Estimate rent
        store_count = max(1, d.get("store_count", 1))
        sales_per_store = int(d["monthly_sales"] / store_count)
        pctile = svc._sales_percentile.get(d["district_code"], 0.5)
        est_rent = estimate_rent(
            d["district_type"], sales_per_store, pctile,
            svc._rent_ranges, industry_code=industry_code,
        )

        # Rent range filter — soft: flag but don't exclude
        budget_fit = True
        if rent_min_won is not None and est_rent < rent_min_won:
            budget_fit = False
        if rent_max_won is not None and est_rent > rent_max_won:
            budget_fit = False

        # Success probability
        prob = svc._calculate_success_probability(d)

        # Scorecard total
        scorecard_total = sc_svc._quick_score(d)

        # Key factors
        key_factors = svc._extract_key_factors(d)

        candidates.append({
            "district": d,
            "estimated_rent": est_rent,
            "success_probability": prob,
            "scorecard_total": scorecard_total,
            "key_factors": key_factors,
            "budget_fit": budget_fit,
        })

    total_available = len(candidates)

    # Sort: budget-fitting first, then by success probability descending
    candidates.sort(key=lambda c: (c["budget_fit"], c["success_probability"]), reverse=True)

    results = []
    for rank, c in enumerate(candidates[:limit], 1):
        d = c["district"]
        store_count = max(1, d.get("store_count", 1))
        sales_per_store = int(d["monthly_sales"] / store_count)

        results.append({
            "rank": rank,
            "district_code": str(d.get("district_code", "")),
            "district_name": d.get("district_name", ""),
            "district_type": d.get("district_type", ""),
            "success_probability": c["success_probability"],
            "verdict": _verdict(c["success_probability"]),
            "estimated_rent": c["estimated_rent"],
            "monthly_sales": d.get("monthly_sales", 0),
            "sales_per_store": sales_per_store,
            "store_count": d.get("store_count", 0),
            "survival_rate": min(d.get("survival_rate", 0), 1.0),
            "peak_time": d.get("peak_time", ""),
            "peak_day": d.get("peak_day", ""),
            "main_age_group": d.get("main_age_group", ""),
            "foot_traffic_total": d.get("foot_traffic_total", 0),
            "worker_total": d.get("worker_total", 0),
            "subway_count": d.get("facility_subway", 0),
            "change_indicator": d.get("change_indicator", ""),
            "lat": d.get("lat", 0.0),
            "lng": d.get("lng", 0.0),
            "scorecard_total": c["scorecard_total"],
            "key_factors": c["key_factors"],
            "budget_fit": c.get("budget_fit", True),
        })

    filters_applied: dict[str, Any] = {"industry_code": industry_code}
    if budget_min is not None:
        filters_applied["budget_min"] = budget_min
    if budget_max is not None:
        filters_applied["budget_max"] = budget_max
    if rent_min is not None:
        filters_applied["rent_min"] = rent_min
    if rent_max is not None:
        filters_applied["rent_max"] = rent_max
    if district_filter:
        filters_applied["district_filter"] = district_filter
    if area_type:
        filters_applied["area_type"] = area_type

    return {
        "results": results,
        "total_available": total_available,
        "filters_applied": filters_applied,
    }
