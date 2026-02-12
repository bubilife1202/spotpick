from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.services.kakao_local_service import search_places_in_area

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/competition")


class NearbyCompetitorItem(BaseModel):
    name: str
    address: str
    distance: int
    category: str


class NearbyCompetitorsResponse(BaseModel):
    keyword: str
    count: int
    competitors: list[NearbyCompetitorItem]


@router.get("/nearby", response_model=NearbyCompetitorsResponse)
async def get_nearby_competitors(
    keyword: Annotated[str, Query(..., min_length=1, description="검색 키워드 (e.g., 만화카페)")],
    x: Annotated[str, Query(..., description="경도")],
    y: Annotated[str, Query(..., description="위도")],
    radius: Annotated[int, Query(1000, ge=1, le=20000, description="검색 반경 (미터)")] = 1000,
    industry_code: Annotated[str, Query("CS100010", description="업종 코드")] = "CS100010",
) -> NearbyCompetitorsResponse:
    try:
        lng = float(x)
        lat = float(y)
    except ValueError:
        logger.warning("Invalid coordinates for nearby competition search: x=%s, y=%s", x, y)
        return NearbyCompetitorsResponse(keyword=keyword, count=0, competitors=[])

    try:
        places = await search_places_in_area(
            lat=lat,
            lng=lng,
            keyword=keyword,
            radius=radius,
            industry_code=industry_code,
            size=15,
            max_pages=1,
        )
    except Exception as exc:
        logger.error("Nearby competition search failed: %s", exc, exc_info=True)
        return NearbyCompetitorsResponse(keyword=keyword, count=0, competitors=[])

    competitors = [
        NearbyCompetitorItem(
            name=p.get("place_name", ""),
            address=p.get("road_address") or p.get("address", ""),
            distance=int(p.get("distance", 0) or 0),
            category=p.get("category_name", ""),
        )
        for p in places
    ]

    return NearbyCompetitorsResponse(
        keyword=keyword,
        count=len(competitors),
        competitors=competitors,
    )
