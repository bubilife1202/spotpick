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
    #
    # Budget feasibility: Instead of hard NO-GO against KREI industry average,
    # we check against cafe-type-specific minimums. A 5,000만원 budget is NO-GO
    # for a standard cafe but perfectly fine for a takeout cafe.
    rent_budget_max_won: Optional[int] = None
    budget_warning_reason = None
    if budget_max is not None and budget_max > 0:
        try:
            if industry_code == "CS100010":
                from api.services.cafe_type_service import MIN_BUDGET_MAN as CAFE_MIN_BUDGETS

                cheapest_min = min(CAFE_MIN_BUDGETS.values())
                if budget_max < cheapest_min:
                    budget_warning_reason = {
                        "factor": "예산",
                        "level": "danger",
                        "detail": f"모든 카페 유형의 최소 예산에 미달합니다 (최소 {cheapest_min:,}만원)",
                        "data_value": f"{budget_max:,}만원",
                        "threshold": f"최소 {cheapest_min:,}만원 (테이크아웃 기준)",
                    }
                else:
                    from api.services.krei_data_service import get_startup_investment

                    inv = get_startup_investment(industry_code)
                    if inv and inv.get("total"):
                        startup_total_man = int(inv.get("total") or 0)
                        if budget_max < startup_total_man:
                            affordable = [t for t, m in CAFE_MIN_BUDGETS.items() if budget_max >= m]
                            budget_warning_reason = {
                                "factor": "예산",
                                "level": "warning",
                                "detail": (
                                    f"업종 평균({startup_total_man:,}만원) 대비 낮지만, "
                                    f"{len(affordable)}개 카페 유형은 가능합니다"
                                ),
                                "data_value": f"{budget_max:,}만원",
                                "threshold": f"평균 {startup_total_man:,}만원 ({str(inv.get('source') or 'KREI 2023')})",
                            }
            else:
                from api.services.krei_data_service import get_startup_investment

                inv = get_startup_investment(industry_code)
                if inv and inv.get("total"):
                    startup_total_man = int(inv.get("total") or 0)
                    if budget_max < startup_total_man:
                        budget_warning_reason = {
                            "factor": "예산",
                            "level": "warning",
                            "detail": "예산이 업종 평균 창업비용보다 낮습니다",
                            "data_value": f"{budget_max:,}만원",
                            "threshold": f"평균 {startup_total_man:,}만원 ({str(inv.get('source') or 'KREI 2023')})",
                        }
        except Exception:
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

    result = compute_verdict(
        district=district,
        industry_code=industry_code,
        budget_max=rent_budget_max_won,
        experience_level=experience_level,
        estimated_rent=estimated_rent,
    )

    if budget_warning_reason:
        budget_level = budget_warning_reason["level"]
        result["reasons"].insert(
            0,
            {
                "factor": str(budget_warning_reason["factor"]),
                "level": "danger" if budget_level == "danger" else "warning",
                "detail": str(budget_warning_reason["detail"]),
                "data_value": str(budget_warning_reason["data_value"]),
                "threshold": str(budget_warning_reason["threshold"]),
            },
        )
        if budget_level == "danger":
            result["danger_count"] += 1
        else:
            result["warning_count"] += 1

    return result
