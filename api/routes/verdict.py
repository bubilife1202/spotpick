"""Go/No-Go verdict endpoint — exposes the verdict engine directly."""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/verdict/{industry_code}/{district_code}")
async def get_verdict(
    industry_code: str,
    district_code: str,
    budget_max: Annotated[
        Optional[int],
        Query(description="Total startup budget in 만원 (e.g., 5000)"),
    ] = None,
    experience_level: Annotated[
        Optional[str],
        Query(description="beginner, experienced, or expert"),
    ] = None,
    estimated_rent: Annotated[
        Optional[int],
        Query(
            description="Pre-computed monthly rent in 원 (from dashboard). If not provided, computed from data.",
        ),
    ] = None,
):
    """
    Compute Go/No-Go verdict for a specific district.

    Returns the full VerdictResult including:
    - verdict (GO / CAUTION / NO_GO)
    - confidence (0-100)
    - summary (Korean text)
    - reasons (list of factors with data values and thresholds)
    - alternatives (up to 3 alternative districts if NO_GO)
    """
    from api.services.data_service import get_data_service, estimate_rent as calc_rent
    from api.services.verdict_service import compute_verdict

    # Convert total startup budget (만원) to an affordable monthly rent ceiling (원).
    # This aligns the verdict engine's `budget_max` with estimated_rent (원/month).
    rent_budget_max_won: Optional[int] = None
    if budget_max is not None and budget_max > 0:
        try:
            from api.services.krei_data_service import get_startup_investment

            inv = get_startup_investment(industry_code)
            if inv and inv.get("total"):
                startup_total_man = int(inv.get("total") or 0)
                if budget_max < startup_total_man:
                    return {
                        "verdict": "NO_GO",
                        "confidence": 90,
                        "summary": f"NO_GO — 예산이 업종 평균 창업비용에 미달합니다.",
                        "reasons": [
                            {
                                "factor": "예산",
                                "level": "danger",
                                "detail": "예산이 업종 평균 창업비용보다 낮습니다",
                                "data_value": f"{budget_max:,}만원",
                                "threshold": f"평균 {startup_total_man:,}만원 ({str(inv.get('source') or 'KREI 2023')})",
                            }
                        ],
                        "danger_count": 1,
                        "warning_count": 0,
                        "positive_count": 0,
                        "alternatives": [],
                        "data_source": str(inv.get("source") or "KREI 2023"),
                    }
        except Exception:
            # If KREI data is unavailable, proceed without the budget feasibility gate.
            pass

        try:
            from api.routes.dashboard import _budget_to_rent

            _, rent_budget_max_won = _budget_to_rent(
                budget_min=budget_max,
                budget_max=budget_max,
                industry_code=industry_code,
            )
        except Exception:
            rent_budget_max_won = None

    try:
        svc = get_data_service(industry_code)
    except Exception as e:
        logger.exception("Failed to load data service for %s", industry_code)
        raise HTTPException(
            status_code=400, detail=f"Invalid industry_code: {industry_code}"
        ) from e

    # Find the district
    district = svc.get_district(district_code)
    if district is None:
        # Try by name match as fallback
        district = svc.get_district_by_name(district_code)
    if district is None:
        raise HTTPException(status_code=404, detail=f"District not found: {district_code}")

    # Compute estimated rent if not provided
    if estimated_rent is None or estimated_rent <= 0:
        store_count = max(1, int(district.get("store_count", 1) or 1))
        sales_per_store = int(district.get("monthly_sales", 0) or 0) // store_count
        district_type = str(district.get("district_type") or "골목상권")
        code = district.get("district_code")
        pctile = 0.5
        if isinstance(code, str) and code:
            pctile = float(getattr(svc, "_sales_percentile", {}).get(code, 0.5))
        estimated_rent = calc_rent(
            district_type,
            sales_per_store,
            pctile,
            getattr(svc, "_rent_ranges", None),
            industry_code=industry_code,
        )

    # Compute verdict
    result = compute_verdict(
        district=district,
        industry_code=industry_code,
        budget_max=rent_budget_max_won,
        experience_level=experience_level,
        estimated_rent=estimated_rent,
    )

    return result
