"""
공정거래위원회 가맹사업 데이터 서비스

data.go.kr API를 통해 업종별 실제 가맹사업 창업비용·업종개황 데이터를 조회한다.
시뮬레이션 서비스의 하드코딩 추정치를 대체하기 위한 참조 데이터.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional, TypedDict

import httpx  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY", "")

# ---------------------------------------------------------------------------
# 엔드포인트
# ---------------------------------------------------------------------------

BASE_URL_COST = (
    "https://apis.data.go.kr/1130000/FftcSclasIndutyFntnStatsService"
)
BASE_URL_STATUS = (
    "https://apis.data.go.kr/1130000/FftcIndutyStusStatsService"
)

# ---------------------------------------------------------------------------
# 우리 업종코드 → 공정위 업종 소분류 키워드 매핑
# ---------------------------------------------------------------------------

INDUSTRY_KEYWORD_MAP: dict[str, list[str]] = {
    "CS100001": ["한식"],
    "CS100002": ["중식"],
    "CS100003": ["일식"],
    "CS100004": ["서양식", "양식"],
    "CS100005": ["제과제빵", "베이커리"],
    "CS100006": ["패스트푸드", "피자", "햄버거"],
    "CS100007": ["치킨"],
    "CS100008": ["분식"],
    "CS100009": ["주점", "호프"],
    "CS100010": ["커피", "음료"],
}

# ---------------------------------------------------------------------------
# 타입 정의
# ---------------------------------------------------------------------------


class FranchiseStartupCost(TypedDict):
    """공정위 기준 가맹사업 창업비용 (단위: 만원 → 원으로 변환)"""
    year: str
    industry_name: str
    franchise_fee: int          # 가맹비
    education_fee: int          # 교육비
    deposit: int                # 보증금
    other_fee: int              # 기타 가입비
    total_joining_cost: int     # 가입비 합계
    interior_cost: int          # 인테리어 비용 (있을 경우)
    total_startup_cost: int     # 총 창업비용 (있을 경우)
    raw: dict[str, Any]         # API 원본 데이터


class FranchiseIndustryStatus(TypedDict):
    """공정위 기준 업종 개황"""
    year: str
    industry_name: str
    brand_count: int            # 가맹본부 수
    store_count: int            # 가맹점 수
    avg_sales: int              # 평균 매출액 (있을 경우)
    raw: dict[str, Any]


# ---------------------------------------------------------------------------
# 캐시 (TTL 24시간)
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 86400  # 24h


def _get_cached(key: str) -> Any | None:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
        del _cache[key]
    return None


def _set_cached(key: str, val: Any) -> None:
    _cache[key] = (time.time(), val)


# ---------------------------------------------------------------------------
# 내부 API 호출
# ---------------------------------------------------------------------------

async def _call_api(
    base_url: str,
    endpoint: str,
    params: dict[str, str],
) -> list[dict[str, Any]]:
    """data.go.kr API 호출 → items 배열 반환"""
    if not DATA_GO_KR_API_KEY:
        logger.warning("DATA_GO_KR_API_KEY 미설정")
        return []

    url = f"{base_url}/{endpoint}"
    params = {
        "serviceKey": DATA_GO_KR_API_KEY,
        "resultType": "json",
        **params,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("공정위 API HTTP 오류: %s %s", e.response.status_code, url)
        return []
    except Exception as e:
        logger.error("공정위 API 호출 실패: %s", e)
        return []

    # data.go.kr 응답 구조: response.body.items or items.item
    try:
        body = data.get("response", data).get("body", data)
        items = body.get("items", [])
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        return items if isinstance(items, list) else []
    except Exception:
        logger.error("공정위 API 응답 파싱 실패: %s", str(data)[:300])
        return []


# ---------------------------------------------------------------------------
# 업종 매칭 유틸
# ---------------------------------------------------------------------------

def _match_industry(
    items: list[dict[str, Any]],
    keywords: list[str],
) -> list[dict[str, Any]]:
    """indutyMlsfcNm(소분류명) 또는 indutyLclasNm(중분류명)에 키워드가 포함된 항목 필터"""
    matched = []
    for item in items:
        names = [
            str(item.get("indutyMlsfcNm", "")),
            str(item.get("indutyLclasNm", "")),
            str(item.get("indutyNm", "")),
        ]
        for kw in keywords:
            if any(kw in n for n in names):
                matched.append(item)
                break
    return matched


def _safe_int(val: Any, unit_manwon: bool = True) -> int:
    """값을 int로 변환. unit_manwon=True면 만원→원 변환"""
    try:
        v = int(float(str(val).replace(",", "")))
        return v * 10_000 if unit_manwon else v
    except (ValueError, TypeError):
        return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def fetch_franchise_startup_costs(
    industry_code: str,
    year: str | None = None,
) -> list[FranchiseStartupCost]:
    """
    업종별 가맹사업 창업비용 조회.
    year 미지정 시 최근 연도 데이터를 가져온다.
    """
    cache_key = f"startup_cost:{industry_code}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    keywords = INDUSTRY_KEYWORD_MAP.get(industry_code)
    if not keywords:
        return []

    # 최근 3년 중 데이터 있는 연도 탐색
    years = [year] if year else ["2024", "2023", "2022"]
    all_results: list[FranchiseStartupCost] = []

    for yr in years:
        items = await _call_api(
            BASE_URL_COST,
            "getSclaIndutyFntnOutStats",
            {"pageNo": "1", "numOfRows": "200", "yr": yr},
        )
        if not items:
            continue

        matched = _match_industry(items, keywords)
        for item in matched:
            result = FranchiseStartupCost(
                year=yr,
                industry_name=item.get("indutyMlsfcNm", ""),
                franchise_fee=_safe_int(item.get("avrgFntnAmt", 0)),
                education_fee=_safe_int(item.get("avrgFrcsAmt", 0)),
                deposit=_safe_int(item.get("avrgBznsmrtAmt", 0)),
                other_fee=_safe_int(item.get("avrgJngEtcAmt", 0)),
                total_joining_cost=_safe_int(item.get("smtnAmt", 0)),
                interior_cost=_safe_int(item.get("avrgIntrrAmt", 0)),
                total_startup_cost=_safe_int(item.get("smtnFntnAmt", 0)),
                raw=item,
            )
            all_results.append(result)

        if all_results:
            break  # 최근 연도 데이터 있으면 중단

    _set_cached(cache_key, all_results)
    return all_results


async def fetch_franchise_industry_status(
    industry_code: str,
    year: str | None = None,
) -> list[FranchiseIndustryStatus]:
    """업종별 가맹사업 개황 조회"""
    cache_key = f"industry_status:{industry_code}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    keywords = INDUSTRY_KEYWORD_MAP.get(industry_code)
    if not keywords:
        return []

    years = [year] if year else ["2024", "2023", "2022"]
    all_results: list[FranchiseIndustryStatus] = []

    for yr in years:
        items = await _call_api(
            BASE_URL_STATUS,
            "getIndutySttusOutStats",
            {"pageNo": "1", "numOfRows": "200", "yr": yr},
        )
        if not items:
            continue

        matched = _match_industry(items, keywords)
        for item in matched:
            result = FranchiseIndustryStatus(
                year=yr,
                industry_name=item.get("indutyMlsfcNm", item.get("indutyNm", "")),
                brand_count=_safe_int(item.get("frchsHdofcCnt", 0), unit_manwon=False),
                store_count=_safe_int(item.get("frchsStorCnt", 0), unit_manwon=False),
                avg_sales=_safe_int(item.get("avrgSlsAmt", 0)),
                raw=item,
            )
            all_results.append(result)

        if all_results:
            break

    _set_cached(cache_key, all_results)
    return all_results


async def get_franchise_benchmark(
    industry_code: str,
) -> dict[str, Any]:
    """
    시뮬레이션에서 사용할 벤치마크 데이터 통합 조회.
    하드코딩 추정치 대체용.
    """
    costs = await fetch_franchise_startup_costs(industry_code)
    status = await fetch_franchise_industry_status(industry_code)

    benchmark: dict[str, Any] = {
        "source": "공정거래위원회 가맹사업 정보공개서",
        "available": bool(costs or status),
        "startup_costs": [],
        "industry_status": [],
    }

    if costs:
        # 가장 최근 연도 + 합산 평균
        latest = costs[0]
        benchmark["year"] = latest["year"]
        benchmark["startup_costs"] = [
            {
                "name": c["industry_name"],
                "franchise_fee": c["franchise_fee"],
                "education_fee": c["education_fee"],
                "deposit": c["deposit"],
                "other_fee": c["other_fee"],
                "total_joining_cost": c["total_joining_cost"],
                "interior_cost": c["interior_cost"],
                "total_startup_cost": c["total_startup_cost"],
            }
            for c in costs
        ]
        # 평균 창업비용 산출
        valid_totals = [c["total_startup_cost"] for c in costs if c["total_startup_cost"] > 0]
        if valid_totals:
            benchmark["avg_total_startup_cost"] = sum(valid_totals) // len(valid_totals)
        valid_interior = [c["interior_cost"] for c in costs if c["interior_cost"] > 0]
        if valid_interior:
            benchmark["avg_interior_cost"] = sum(valid_interior) // len(valid_interior)

    if status:
        benchmark["industry_status"] = [
            {
                "name": s["industry_name"],
                "brand_count": s["brand_count"],
                "store_count": s["store_count"],
                "avg_sales": s["avg_sales"],
            }
            for s in status
        ]

    return benchmark


# ---------------------------------------------------------------------------
# 전체 업종 원본 데이터 조회 (디버그/탐색용)
# ---------------------------------------------------------------------------

async def fetch_all_raw(
    endpoint: str = "getSclaIndutyFntnOutStats",
    year: str = "2024",
) -> list[dict[str, Any]]:
    """지정 연도의 전체 원본 데이터 조회 (디버그용)"""
    return await _call_api(
        BASE_URL_COST,
        endpoint,
        {"pageNo": "1", "numOfRows": "500", "yr": year},
    )
