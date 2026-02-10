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
        Query(description="Total budget in 만원 (e.g., 5000)"),
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
        estimated_rent = calc_rent(
            district_type,
            sales_per_store,
            0.5,
            industry_code=industry_code,
        )

    # Compute verdict
    result = compute_verdict(
        district=district,
        industry_code=industry_code,
        budget_max=budget_max,
        experience_level=experience_level,
        estimated_rent=estimated_rent,
    )

    return result
