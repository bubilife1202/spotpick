"""Scorecard API — transparent, explainable district scoring."""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/scorecard/{industry_code}/ranking")
async def get_ranking(
    industry_code: str,
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get ranked list of all districts by scorecard total score."""
    from api.services.scorecard_service import get_scorecard_service
    from api.services.data_service import get_data_service

    try:
        data_svc = get_data_service(industry_code)
        scorecard_svc = get_scorecard_service(industry_code)

        if not scorecard_svc._districts:
            scorecard_svc.set_districts(data_svc.districts)

        results = scorecard_svc.rank_all(limit=limit, offset=offset)
        return {
            "industry_code": industry_code,
            "total": len(data_svc.districts),
            "limit": limit,
            "offset": offset,
            "results": results,
        }

    except Exception as e:
        logger.error(f"Scorecard ranking error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


@router.get("/scorecard/{industry_code}/{district_code}")
async def get_district_scorecard(
    industry_code: str,
    district_code: str,
):
    """Get detailed scorecard for a single district."""
    from api.services.scorecard_service import get_scorecard_service
    from api.services.data_service import get_data_service

    try:
        data_svc = get_data_service(industry_code)
        scorecard_svc = get_scorecard_service(industry_code)

        # Ensure scorecard has districts loaded
        if not scorecard_svc._districts:
            scorecard_svc.set_districts(data_svc.districts)

        district = data_svc.get_district(district_code)
        if not district:
            raise HTTPException(status_code=404, detail=f"District {district_code} not found")

        result = scorecard_svc.score_district(district)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scorecard district error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
