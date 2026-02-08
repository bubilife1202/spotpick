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
    """공정위 기준 가맹사업 창업비용 (단위: 천원 → 원으로 변환)

    API 실제 필드:
      avrgFrcsAmt  – 평균 가맹비(교육비 포함)
      avrgFntnAmt  – 평균 가맹금(가입비)
      avrgJngEtcAmt – 평균 기타 가입비
      smtnAmt      – 합계
    """
    year: str
    industry_name: str
    franchise_fee: int          # avrgFntnAmt – 가맹금(가입비)
    education_fee: int          # avrgFrcsAmt – 가맹비(교육비 포함)
    other_fee: int              # avrgJngEtcAmt – 기타 가입비
    total_joining_cost: int     # smtnAmt – 합계
    franchise_count: int        # jnghdqrtrsCnt – 가맹본부 수
    store_count: int            # frcsCnt – 가맹점 수
    raw: dict[str, Any]         # API 원본 데이터


class FranchiseIndustryStatus(TypedDict):
    """공정위 기준 업종 개황

    API 실제 필드 (getIndutySttusOutStats):
      jnghdqrtrsCnt     – 가맹본부 수
      jnghdqrtrsCntRate – 가맹본부 비율(%)
      brandCnt          – 브랜드 수
      brandCntRate      – 브랜드 비율(%)
      frcsCnt           – 가맹점 수
      frcsCntRate       – 가맹점 비율(%)
      droperStorCnt     – 폐점 수
      droperStorCntRate – 폐점 비율(%)
    """
    year: str
    industry_name: str
    hq_count: int               # jnghdqrtrsCnt – 가맹본부 수
    brand_count: int             # brandCnt – 브랜드 수
    store_count: int             # frcsCnt – 가맹점 수
    closed_store_count: int      # droperStorCnt – 폐점 수
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

    # ---------------------------------------------------------------
    # 공정위 가맹사업 API 응답 구조 (2가지 형태 모두 처리)
    #   (A) 플랫 형태 : {"resultCode":"00", "items":[...]}
    #   (B) 중첩 형태 : {"response":{"header":..., "body":{"items":{"item":[...]}}}}
    # ---------------------------------------------------------------
    try:
        # (A) 에러 코드 확인 (플랫 형태)
        result_code = data.get("resultCode") or ""
        if str(result_code) != "00" and str(result_code) != "":
            result_msg = data.get("resultMsg", "UNKNOWN")
            logger.error(
                "공정위 API 오류 응답: resultCode=%s, resultMsg=%s, url=%s",
                result_code, result_msg, url,
            )
            return []

        # (A) 플랫 형태 → items 키가 최상위에 있으면 바로 반환
        if "items" in data and isinstance(data["items"], list):
            return data["items"]

        # (B) 중첩 형태 → response.body.items.item
        body = data.get("response", {}).get("body", {})
        # 중첩 형태의 에러 체크
        header = data.get("response", {}).get("header", {})
        h_code = header.get("resultCode", "")
        if str(h_code) != "00" and str(h_code) != "":
            logger.error(
                "공정위 API 오류 응답: resultCode=%s, resultMsg=%s, url=%s",
                h_code, header.get("resultMsg", ""), url,
            )
            return []

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


def _safe_int(val: Any, unit_cheonwon: bool = True) -> int:
    """값을 int로 변환. unit_cheonwon=True면 천원→원 변환 (API 응답 단위: 천원)"""
    try:
        v = int(float(str(val).replace(",", "")))
        return v * 1_000 if unit_cheonwon else v
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
                other_fee=_safe_int(item.get("avrgJngEtcAmt", 0)),
                total_joining_cost=_safe_int(item.get("smtnAmt", 0)),
                franchise_count=_safe_int(
                    item.get("jnghdqrtrsCnt", 0), unit_cheonwon=False,
                ),
                store_count=_safe_int(
                    item.get("frcsCnt", 0), unit_cheonwon=False,
                ),
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
                hq_count=_safe_int(
                    item.get("jnghdqrtrsCnt", 0), unit_cheonwon=False,
                ),
                brand_count=_safe_int(
                    item.get("brandCnt", 0), unit_cheonwon=False,
                ),
                store_count=_safe_int(
                    item.get("frcsCnt", 0), unit_cheonwon=False,
                ),
                closed_store_count=_safe_int(
                    item.get("droperStorCnt", 0), unit_cheonwon=False,
                ),
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
                "other_fee": c["other_fee"],
                "total_joining_cost": c["total_joining_cost"],
                "franchise_count": c["franchise_count"],
                "store_count": c["store_count"],
            }
            for c in costs
        ]
        # 평균 창업비용(합계) 산출
        valid_totals = [c["total_joining_cost"] for c in costs if c["total_joining_cost"] > 0]
        if valid_totals:
            benchmark["avg_total_startup_cost"] = sum(valid_totals) // len(valid_totals)

    if status:
        benchmark["industry_status"] = [
            {
                "name": s["industry_name"],
                "hq_count": s["hq_count"],
                "brand_count": s["brand_count"],
                "store_count": s["store_count"],
                "closed_store_count": s["closed_store_count"],
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
