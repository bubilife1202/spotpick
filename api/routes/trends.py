"""
Naver DataLab Search Trends API Routes

Endpoints:
- GET /api/v1/trends/search - Get search trend for keywords
- GET /api/v1/trends/compare - Compare multiple keywords
- GET /api/v1/trends/district - Compare districts for a base keyword
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Any

from ..services.trend_service import get_trend_service

logger = logging.getLogger(__name__)

router = APIRouter()


class TrendResponse(BaseModel):
    """Response model for trend data"""
    keywords: list[str] = Field(..., description="Keywords analyzed")
    period: dict[str, str] = Field(..., description="Date range (start, end)")
    trends: list[dict[str, Any]] = Field(..., description="Trend data for each keyword")
    summary: dict[str, Any] | None = Field(None, description="Summary insights")


@router.get("/trends/search", response_model=dict[str, Any])
async def get_search_trend(
    keyword: str = Query(..., description="Keyword to search (e.g., '강남 카페')"),
    months: int = Query(12, ge=1, le=60, description="Number of months to analyze (1-60)"),
    device: str = Query("", pattern="^(|pc|mo)$", description="Device filter: '', 'pc', or 'mo'")
) -> dict[str, Any]:
    """
    Get search trend for a single keyword.

    Example: GET /api/v1/trends/search?keyword=강남 카페&months=12

    Returns:
        Naver DataLab API response with monthly trend data
    """
    try:
        service = get_trend_service()
        result = await service.get_search_trend(
            keywords=[keyword],
            device=device
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to fetch trend data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


@router.get("/trends/compare", response_model=TrendResponse)
async def compare_keywords(
    keywords: str = Query(
        ...,
        description="Comma-separated keywords to compare (max 5, e.g., '강남카페,홍대카페,이태원카페')"
    ),
    months: int = Query(12, ge=1, le=60, description="Number of months to analyze (1-60)"),
    device: str = Query("", pattern="^(|pc|mo)$", description="Device filter: '', 'pc', or 'mo'")
) -> dict[str, Any]:
    """
    Compare search trends for multiple keywords.

    Example: GET /api/v1/trends/compare?keywords=강남카페,홍대카페,이태원카페&months=12

    Returns:
        Normalized comparison data with ranking and insights
    """
    try:
        # Parse comma-separated keywords
        keyword_list = [k.strip() for k in keywords.split(",") if k.strip()]

        if not keyword_list:
            raise HTTPException(status_code=400, detail="No valid keywords provided")

        if len(keyword_list) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 keywords allowed")

        service = get_trend_service()
        result = await service.compare_keywords(
            keywords=keyword_list,
            months=months,
            device=device
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to compare keywords: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")


@router.get("/trends/district", response_model=TrendResponse)
async def compare_districts(
    keyword: str = Query(..., description="Base keyword (e.g., '카페')"),
    districts: str = Query(
        ...,
        description="Comma-separated district names (max 5, e.g., '강남,홍대,이태원')"
    ),
    months: int = Query(12, ge=1, le=60, description="Number of months to analyze (1-60)")
) -> dict[str, Any]:
    """
    Compare search trends across districts for a base keyword.

    Example: GET /api/v1/trends/district?keyword=카페&districts=강남,홍대,이태원&months=12

    This will compare trends for "강남 카페", "홍대 카페", "이태원 카페"

    Returns:
        District-wise trend comparison data
    """
    try:
        # Parse comma-separated districts
        district_list = [d.strip() for d in districts.split(",") if d.strip()]

        if not district_list:
            raise HTTPException(status_code=400, detail="No valid districts provided")

        if len(district_list) > 5:
            raise HTTPException(status_code=400, detail="Maximum 5 districts allowed")

        service = get_trend_service()
        result = await service.get_district_trend(
            base_keyword=keyword,
            districts=district_list,
            months=months
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to compare districts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
