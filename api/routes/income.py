"""서울시 소득소비 데이터 API — 상권별/행정동별 구매력 정보"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/income")


@router.get("/district/{district_code}")
async def get_district_income(district_code: str):
    """상권코드 기반 소득소비 정보 조회."""
    from api.services.income_data_service import fetch_income_by_trdar_cd

    try:
        result = await fetch_income_by_trdar_cd(district_code)
        if result is None:
            return {
                "district_code": district_code,
                "available": False,
                "message": "해당 상권의 소득소비 데이터가 없습니다 (API 점검 중일 수 있음).",
            }
        return {"district_code": district_code, "available": True, **result}
    except Exception as e:
        logger.error("Income district error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="소득소비 데이터 조회 중 오류가 발생했습니다.",
        )


@router.get("/dong/{dong_code}")
async def get_dong_income(dong_code: str):
    """행정동코드 기반 소득소비 정보 조회."""
    from api.services.income_data_service import fetch_income_by_adstrd_cd

    try:
        result = await fetch_income_by_adstrd_cd(dong_code)
        if result is None:
            return {
                "dong_code": dong_code,
                "available": False,
                "message": "해당 행정동의 소득소비 데이터가 없습니다.",
            }
        return {"dong_code": dong_code, "available": True, **result}
    except Exception as e:
        logger.error("Income dong error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="소득소비 데이터 조회 중 오류가 발생했습니다.",
        )


@router.get("/health")
async def health():
    """소득소비 API 헬스체크."""
    from api.services.income_data_service import health_check

    try:
        return await health_check()
    except Exception as e:
        logger.error("Income health check error: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}
