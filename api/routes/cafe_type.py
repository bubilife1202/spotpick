"""Cafe type recommendation endpoint.

Returns a ranked list of cafe business models (types) for a single district.
"""

from __future__ import annotations

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/cafe-type/{industry_code}/{district_code}")
async def get_cafe_type(
    industry_code: str,
    district_code: str,
    budget_max: Annotated[
        Optional[int],
        Query(description="Total startup budget in 만원 (e.g., 8000)"),
    ] = None,
    experience_level: Annotated[
        Optional[str],
        Query(description="beginner, experienced, or expert"),
    ] = None,
):
    from api.services.cafe_type_service import compute_cafe_type_recommendation
    from api.services.data_service import get_data_service

    try:
        svc = get_data_service(industry_code)
    except Exception as e:
        logger.exception("Failed to load data service for %s", industry_code)
        raise HTTPException(
            status_code=400, detail=f"Invalid industry_code: {industry_code}"
        ) from e

    district = svc.get_district(district_code)
    if district is None:
        district = svc.get_district_by_name(district_code)
    if district is None:
        raise HTTPException(status_code=404, detail=f"District not found: {district_code}")

    return compute_cafe_type_recommendation(
        industry_code=industry_code,
        district=district,
        budget_max_man=budget_max,
        experience_level=experience_level,
    )
