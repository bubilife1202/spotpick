"""
주변 카페 검색 API — 카카오 로컬 연동
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.kakao_local_service import get_kakao_local_service

router = APIRouter(prefix="/nearby")


class NearbyStoreItem(BaseModel):
    id: str
    name: str
    category: str
    address: str
    road_address: str
    phone: str
    x: float
    y: float
    place_url: str
    distance: int


class NearbyResponse(BaseModel):
    stores: list[NearbyStoreItem]
    total_count: int
    query: str


@router.get("/cafes", response_model=NearbyResponse)
async def search_nearby_cafes(
    query: str,
    x: Optional[float] = None,
    y: Optional[float] = None,
    radius: int = 1000,
    size: int = 15,
    page: int = 1,
) -> NearbyResponse:
    service = get_kakao_local_service()
    if not service.available:
        raise HTTPException(status_code=503, detail="카카오 로컬 API 키가 설정되지 않았습니다")

    try:
        result = await service.search_nearby_cafes(
            query=query, x=x, y=y, radius=radius, size=size, page=page,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"카카오 API 호출 실패: {e}")

    return NearbyResponse(
        stores=[NearbyStoreItem(**s) for s in result["stores"]],
        total_count=result["total_count"],
        query=result["query"],
    )


@router.get("/parking", response_model=NearbyResponse)
async def search_nearby_parking(
    x: float,
    y: float,
    radius: int = 500,
    size: int = 15,
) -> NearbyResponse:
    """주변 주차장 검색 (카카오 로컬 PK6 카테고리).

    Notes:
    - x=경도(lng), y=위도(lat)
    - radius 기본 500m
    """
    service = get_kakao_local_service()
    if not service.available:
        raise HTTPException(status_code=503, detail="카카오 로컬 API 키가 설정되지 않았습니다")

    try:
        result = await service.search_nearby_parking(
            x=x,
            y=y,
            radius=radius,
            size=size,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"카카오 API 호출 실패: {e}")

    return NearbyResponse(
        stores=[NearbyStoreItem(**s) for s in result["stores"]],
        total_count=result["total_count"],
        query=result["query"],
    )
