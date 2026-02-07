"""공정거래위원회 가맹사업 데이터 API — 실제 창업비용 벤치마크"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/franchise")

VALID_INDUSTRY_CODES = {
    f"CS10000{i}" for i in range(1, 10)
} | {"CS100010"}


def _validate_industry_code(industry_code: str) -> None:
    if industry_code not in VALID_INDUSTRY_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 업종 코드입니다: {industry_code} (CS100001~CS100010)",
        )


@router.get("/benchmark/{industry_code}")
async def get_benchmark(industry_code: str):
    """업종별 공정위 가맹사업 벤치마크 데이터 통합 조회"""
    _validate_industry_code(industry_code)

    from api.services.franchise_data_service import get_franchise_benchmark

    try:
        result = await get_franchise_benchmark(industry_code)
        return result
    except Exception as e:
        logger.error(f"Franchise benchmark error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="공정위 데이터 조회 중 오류가 발생했습니다.",
        )


@router.get("/startup-costs/{industry_code}")
async def get_startup_costs(
    industry_code: str,
    year: Optional[str] = Query(None, description="조회 연도 (미지정 시 최근 연도)"),
):
    """업종별 가맹사업 창업비용 상세 조회"""
    _validate_industry_code(industry_code)

    from api.services.franchise_data_service import fetch_franchise_startup_costs

    try:
        results = await fetch_franchise_startup_costs(industry_code, year=year)
        return {"industry_code": industry_code, "year": year, "results": results}
    except Exception as e:
        logger.error(f"Franchise startup costs error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="공정위 창업비용 데이터 조회 중 오류가 발생했습니다.",
        )


@router.get("/industry-status/{industry_code}")
async def get_industry_status(
    industry_code: str,
    year: Optional[str] = Query(None, description="조회 연도 (미지정 시 최근 연도)"),
):
    """업종별 가맹사업 개황 (브랜드수, 가맹점수, 평균매출 등)"""
    _validate_industry_code(industry_code)

    from api.services.franchise_data_service import fetch_franchise_industry_status

    try:
        results = await fetch_franchise_industry_status(industry_code, year=year)
        return {"industry_code": industry_code, "year": year, "results": results}
    except Exception as e:
        logger.error(f"Franchise industry status error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="공정위 업종 개황 데이터 조회 중 오류가 발생했습니다.",
        )


@router.get("/raw")
async def get_raw_data(
    year: str = Query("2024", description="조회 연도"),
    endpoint: str = Query(
        "getSclaIndutyFntnOutStats",
        description="API 엔드포인트명",
    ),
):
    """디버그용: 공정위 API 원본 데이터 전체 조회"""
    from api.services.franchise_data_service import fetch_all_raw

    try:
        items = await fetch_all_raw(endpoint=endpoint, year=year)
        return {"endpoint": endpoint, "year": year, "count": len(items), "items": items}
    except Exception as e:
        logger.error(f"Franchise raw data error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="공정위 원본 데이터 조회 중 오류가 발생했습니다.",
        )


@router.get("/health")
async def health():
    """공정위 가맹사업 API 헬스체크"""
    from api.services.franchise_data_service import DATA_GO_KR_API_KEY

    return {
        "status": "ok",
        "service": "franchise_data",
        "api_key_configured": bool(DATA_GO_KR_API_KEY),
    }
