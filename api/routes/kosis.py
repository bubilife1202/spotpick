"""KOSIS 외식업체경영실태조사 데이터 API — 업종별 원가구조·수익성 벤치마크"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kosis")

VALID_INDUSTRY_CODES = {
    f"CS10000{i}" for i in range(1, 10)
} | {"CS100010"}


def _validate_industry_code(industry_code: str) -> None:
    if industry_code not in VALID_INDUSTRY_CODES:
        raise HTTPException(
            status_code=400,
            detail=f"유효하지 않은 업종 코드입니다: {industry_code} (CS100001~CS100010)",
        )


@router.get("/cost-structure/{industry_code}")
async def get_cost_structure(industry_code: str):
    """업종별 원가구조 (식재료비·인건비·임차료 비율)"""
    _validate_industry_code(industry_code)

    from api.services.kosis_data_service import get_cost_structure as _get

    try:
        result = await _get(industry_code)
        if result is None:
            return {
                "industry_code": industry_code,
                "available": False,
                "message": "해당 업종의 KOSIS 원가구조 데이터가 없습니다.",
            }
        return {"industry_code": industry_code, "available": True, **result}
    except Exception as e:
        logger.error("KOSIS cost-structure error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="KOSIS 원가구조 데이터 조회 중 오류가 발생했습니다.",
        )


@router.get("/profitability/{industry_code}")
async def get_profitability(industry_code: str):
    """업종별 수익성 분석 (영업이익률, 식재료+인건비 비율 등)"""
    _validate_industry_code(industry_code)

    from api.services.kosis_data_service import get_profitability as _get

    try:
        result = await _get(industry_code)
        if result is None:
            return {
                "industry_code": industry_code,
                "available": False,
                "message": "해당 업종의 KOSIS 수익성 데이터가 없습니다.",
            }
        return {"industry_code": industry_code, "available": True, **result}
    except Exception as e:
        logger.error("KOSIS profitability error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="KOSIS 수익성 데이터 조회 중 오류가 발생했습니다.",
        )


@router.get("/benchmark/{industry_code}")
async def get_benchmark(industry_code: str):
    """업종별 KOSIS 통합 벤치마크 데이터 (원가구조 + 수익성 + 객단가)"""
    _validate_industry_code(industry_code)

    from api.services.kosis_data_service import get_all_benchmarks

    try:
        result = await get_all_benchmarks(industry_code)
        if result is None:
            return {
                "industry_code": industry_code,
                "available": False,
                "message": "해당 업종의 KOSIS 데이터가 없습니다.",
            }
        return {"available": True, **result}
    except Exception as e:
        logger.error("KOSIS benchmark error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="KOSIS 벤치마크 데이터 조회 중 오류가 발생했습니다.",
        )


@router.get("/single-household")
async def get_single_household(region: str = "서울특별시"):
    """지역별 1인가구 비율 (KOSIS 장래가구추계)"""
    from api.services.kosis_data_service import get_single_household_ratio

    try:
        result = await get_single_household_ratio(region)
        if result is None:
            return {
                "region": region,
                "available": False,
                "message": "해당 지역의 1인가구 데이터가 없습니다.",
            }
        return {"region": region, "available": True, **result}
    except Exception as e:
        logger.error("KOSIS single-household error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="KOSIS 1인가구 데이터 조회 중 오류가 발생했습니다.",
        )


@router.get("/rent-trend")
async def get_rent_trend(
    district_code: str | None = None,
    gu_name: str | None = None,
):
    """상가임대료 분기별 트렌드 (commercial_rent.json 기반)."""
    import json
    from pathlib import Path

    rent_file = Path(__file__).parent.parent.parent / "data" / "seoul" / "commercial_rent.json"
    if not rent_file.exists():
        return {"available": False, "message": "임대료 데이터가 없습니다."}

    try:
        with open(rent_file, encoding="utf-8") as f:
            raw = json.load(f)

        tables = raw.get("tables", {})
        small_rent = tables.get("small_store_rent", {})
        rows = small_rent.get("row", [])

        if not rows:
            return {"available": False, "message": "임대료 행 데이터가 없습니다."}

        # Filter by region if specified
        target_name = gu_name or ""
        filtered: list[dict] = []
        seoul_rows: list[dict] = []

        for r in rows:
            region = r.get("C1_NM", "")
            if region == "서울":
                seoul_rows.append(r)
            if target_name and target_name in region:
                filtered.append(r)

        # Use filtered if available, else seoul-level data
        data_rows = filtered if filtered else seoul_rows

        quarterly_rent: list[dict] = []
        for r in data_rows:
            period = r.get("PRD_DE", "")
            rent_val = float(r.get("DT", 0) or 0)
            quarterly_rent.append({
                "period": period,
                "rent_per_sqm": round(rent_val, 2),
                "region": r.get("C1_NM", ""),
            })

        # Sort by period
        quarterly_rent.sort(key=lambda x: x["period"])

        # Calculate YoY change
        yoy_change = 0.0
        if len(quarterly_rent) >= 5:
            current = quarterly_rent[-1]["rent_per_sqm"]
            year_ago = quarterly_rent[-5]["rent_per_sqm"]
            if year_ago > 0:
                yoy_change = round((current - year_ago) / year_ago * 100, 1)

        # Seoul average percentile
        seoul_avg = 0.0
        if seoul_rows:
            seoul_avg = sum(float(r.get("DT", 0) or 0) for r in seoul_rows) / len(seoul_rows)

        current_rent = quarterly_rent[-1]["rent_per_sqm"] if quarterly_rent else 0
        percentile = round(current_rent / max(1, seoul_avg) * 100, 1) if seoul_avg > 0 else 50

        return {
            "available": True,
            "district_code": district_code,
            "gu_name": gu_name or "서울",
            "quarterly_rent": quarterly_rent[-12:],  # Last 3 years (12 quarters)
            "yoy_change": yoy_change,
            "seoul_avg_percentile": percentile,
            "current_rent_per_sqm": current_rent,
        }

    except Exception as e:
        logger.error("Rent trend error: %s", e, exc_info=True)
        return {"available": False, "message": "임대료 트렌드 조회 중 오류가 발생했습니다."}


@router.get("/health")
async def health():
    """KOSIS API 헬스체크"""
    from api.services.kosis_data_service import health_check

    try:
        return await health_check()
    except Exception as e:
        logger.error("KOSIS health check error: %s", e, exc_info=True)
        return {"status": "error", "error": str(e)}
