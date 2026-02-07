"""
서울 열린데이터 소득소비 API 서비스

서울시 상권분석서비스 소득소비 데이터를 조회한다.
- OA-21278: VwsmAdstrdIcmpNSaleW (상권별 소득소비)
- OA-22166: VwsmHdongIcmpNSaleW (행정동별 소득소비)

구매력 지표(월평균소득, 외식비지출 등)를 추천·시뮬레이션에 반영하기 위한 서비스.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, TypedDict

import httpx

logger = logging.getLogger(__name__)

SEOUL_API_KEY = os.getenv("SEOUL_API_KEY", "")
BASE_URL = "http://openapi.seoul.go.kr:8088"

# 서비스명
SVC_TRDAR = "VwsmAdstrdIcmpNSaleW"   # 상권별 소득소비
SVC_HDONG = "VwsmHdongIcmpNSaleW"    # 행정동별 소득소비

# ---------------------------------------------------------------------------
# 타입 정의
# ---------------------------------------------------------------------------


class IncomeData(TypedDict, total=False):
    """소득소비 데이터 (상권별 or 행정동별)."""
    code: str                          # 상권코드 또는 행정동코드
    code_name: str                     # 상권명 또는 행정동명
    quarter: str                       # 기준분기 (예: "20243")
    avg_monthly_income: int            # 월평균소득금액
    expenditure_total: int             # 지출총금액
    food_expenditure: int              # 식료품지출총금액
    dining_out_expenditure: int        # 외식비지출총금액
    grocery_expenditure: int           # 식료품_비주류음료지출총금액
    education_expenditure: int         # 교육지출총금액
    entertainment_expenditure: int     # 오락문화지출총금액
    income_level: str                  # 소득수준 (상/중/하)
    dining_out_ratio: float            # 외식비 비율 (소득 대비)
    source: str


class DistrictIncomeInfo(TypedDict, total=False):
    """추천 카드에 붙는 간소화된 소득 정보."""
    avg_monthly_income: int
    dining_out_expenditure: int
    dining_out_ratio: float
    income_level: str
    source: str


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
# 최신 분기 결정
# ---------------------------------------------------------------------------

def _latest_quarter() -> str:
    """현재 시점에서 데이터가 있을 가능성이 높은 최신 분기를 반환."""
    import datetime
    now = datetime.datetime.now()
    year = now.year
    q = (now.month - 1) // 3  # 현재 분기 (0-indexed)
    # 데이터는 보통 1~2분기 후에 반영, 2분기 전을 시도
    if q <= 1:
        return f"{year - 1}{q + 2}"
    return f"{year}{q - 1}"


# ---------------------------------------------------------------------------
# API 호출
# ---------------------------------------------------------------------------

async def _fetch_seoul_api(
    service_name: str,
    start: int,
    end: int,
    quarter: str | None = None,
) -> list[dict[str, Any]]:
    """서울 열린데이터 API 호출."""
    if not SEOUL_API_KEY:
        logger.warning("SEOUL_API_KEY 미설정")
        return []

    if quarter:
        url = f"{BASE_URL}/{SEOUL_API_KEY}/json/{service_name}/{start}/{end}/{quarter}"
    else:
        url = f"{BASE_URL}/{SEOUL_API_KEY}/json/{service_name}/{start}/{end}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            data = resp.json()

        if "RESULT" in data:
            code = data["RESULT"].get("CODE", "")
            if code != "INFO-000":
                logger.warning("Seoul API %s 오류: %s", service_name, data["RESULT"].get("MESSAGE", ""))
                return []

        if service_name in data:
            return data[service_name].get("row", [])

        return []
    except Exception as e:
        logger.warning("Seoul API %s 호출 실패: %s", service_name, e)
        return []


# ---------------------------------------------------------------------------
# 소득수준 판정
# ---------------------------------------------------------------------------

def _income_level(avg_income: int) -> str:
    """월평균소득 기반 소득수준 구분."""
    if avg_income >= 5_000_000:
        return "상"
    elif avg_income >= 3_500_000:
        return "중"
    else:
        return "하"


def _parse_row(row: dict[str, Any], code_field: str, name_field: str) -> IncomeData:
    """API 응답 row → IncomeData 변환."""
    avg_income = int(float(row.get("AVER_MNTHLY_ICMP_AMT", 0) or 0))
    dining_out = int(float(row.get("DINING_OUT_EXPNDTR_TOTAMT", 0) or 0))
    food_exp = int(float(row.get("FD_EXPNDTR_TOTAMT", 0) or 0))
    expenditure_total = int(float(row.get("EXPNDTR_TOTAMT", 0) or 0))
    grocery_exp = int(float(row.get("FD_BVRG_EXPNDTR_TOTAMT", 0) or 0))
    edu_exp = int(float(row.get("EDC_EXPNDTR_TOTAMT", 0) or 0))
    ent_exp = int(float(row.get("CLTUR_EXPNDTR_TOTAMT", 0) or 0))

    dining_ratio = round(dining_out / max(1, avg_income), 4) if avg_income > 0 else 0.0

    return IncomeData(
        code=str(row.get(code_field, "")),
        code_name=str(row.get(name_field, "")),
        quarter=str(row.get("STDR_YYQU_CD", "")),
        avg_monthly_income=avg_income,
        expenditure_total=expenditure_total,
        food_expenditure=food_exp,
        dining_out_expenditure=dining_out,
        grocery_expenditure=grocery_exp,
        education_expenditure=edu_exp,
        entertainment_expenditure=ent_exp,
        income_level=_income_level(avg_income),
        dining_out_ratio=dining_ratio,
        source="서울 열린데이터 상권분석서비스 소득소비",
    )


# ---------------------------------------------------------------------------
# Public API: 상권별 소득소비
# ---------------------------------------------------------------------------

async def fetch_income_by_trdar_cd(
    trdar_cd: str,
    quarter: str | None = None,
) -> IncomeData | None:
    """상권코드로 소득소비 데이터 조회."""
    q = quarter or _latest_quarter()
    cache_key = f"income_trdar:{trdar_cd}:{q}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # 해당 분기 전체 데이터 조회 후 상권코드 필터
    all_data = await _fetch_all_trdar(q)
    if not all_data:
        return None

    for row in all_data:
        if str(row.get("TRDAR_CD", "")) == trdar_cd:
            result = _parse_row(row, "TRDAR_CD", "TRDAR_CD_NM")
            _set_cached(cache_key, result)
            return result

    return None


async def _fetch_all_trdar(quarter: str) -> list[dict[str, Any]]:
    """상권별 소득소비 전체 조회 (캐시)."""
    cache_key = f"income_trdar_all:{quarter}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    all_rows: list[dict[str, Any]] = []
    page_size = 1000
    start = 1

    # 첫 페이지로 total 확인
    rows = await _fetch_seoul_api(SVC_TRDAR, 1, page_size, quarter)
    if not rows:
        # 해당 분기 데이터 없으면 이전 분기 시도
        prev_q = _prev_quarter(quarter)
        rows = await _fetch_seoul_api(SVC_TRDAR, 1, page_size, prev_q)
        if not rows:
            return []
        quarter = prev_q

    all_rows.extend(rows)

    # 추가 페이지 (필요 시)
    if len(rows) == page_size:
        for page_start in range(page_size + 1, 10001, page_size):
            more = await _fetch_seoul_api(SVC_TRDAR, page_start, page_start + page_size - 1, quarter)
            if not more:
                break
            all_rows.extend(more)
            if len(more) < page_size:
                break

    if all_rows:
        _set_cached(cache_key, all_rows)
    return all_rows


# ---------------------------------------------------------------------------
# Public API: 행정동별 소득소비
# ---------------------------------------------------------------------------

async def fetch_income_by_adstrd_cd(
    adstrd_cd: str,
    quarter: str | None = None,
) -> IncomeData | None:
    """행정동코드로 소득소비 데이터 조회."""
    q = quarter or _latest_quarter()
    cache_key = f"income_hdong:{adstrd_cd}:{q}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    all_data = await _fetch_all_hdong(q)
    if not all_data:
        return None

    for row in all_data:
        if str(row.get("ADSTRD_CD", "")) == adstrd_cd:
            result = _parse_row(row, "ADSTRD_CD", "ADSTRD_CD_NM")
            _set_cached(cache_key, result)
            return result

    return None


async def _fetch_all_hdong(quarter: str) -> list[dict[str, Any]]:
    """행정동별 소득소비 전체 조회 (캐시)."""
    cache_key = f"income_hdong_all:{quarter}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    all_rows: list[dict[str, Any]] = []
    page_size = 1000

    rows = await _fetch_seoul_api(SVC_HDONG, 1, page_size, quarter)
    if not rows:
        prev_q = _prev_quarter(quarter)
        rows = await _fetch_seoul_api(SVC_HDONG, 1, page_size, prev_q)
        if not rows:
            return []

    all_rows.extend(rows)

    if len(rows) == page_size:
        for page_start in range(page_size + 1, 10001, page_size):
            more = await _fetch_seoul_api(SVC_HDONG, page_start, page_start + page_size - 1, quarter)
            if not more:
                break
            all_rows.extend(more)
            if len(more) < page_size:
                break

    if all_rows:
        _set_cached(cache_key, all_rows)
    return all_rows


# ---------------------------------------------------------------------------
# Public API: 상권코드로 간소화 소득정보
# ---------------------------------------------------------------------------

async def get_district_income_info(trdar_cd: str) -> DistrictIncomeInfo | None:
    """추천 카드에 표시할 간소화된 소득 정보."""
    data = await fetch_income_by_trdar_cd(trdar_cd)
    if data is None:
        return None

    return DistrictIncomeInfo(
        avg_monthly_income=data.get("avg_monthly_income", 0),
        dining_out_expenditure=data.get("dining_out_expenditure", 0),
        dining_out_ratio=data.get("dining_out_ratio", 0.0),
        income_level=data.get("income_level", "중"),
        source=data.get("source", ""),
    )


# ---------------------------------------------------------------------------
# 헬스 체크
# ---------------------------------------------------------------------------

async def health_check() -> dict[str, Any]:
    """소득소비 API 연결 상태 확인."""
    status: dict[str, Any] = {
        "service": "income_data",
        "api_key_configured": bool(SEOUL_API_KEY),
    }

    if not SEOUL_API_KEY:
        status["status"] = "no_api_key"
        return status

    try:
        rows = await _fetch_seoul_api(SVC_TRDAR, 1, 1, _latest_quarter())
        if rows:
            status["status"] = "ok"
            status["sample_fields"] = list(rows[0].keys()) if rows else []
            status["quarter"] = rows[0].get("STDR_YYQU_CD") if rows else None
        else:
            status["status"] = "no_data"
            status["message"] = "API가 데이터를 반환하지 않습니다 (서버 점검 중일 수 있음)"
    except Exception as e:
        status["status"] = "error"
        status["error"] = str(e)

    return status


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _prev_quarter(q: str) -> str:
    """이전 분기 계산."""
    year = int(q[:4])
    qtr = int(q[4])
    if qtr <= 1:
        return f"{year - 1}4"
    return f"{year}{qtr - 1}"
