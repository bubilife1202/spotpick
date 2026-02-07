"""
KREI 외식업체경영실태조사 2023 원시자료 기반 데이터 서비스

전처리된 JSON(data/krei/krei_2023_processed.json)을 로드하여
시뮬레이션의 하드코딩 값을 실데이터로 대체한다.

KOSIS API 대비 장점:
- 원시자료 3,077건 직접 집계 → 업종·상권유형·지역 교차 분석 가능
- API 호출 없이 로컬 JSON 기반 → 안정적·빠름
- 한식 세분류(한식일반/면요리/육류/해산물) 지원
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 타입 정의
# ---------------------------------------------------------------------------


class CostRatios(TypedDict, total=False):
    food_pct: float       # 식재료비 비율 (%)
    labor_pct: float      # 인건비 비율 (%)
    rent_pct: float       # 임차료 비율 (%)
    profit_pct: float     # 영업이익률 (%)
    n: int                # 표본 수
    source: str


class RentBenchmark(TypedDict, total=False):
    monthly_rent_median: float  # 중앙값 (만원)
    monthly_rent_p25: float     # 25% (만원)
    monthly_rent_p75: float     # 75% (만원)
    deposit_median: float       # 보증금 중앙값 (만원)
    n: int
    source: str


class StartupInvestment(TypedDict, total=False):
    total: float       # 총투자 가중평균 (만원)
    interior: float    # 인테리어 가중평균 (만원)
    kitchen: float     # 주방기기 가중평균 (만원)
    n: int
    source: str


class AvgTicketResult(TypedDict, total=False):
    avg_ticket: float   # 객단가 가중평균 (원)
    n: int
    source: str


# ---------------------------------------------------------------------------
# 캐시 (24시간 TTL)
# ---------------------------------------------------------------------------

_data_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 86400  # 24h


def _get_data() -> dict[str, Any] | None:
    """전처리된 KREI JSON 로드 (캐시)."""
    cache_key = "krei_processed"
    if cache_key in _data_cache:
        ts, val = _data_cache[cache_key]
        if time.time() - ts < _CACHE_TTL:
            return val
        del _data_cache[cache_key]

    json_path = Path(__file__).parent.parent.parent / "data" / "krei" / "krei_2023_processed.json"
    if not json_path.exists():
        logger.warning("KREI 데이터 파일 없음: %s", json_path)
        return None

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
        _data_cache[cache_key] = (time.time(), data)
        logger.info("KREI 데이터 로드: %d건", data.get("total_records", 0))
        return data
    except Exception as e:
        logger.warning("KREI 데이터 로드 실패: %s", e)
        return None


def _get_industry_data(
    industry_code: str,
    sub_category: str | None = None,
    seoul_only: bool = True,
    district_type: str | None = None,
) -> dict[str, Any] | None:
    """
    업종별 집계 데이터를 조회한다.

    우선순위: 서울 상권유형별 → 서울 전체 → 전국 상권유형별 → 전국 전체
    """
    data = _get_data()
    if data is None:
        return None

    ind = data.get("industries", {}).get(industry_code)
    if ind is None:
        return None

    # 한식 세분류
    base = ind
    if sub_category and industry_code == "CS100001":
        sub_data = ind.get("sub_categories", {}).get(sub_category)
        if sub_data:
            base = sub_data

    # 상권유형 × 지역 교차
    if district_type:
        dt_data = base.get("by_district_type", {}).get(district_type)
        if dt_data:
            if seoul_only and dt_data.get("seoul"):
                return dt_data["seoul"]
            return dt_data.get("total")

    # 지역별
    if seoul_only and base.get("seoul"):
        return base["seoul"]

    return base.get("total")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_cost_ratios(
    industry_code: str,
    sub_category: str | None = None,
    seoul_only: bool = True,
) -> CostRatios | None:
    """
    업종별 원가율 (식재료비, 인건비, 임차료, 영업이익률).

    Returns:
        CostRatios with pct values (e.g., food_pct=35.5 means 35.5%)
        or None if data not available.
    """
    agg = _get_industry_data(industry_code, sub_category, seoul_only)
    if agg is None or agg.get("n", 0) < 5:
        # 서울 데이터 부족 시 전국으로 폴백
        if seoul_only:
            agg = _get_industry_data(industry_code, sub_category, seoul_only=False)
        if agg is None or agg.get("n", 0) < 5:
            return None

    result = CostRatios(
        n=agg["n"],
        source=f"KREI 외식업체경영실태조사 2023 (n={agg['n']})",
    )
    if "food_pct" in agg:
        result["food_pct"] = agg["food_pct"]
    if "labor_pct" in agg:
        result["labor_pct"] = agg["labor_pct"]
    if "rent_pct" in agg:
        result["rent_pct"] = agg["rent_pct"]
    if "profit_pct" in agg:
        result["profit_pct"] = agg["profit_pct"]

    return result


def get_rent_benchmark(
    industry_code: str,
    district_type: str | None = None,
    seoul_only: bool = True,
) -> RentBenchmark | None:
    """
    업종별 · 상권유형별 임대료 분위수 (만원).

    Returns:
        RentBenchmark or None if n < 10.
    """
    agg = _get_industry_data(industry_code, district_type=district_type, seoul_only=seoul_only)
    if agg is None:
        if seoul_only:
            agg = _get_industry_data(industry_code, district_type=district_type, seoul_only=False)
        if agg is None:
            return None

    rent_n = agg.get("monthly_rent_n", 0)
    if rent_n < 10:
        # 상권유형 제거하고 재시도
        if district_type:
            return get_rent_benchmark(industry_code, district_type=None, seoul_only=seoul_only)
        return None

    result = RentBenchmark(
        n=rent_n,
        source=f"KREI 외식업체경영실태조사 2023 (n={rent_n})",
    )
    if "monthly_rent_median" in agg:
        result["monthly_rent_median"] = agg["monthly_rent_median"]
    if "monthly_rent_p25" in agg:
        result["monthly_rent_p25"] = agg["monthly_rent_p25"]
    if "monthly_rent_p75" in agg:
        result["monthly_rent_p75"] = agg["monthly_rent_p75"]
    if "deposit_median" in agg:
        result["deposit_median"] = agg["deposit_median"]

    return result


def get_startup_investment(
    industry_code: str,
    seoul_only: bool = True,
) -> StartupInvestment | None:
    """
    업종별 초기 투자비 가중평균 (만원).

    Returns:
        StartupInvestment or None if data not available.
    """
    agg = _get_industry_data(industry_code, seoul_only=seoul_only)
    if agg is None or agg.get("invest_n", 0) < 5:
        if seoul_only:
            agg = _get_industry_data(industry_code, seoul_only=False)
        if agg is None or agg.get("invest_n", 0) < 5:
            return None

    result = StartupInvestment(
        n=agg.get("invest_n", 0),
        source=f"KREI 외식업체경영실태조사 2023 (n={agg.get('invest_n', 0)})",
    )
    if "invest_total" in agg:
        result["total"] = agg["invest_total"]
    if "interior" in agg:
        result["interior"] = agg["interior"]
    if "kitchen" in agg:
        result["kitchen"] = agg["kitchen"]

    return result


def get_avg_ticket(
    industry_code: str,
    sub_category: str | None = None,
) -> AvgTicketResult | None:
    """
    업종별 평균 객단가 (원).

    Returns:
        AvgTicketResult or None.
    """
    # 객단가는 전국 데이터 사용 (표본 확보)
    agg = _get_industry_data(industry_code, sub_category, seoul_only=False)
    if agg is None or agg.get("ticket_n", 0) < 5:
        return None

    if "avg_ticket" not in agg:
        return None

    return AvgTicketResult(
        avg_ticket=agg["avg_ticket"],
        n=agg.get("ticket_n", 0),
        source=f"KREI 외식업체경영실태조사 2023 (n={agg.get('ticket_n', 0)})",
    )


def get_avg_area(industry_code: str, seoul_only: bool = True) -> float | None:
    """업종별 평균 영업면적(평)."""
    agg = _get_industry_data(industry_code, seoul_only=seoul_only)
    if agg is None:
        if seoul_only:
            agg = _get_industry_data(industry_code, seoul_only=False)
    if agg and "avg_area_pyeong" in agg:
        return agg["avg_area_pyeong"]
    return None
