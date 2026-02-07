"""
KOSIS (국가통계포털) 외식업체경영실태조사 데이터 서비스

통계청 KOSIS Open API (PublicDataReader)를 통해 업종별 원가구조·수익성·객단가를 조회한다.
시뮬레이션의 하드코딩 원가율을 실제 정부 조사 데이터로 대체하기 위한 서비스.

사용 통계표 (orgId=114, 외식업체경영실태조사):
- DT_114054_029: 수익성·생산성 분석
- DT_114054_028: 사업실적 (매출액/식재료비/인건비/임차료)
- DT_114054_031: 식재료비 사용
- DT_114054_022: 객단가
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

KOSIS_API_KEY = os.getenv("KOSIS_API_KEY", "")

# ---------------------------------------------------------------------------
# 우리 업종코드 → KOSIS 업종명 매핑
# ---------------------------------------------------------------------------

INDUSTRY_NAME_MAP: dict[str, str] = {
    "CS100001": "한식",
    "CS100002": "중식",
    "CS100003": "일식",
    "CS100004": "서양식",
    "CS100005": "제과점",
    "CS100006": "피자·햄버거·샌드위치 및 유사 음식점업",
    "CS100007": "치킨전문점",
    "CS100008": "김밥 및 기타 간이 음식점업",
    "CS100009": "주점업",
    "CS100010": "비알코올 음료점업",
}

# KOSIS 분류값명에서 부분 매칭용 키워드 (업종명이 정확히 일치하지 않을 때)
INDUSTRY_KEYWORDS: dict[str, list[str]] = {
    "CS100001": ["한식"],
    "CS100002": ["중식"],
    "CS100003": ["일식"],
    "CS100004": ["서양식", "양식"],
    "CS100005": ["제과점", "제과"],
    "CS100006": ["피자", "햄버거", "샌드위치"],
    "CS100007": ["치킨"],
    "CS100008": ["김밥", "간이"],
    "CS100009": ["주점"],
    "CS100010": ["비알코올", "음료점"],
}

# DT_114054_028 (사업실적)은 대분류만 있음 → 세부 업종의 부모 카테고리 매핑
# 한식/중식/일식/서양식 → 일반음식점업, 제과점/피자/치킨/김밥 → 기타 음식점업
COST_STRUCTURE_PARENT: dict[str, list[str]] = {
    "CS100001": ["일반음식점"],
    "CS100002": ["일반음식점"],
    "CS100003": ["일반음식점"],
    "CS100004": ["일반음식점"],
    "CS100005": ["기타 음식점"],
    "CS100006": ["기타 음식점"],
    "CS100007": ["기타 음식점"],
    "CS100008": ["기타 음식점"],
    "CS100009": ["주점"],
    "CS100010": ["비알코올", "음료점"],
}

# ---------------------------------------------------------------------------
# 타입 정의
# ---------------------------------------------------------------------------


class CostStructure(TypedDict, total=False):
    food_cost_ratio: float       # 식재료비 비율
    labor_cost_ratio: float      # 인건비 비율
    rent_ratio: float            # 임차료 비율
    profit_margin: float         # 영업이익률
    source: str
    year: str


class Profitability(TypedDict, total=False):
    profit_margin: float         # 영업이익률
    food_labor_ratio: float      # 식재료+인건비 비율
    sales_per_employee: int      # 종사자당 매출액 (만원)
    sales_per_seat: int          # 좌석당 매출액 (만원)
    source: str
    year: str


class AvgTicket(TypedDict, total=False):
    avg_ticket: int              # 평균 객단가 (원)
    lunch_ticket: int            # 점심 객단가
    dinner_ticket: int           # 저녁 객단가
    source: str
    year: str


class KosisBenchmark(TypedDict, total=False):
    industry_code: str
    industry_name: str
    cost_structure: CostStructure | None
    profitability: Profitability | None
    avg_ticket: AvgTicket | None
    source: str
    year: str


# ---------------------------------------------------------------------------
# 캐시 (TTL 24시간) — franchise_data_service.py 와 동일 패턴
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
# KOSIS API 호출 (PublicDataReader 사용)
# ---------------------------------------------------------------------------

def _get_kosis_client():
    """Kosis 클라이언트를 생성. 임포트 에러 시 None 반환."""
    if not KOSIS_API_KEY:
        logger.warning("KOSIS_API_KEY 미설정")
        return None
    try:
        from PublicDataReader import Kosis  # type: ignore[import-not-found]
        return Kosis(KOSIS_API_KEY)
    except ImportError:
        logger.warning("PublicDataReader 패키지 미설치")
        return None
    except Exception as e:
        logger.warning("Kosis 클라이언트 생성 실패: %s", e)
        return None


# 2개 분류 레벨이 있는 테이블 (objL2 필요)
_TWO_LEVEL_TABLES = {"DT_114054_028", "DT_114054_022", "DT_114054_031"}


def _fetch_table(tbl_id: str, year: str = "2023") -> Any:
    """
    KOSIS 통계표 조회 → pandas DataFrame 반환.
    실패 시 None.

    일부 테이블은 분류 레벨이 1개(objL1만), 일부는 2개(objL1+objL2).
    잘못된 파라미터 전달 시 KOSIS API가 에러를 반환하므로 구분 처리.
    """
    cache_key = f"kosis_raw:{tbl_id}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    client = _get_kosis_client()
    if client is None:
        return None

    try:
        params: dict[str, str] = {
            "service_name": "통계자료",
            "orgId": "114",
            "tblId": tbl_id,
            "objL1": "ALL",
            "itmId": "ALL",
            "prdSe": "Y",
            "startPrdDe": year,
            "endPrdDe": year,
        }
        if tbl_id in _TWO_LEVEL_TABLES:
            params["objL2"] = "ALL"

        df = client.get_data(**params)
        if df is not None and len(df) > 0:
            _set_cached(cache_key, df)
            return df
        logger.info("KOSIS %s (%s): 데이터 없음", tbl_id, year)
        return None
    except Exception as e:
        logger.warning("KOSIS %s 조회 실패: %s", tbl_id, e)
        return None


def _match_industry_rows(df: Any, industry_code: str) -> Any:
    """
    DataFrame에서 업종명이 매칭되는 행을 필터링.
    분류값명1 또는 분류값명2 컬럼에서 키워드 검색.
    """
    import pandas as pd  # type: ignore[import-not-found]

    target_name = INDUSTRY_NAME_MAP.get(industry_code, "")
    keywords = INDUSTRY_KEYWORDS.get(industry_code, [target_name] if target_name else [])

    if df is None or len(df) == 0:
        return pd.DataFrame()

    # KOSIS 컬럼명 후보
    name_cols = [c for c in df.columns if "분류값명" in c or "classNm" in c.lower()]

    mask = pd.Series([False] * len(df), index=df.index)
    for col in name_cols:
        for kw in keywords:
            mask = mask | df[col].astype(str).str.contains(kw, na=False)

    return df[mask]


def _safe_float(val: Any) -> float | None:
    """값을 float로 안전 변환"""
    try:
        v = str(val).replace(",", "").replace(" ", "").strip()
        if v in ("", "-", "x", "X", "…"):
            return None
        return float(v)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Public API: 원가구조
# ---------------------------------------------------------------------------

async def get_cost_structure(
    industry_code: str,
    year: str = "2023",
) -> CostStructure | None:
    """
    DT_114054_028 (사업실적)에서 식재료비·인건비·임차료 비율 추출.

    테이블 구조:
    - 분류값명1: 비용항목 (매출액, 식재료비, 고용인 인건비, 임차료, 영업이익 등)
    - 분류값명2: 업종 (일반음식점업, 비알코올 음료점업, 주점업 등)
    - 항목명: "금액" 또는 "비율"
    - 수치값: 값
    """
    cache_key = f"kosis_cost:{industry_code}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    df = _fetch_table("DT_114054_028", year)
    if df is None:
        return None

    try:
        # 업종 매칭 (분류값명2에서)
        matched = _match_industry_rows(df, industry_code)
        if matched.empty:
            # DT_114054_028은 대분류만 있으므로 부모 카테고리로 재시도
            parent_kw = COST_STRUCTURE_PARENT.get(industry_code)
            if parent_kw:
                import pandas as pd  # type: ignore[import-not-found]
                name_cols = [c for c in df.columns if "분류값명" in c]
                mask = pd.Series([False] * len(df), index=df.index)
                for col in name_cols:
                    for kw in parent_kw:
                        mask = mask | df[col].astype(str).str.contains(kw, na=False)
                matched = df[mask]

            if matched.empty:
                logger.info("KOSIS DT_114054_028: %s 매칭 데이터 없음", industry_code)
                return None

        # 비율 행만 필터 (항목명 == "비율")
        ratio_rows = matched[matched["항목명"].astype(str).str.contains("비율")]
        if ratio_rows.empty:
            logger.info("KOSIS DT_114054_028: 비율 데이터 없음")
            return None

        result = CostStructure(
            source=f"KOSIS 외식업체경영실태조사 {year}",
            year=year,
        )

        for _, row in ratio_rows.iterrows():
            cost_item = str(row.get("분류값명1", ""))
            val = _safe_float(row.get("수치값"))
            if val is None:
                continue

            # 수치값은 이미 % 단위 (예: 32.4 → 0.324)
            ratio = val / 100.0

            if "식재료" in cost_item:
                result["food_cost_ratio"] = round(ratio, 4)
            elif "고용인" in cost_item and "인건비" in cost_item:
                result["labor_cost_ratio"] = round(ratio, 4)
            elif "임차료" in cost_item:
                result["rent_ratio"] = round(ratio, 4)
            elif "영업이익" in cost_item:
                result["profit_margin"] = round(ratio, 4)

        if result.get("food_cost_ratio") or result.get("labor_cost_ratio"):
            _set_cached(cache_key, result)
            return result

        return None

    except Exception as e:
        logger.warning("KOSIS 원가구조 파싱 실패: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public API: 수익성
# ---------------------------------------------------------------------------

async def get_profitability(
    industry_code: str,
    year: str = "2023",
) -> Profitability | None:
    """
    DT_114054_029 (수익성·생산성 분석)에서 영업이익률, 식재료+인건비 비율 등 추출.

    테이블 구조:
    - 분류값명1: 업종명 (한식, 비알코올 음료점업 등)
    - 항목명: 지표명 (매출액 대비 영업이익률, 매출 대비 식재료 및 인건비 비율, 종사원 당 매출액 등)
    - 수치값: 값
    """
    cache_key = f"kosis_profit:{industry_code}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    df = _fetch_table("DT_114054_029", year)
    if df is None:
        return None

    try:
        matched = _match_industry_rows(df, industry_code)
        if matched.empty:
            logger.info("KOSIS DT_114054_029: %s 매칭 데이터 없음", industry_code)
            return None

        result = Profitability(
            source=f"KOSIS 외식업체경영실태조사 {year}",
            year=year,
        )

        for _, row in matched.iterrows():
            item_name = str(row.get("항목명", ""))
            val = _safe_float(row.get("수치값"))
            if val is None:
                continue

            if "영업이익률" in item_name:
                # 값은 % 단위 (예: 14.8 → 0.148)
                result["profit_margin"] = round(val / 100.0, 4)
            elif "식재료" in item_name and "인건비" in item_name:
                result["food_labor_ratio"] = round(val / 100.0, 4)
            elif "종사원" in item_name and "매출" in item_name:
                # 만원 단위
                result["sales_per_employee"] = int(val)
            elif "좌석" in item_name and "매출" in item_name:
                result["sales_per_seat"] = int(val)

        if result.get("profit_margin") is not None:
            _set_cached(cache_key, result)
            return result

        return None

    except Exception as e:
        logger.warning("KOSIS 수익성 파싱 실패: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public API: 객단가
# ---------------------------------------------------------------------------

async def get_avg_ticket(
    industry_code: str,
    year: str = "2023",
) -> AvgTicket | None:
    """
    DT_114054_022 (객단가)에서 업종별 평균 객단가 추출.

    테이블 구조:
    - 분류값명1: 업종명 (한식, 비알코올 음료점업 등)
    - 분류값명2: 객단가 범위 ("5천원 미만", "평균" 등)
    - 항목명: "객단가"
    - 수치값: 값 (평균 행은 원 단위, 범위 행은 % 비율)
    """
    cache_key = f"kosis_ticket:{industry_code}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    df = _fetch_table("DT_114054_022", year)
    if df is None:
        return None

    try:
        matched = _match_industry_rows(df, industry_code)
        if matched.empty:
            logger.info("KOSIS DT_114054_022: %s 매칭 데이터 없음", industry_code)
            return None

        result = AvgTicket(
            source=f"KOSIS 외식업체경영실태조사 {year}",
            year=year,
        )

        for _, row in matched.iterrows():
            range_name = str(row.get("분류값명2", ""))
            val = _safe_float(row.get("수치값"))
            if val is None:
                continue

            # "평균" 행이 실제 객단가 (원 단위, 예: 5821.4 = 5,821원)
            if "평균" in range_name:
                result["avg_ticket"] = int(round(val))

        if result.get("avg_ticket"):
            _set_cached(cache_key, result)
            return result

        return None

    except Exception as e:
        logger.warning("KOSIS 객단가 파싱 실패: %s", e)
        return None


# ---------------------------------------------------------------------------
# Public API: 통합 벤치마크
# ---------------------------------------------------------------------------

async def get_all_benchmarks(
    industry_code: str,
    year: str = "2023",
) -> KosisBenchmark | None:
    """
    원가구조 + 수익성 + 객단가 통합 조회.
    시뮬레이션에서 사용할 전체 벤치마크 데이터.
    """
    cache_key = f"kosis_all:{industry_code}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    cost = await get_cost_structure(industry_code, year)
    profit = await get_profitability(industry_code, year)
    ticket = await get_avg_ticket(industry_code, year)

    if cost is None and profit is None and ticket is None:
        # 최근 연도 데이터 없으면 1년 전으로 재시도
        prev_year = str(int(year) - 1)
        cost = await get_cost_structure(industry_code, prev_year)
        profit = await get_profitability(industry_code, prev_year)
        ticket = await get_avg_ticket(industry_code, prev_year)
        if cost is None and profit is None and ticket is None:
            return None
        year = prev_year

    result = KosisBenchmark(
        industry_code=industry_code,
        industry_name=INDUSTRY_NAME_MAP.get(industry_code, ""),
        cost_structure=cost,
        profitability=profit,
        avg_ticket=ticket,
        source=f"KOSIS 외식업체경영실태조사 {year}",
        year=year,
    )

    _set_cached(cache_key, result)
    return result


# ---------------------------------------------------------------------------
# 헬스 체크
# ---------------------------------------------------------------------------

async def health_check() -> dict[str, Any]:
    """KOSIS API 연결 상태 확인"""
    status: dict[str, Any] = {
        "service": "kosis_data",
        "api_key_configured": bool(KOSIS_API_KEY),
    }

    if not KOSIS_API_KEY:
        status["status"] = "no_api_key"
        return status

    try:
        client = _get_kosis_client()
        if client is None:
            status["status"] = "client_error"
            return status

        # 가벼운 테스트 쿼리 (1행만)
        df = client.get_data(
            service_name="통계자료",
            orgId="114",
            tblId="DT_114054_029",
            objL1="ALL",
            itmId="ALL",
            prdSe="Y",
            startPrdDe="2023",
            endPrdDe="2023",
        )
        if df is not None and len(df) > 0:
            status["status"] = "ok"
            status["sample_rows"] = len(df)
            status["columns"] = list(df.columns)
        else:
            status["status"] = "no_data"
    except Exception as e:
        status["status"] = "error"
        status["error"] = str(e)

    return status
