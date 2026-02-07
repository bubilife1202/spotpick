"""Trademark conflict check API route."""
from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/trademark/check")
async def check_trademark(
    name: str = Query(..., min_length=1, description="상호명/브랜드명"),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """Check a proposed brand name against known trademarks for the industry."""
    from api.services.trademark_service import get_trademark_service

    svc = get_trademark_service(industry_code)
    result = svc.check(name)
    return result
