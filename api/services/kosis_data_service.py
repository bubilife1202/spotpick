"""
KOSIS (국가통계포털) 외식업체경영실태조사 데이터 서비스

통계청 KOSIS Open API (PublicDataReader)를 통해 업종별 원가구조·수익성·객단가를 조회한다.
시뮬레이션의 하드코딩 원가율을 실제 정부 조사 데이터로 대체하기 위한 서비스.

사용 통계표 (orgId=114, 외식업체경영실태조사):
- DT_114054_029: 수익성·생산성 분석  (분류1: A/특성별, 항목: T001~T006)
- DT_114054_028: 사업실적 (매출액/식재료비/인건비/임차료) (분류1: A/사업실적별, 분류2: B/특성별)
- DT_114054_031: 식재료비 사용  (분류1+분류2)
- DT_114054_022: 객단가  (분류1: A/특성별, 분류2: B/객단가분포별)

KOSIS API 파라미터 주의사항:
- objL1/objL2 에 "ALL" 을 넣어야 전체 조회 (구체 코드는 A01, B01 등 — T1, 01 같은 축약형 불가)
- itmId 에 "ALL" 사용 가능 (구체 코드는 T001, T002 등)
- 2-레벨 분류 테이블은 objL2 누락 시 에러 20 ("필수요청변수값이 누락")
- 잘못된 코드 전달 시 에러 21 ("잘못된 요청 변수를 호출 하였습니다")
- prdSe="Y" (연간), startPrdDe/endPrdDe 로 조회 기간 지정
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, TypedDict

import requests as _requests

logger = logging.getLogger(__name__)

KOSIS_API_KEY = os.getenv("KOSIS_API_KEY", "")

# 최신 이용 가능 연도 (외식업체경영실태조사: 2018~2024)
DEFAULT_YEAR = "2024"

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


class SingleHouseholdData(TypedDict, total=False):
    ratio: float                 # 1인가구 비율 (0.0~1.0)
    count: int                   # 1인가구 수
    total_households: int        # 전체 가구 수
    year: str
    source: str
    by_district: list[dict]      # 시도별 상세 (선택적)


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
# KOSIS API 호출
# ---------------------------------------------------------------------------
# PublicDataReader 라이브러리가 있으면 사용하고, 없으면 직접 HTTP 호출.
#
# PublicDataReader 내부 동작 (kosis.py):
#   URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do?method=getList"
#   params = {apiKey: unquote(key), format: "json", jsonVD: "Y", jsonMVD: "Y", ...kwargs}
#   → requests.get(url, params=params) → JSON 파싱 → DataFrame
#
# 직접 호출 시에도 동일한 파라미터를 사용한다.
# ---------------------------------------------------------------------------

_KOSIS_STAT_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"


def _get_kosis_client():
    """Kosis 클라이언트를 생성. PublicDataReader 미설치 시 None 반환."""
    if not KOSIS_API_KEY:
        logger.warning("KOSIS_API_KEY 미설정")
        return None
    try:
        from PublicDataReader import Kosis  # type: ignore[import-not-found]
        return Kosis(KOSIS_API_KEY)
    except ImportError:
        logger.info("PublicDataReader 미설치 — 직접 HTTP 호출 모드로 전환")
        return None
    except Exception as e:
        logger.warning("Kosis 클라이언트 생성 실패: %s — 직접 HTTP 호출 모드로 전환", e)
        return None


def _fetch_raw_json(api_params: dict[str, str]) -> list[dict] | None:
    """
    PublicDataReader 없이 KOSIS REST API를 직접 호출한다.
    성공 시 list[dict], 에러/빈 데이터 시 None.
    """
    params = {
        "method": "getList",
        "apiKey": _requests.utils.unquote(KOSIS_API_KEY),
        "format": "json",
        "jsonVD": "Y",
        "jsonMVD": "Y",
        **api_params,
    }
    try:
        resp = _requests.get(_KOSIS_STAT_URL, params=params, timeout=30, verify=False)
        data = resp.json()
    except Exception as e:
        logger.warning("KOSIS HTTP 요청 실패: %s", e)
        return None

    if isinstance(data, dict):
        err = data.get("err")
        err_msg = data.get("errMsg", "")
        if err:
            logger.warning("KOSIS API 에러 (err=%s): %s  [params: orgId=%s, tblId=%s]",
                           err, err_msg, api_params.get("orgId"), api_params.get("tblId"))
        return None

    if isinstance(data, list) and len(data) > 0:
        return data
    return None


def _raw_json_to_df(rows: list[dict]) -> Any:
    """list[dict] → pandas DataFrame (한글 컬럼명으로 변환)."""
    import pandas as pd  # type: ignore[import-not-found]

    rename = {
        "ORG_ID": "기관ID", "TBL_ID": "통계표ID", "TBL_NM": "통계표명",
        "C1_OBJ_NM": "분류명1", "C1_NM": "분류값명1", "C1": "분류값ID1",
        "C2_OBJ_NM": "분류명2", "C2_NM": "분류값명2", "C2": "분류값ID2",
        "C3_OBJ_NM": "분류명3", "C3_NM": "분류값명3", "C3": "분류값ID3",
        "ITM_ID": "항목ID", "ITM_NM": "항목명", "ITM_NM_ENG": "항목영문명",
        "UNIT_NM": "단위명", "UNIT_NM_ENG": "단위영문명", "UNIT_ID": "단위ID",
        "PRD_SE": "수록주기", "PRD_DE": "수록시점", "DT": "수치값",
    }
    df = pd.DataFrame(rows).rename(columns=rename)
    return df.dropna(axis=1, how="all")


# 2개 분류 레벨이 있는 테이블 (objL2 필요)
_TWO_LEVEL_TABLES = {"DT_114054_028", "DT_114054_022", "DT_114054_031"}


def _fetch_table(tbl_id: str, year: str = DEFAULT_YEAR) -> Any:
    """
    KOSIS 통계표 조회 → pandas DataFrame 반환.
    실패 시 None.

    일부 테이블은 분류 레벨이 1개(objL1만), 일부는 2개(objL1+objL2).
    잘못된 파라미터 전달 시 KOSIS API가 에러를 반환하므로 구분 처리.

    **중요 파라미터 규칙:**
    - objL1, objL2, itmId 에는 반드시 "ALL" 또는 유효한 분류값ID (예: A01, B0101, T001)를 사용.
      축약형(01, T1 등)은 에러 21("잘못된 요청 변수")을 발생시킴.
    - 2-레벨 분류 테이블에서 objL2를 누락하면 에러 20("필수요청변수값이 누락")이 발생.
    """
    cache_key = f"kosis_raw:{tbl_id}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    api_params: dict[str, str] = {
        "orgId": "114",
        "tblId": tbl_id,
        "objL1": "ALL",
        "itmId": "ALL",
        "prdSe": "Y",
        "startPrdDe": year,
        "endPrdDe": year,
    }
    if tbl_id in _TWO_LEVEL_TABLES:
        api_params["objL2"] = "ALL"

    # 방법 1: PublicDataReader 사용
    client = _get_kosis_client()
    if client is not None:
        try:
            df = client.get_data(service_name="통계자료", **api_params)
            if df is not None and len(df) > 0:
                _set_cached(cache_key, df)
                logger.debug("KOSIS %s (%s): PublicDataReader로 %d행 조회 성공", tbl_id, year, len(df))
                return df
        except Exception as e:
            logger.warning("KOSIS %s PublicDataReader 조회 실패: %s — 직접 HTTP로 재시도", tbl_id, e)

    # 방법 2: 직접 HTTP 호출 (PublicDataReader 미설치 또는 실패 시)
    if not KOSIS_API_KEY:
        logger.warning("KOSIS_API_KEY 미설정")
        return None

    raw = _fetch_raw_json(api_params)
    if raw:
        try:
            df = _raw_json_to_df(raw)
            if len(df) > 0:
                _set_cached(cache_key, df)
                logger.debug("KOSIS %s (%s): 직접 HTTP로 %d행 조회 성공", tbl_id, year, len(df))
                return df
        except Exception as e:
            logger.warning("KOSIS %s JSON→DataFrame 변환 실패: %s", tbl_id, e)

    logger.info("KOSIS %s (%s): 데이터 없음", tbl_id, year)
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
    year: str = DEFAULT_YEAR,
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
    year: str = DEFAULT_YEAR,
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
    year: str = DEFAULT_YEAR,
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
    year: str = DEFAULT_YEAR,
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
# Public API: 1인가구 비율 (장래가구추계)
# ---------------------------------------------------------------------------

# 시도 이름 → KOSIS 분류값 매핑
_REGION_ALIAS: dict[str, str] = {
    "서울": "서울특별시",
    "부산": "부산광역시",
    "대구": "대구광역시",
    "인천": "인천광역시",
    "광주": "광주광역시",
    "대전": "대전광역시",
    "울산": "울산광역시",
    "세종": "세종특별자치시",
    "경기": "경기도",
    "강원": "강원도",
    "충북": "충청북도",
    "충남": "충청남도",
    "전북": "전라북도",
    "전남": "전라남도",
    "경북": "경상북도",
    "경남": "경상남도",
    "제주": "제주특별자치도",
}


def _normalize_region(region: str) -> str:
    """사용자 입력 지역명을 KOSIS 분류값명으로 정규화."""
    region = region.strip()
    if region in _REGION_ALIAS:
        return _REGION_ALIAS[region]
    # 이미 정식 명칭이면 그대로
    for full_name in _REGION_ALIAS.values():
        if region == full_name:
            return region
    # 부분 매칭 시도
    for short, full in _REGION_ALIAS.items():
        if short in region or region in full:
            return full
    return region


def _fetch_household_table(year: str = "2025") -> Any:
    """
    DT_1BZ0506 (가구주의 연령/가구원수별 추계가구_시도) 조회.
    orgId=101 (통계청), 장래가구추계.
    """
    cache_key = f"kosis_household_raw:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    client = _get_kosis_client()
    if client is None:
        return None

    try:
        df = client.get_data(
            service_name="통계자료",
            orgId="101",
            tblId="DT_1BZ0506",
            objL1="ALL",
            objL2="ALL",
            itmId="ALL",
            prdSe="Y",
            startPrdDe=year,
            endPrdDe=year,
        )
        if df is not None and len(df) > 0:
            _set_cached(cache_key, df)
            return df
        logger.info("KOSIS DT_1BZ0506 (%s): 데이터 없음", year)
        return None
    except Exception as e:
        logger.warning("KOSIS DT_1BZ0506 조회 실패: %s", e)
        return None


async def get_single_household_ratio(
    region: str = "서울특별시",
    year: str = "2025",
) -> SingleHouseholdData | None:
    """
    KOSIS 장래가구추계에서 지역별 1인가구 비율 조회.

    DT_1BZ0506 테이블 구조:
    - 분류값명1: 시도 (서울특별시, 부산광역시 ...)
    - 분류값명2: 연령 (합계, 24세이하, ...)
    - 항목명: 가구원수 (계, 1인, 2인, 3인, 4인, 5인이상)
    - 수치값: 가구 수
    """
    normalized = _normalize_region(region)
    cache_key = f"kosis_household:{normalized}:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    df = _fetch_household_table(year)
    if df is None:
        # 1년 전 데이터로 재시도
        prev_year = str(int(year) - 1)
        df = _fetch_household_table(prev_year)
        if df is None:
            return None
        year = prev_year

    try:
        # '합계' 연령대만 필터 (전체 합산)
        total_age = df[df["분류값명2"] == "합계"]

        # 특정 지역 데이터
        region_data = total_age[total_age["분류값명1"] == normalized]
        if region_data.empty:
            logger.info("KOSIS 1인가구: %s 매칭 실패", normalized)
            return None

        total_row = region_data[region_data["항목명"] == "계"]
        single_row = region_data[region_data["항목명"] == "1인"]

        if total_row.empty or single_row.empty:
            return None

        total_val = _safe_float(total_row.iloc[0]["수치값"])
        single_val = _safe_float(single_row.iloc[0]["수치값"])

        if total_val is None or single_val is None or total_val == 0:
            return None

        ratio = single_val / total_val

        result = SingleHouseholdData(
            ratio=round(ratio, 4),
            count=int(single_val),
            total_households=int(total_val),
            year=year,
            source=f"KOSIS 장래가구추계 {year}",
        )

        # 전국 데이터일 때: 시도별 상세 포함
        if normalized in ("전국",):
            by_district: list[dict] = []
            for reg_name in total_age["분류값명1"].unique():
                if reg_name == "전국":
                    continue
                rd = total_age[total_age["분류값명1"] == reg_name]
                t = _safe_float(rd[rd["항목명"] == "계"].iloc[0]["수치값"]) if len(rd[rd["항목명"] == "계"]) > 0 else None
                s = _safe_float(rd[rd["항목명"] == "1인"].iloc[0]["수치값"]) if len(rd[rd["항목명"] == "1인"]) > 0 else None
                if t and s and t > 0:
                    by_district.append({
                        "region": reg_name,
                        "ratio": round(s / t, 4),
                        "count": int(s),
                        "total": int(t),
                    })
            by_district.sort(key=lambda x: x["ratio"], reverse=True)
            result["by_district"] = by_district

        _set_cached(cache_key, result)
        return result

    except Exception as e:
        logger.warning("KOSIS 1인가구 비율 파싱 실패: %s", e)
        return None


async def get_region_household_ratios(year: str = "2025") -> dict[str, float]:
    """
    전체 시도의 1인가구 비율을 dict로 반환.
    {"서울특별시": 0.402, "부산광역시": 0.371, ...}
    추천 카드에 뱃지로 표시할 때 사용.
    """
    cache_key = f"kosis_household_all:{year}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    df = _fetch_household_table(year)
    if df is None:
        prev_year = str(int(year) - 1)
        df = _fetch_household_table(prev_year)
        if df is None:
            return {}

    try:
        total_age = df[df["분류값명2"] == "합계"]
        ratios: dict[str, float] = {}

        for region_name in total_age["분류값명1"].unique():
            rd = total_age[total_age["분류값명1"] == region_name]
            t = _safe_float(rd[rd["항목명"] == "계"].iloc[0]["수치값"]) if len(rd[rd["항목명"] == "계"]) > 0 else None
            s = _safe_float(rd[rd["항목명"] == "1인"].iloc[0]["수치값"]) if len(rd[rd["항목명"] == "1인"]) > 0 else None
            if t and s and t > 0:
                ratios[region_name] = round(s / t, 4)

        _set_cached(cache_key, ratios)
        return ratios

    except Exception as e:
        logger.warning("KOSIS 전체 시도 1인가구 비율 조회 실패: %s", e)
        return {}


# ---------------------------------------------------------------------------
# 헬스 체크
# ---------------------------------------------------------------------------

async def health_check() -> dict[str, Any]:
    """KOSIS API 연결 상태 확인 — PublicDataReader 또는 직접 HTTP 모두 테스트"""
    status: dict[str, Any] = {
        "service": "kosis_data",
        "api_key_configured": bool(KOSIS_API_KEY),
        "default_year": DEFAULT_YEAR,
    }

    if not KOSIS_API_KEY:
        status["status"] = "no_api_key"
        return status

    try:
        # _fetch_table 은 PublicDataReader → 직접 HTTP 순으로 fallback 한다
        df = _fetch_table("DT_114054_029", DEFAULT_YEAR)
        if df is not None and len(df) > 0:
            status["status"] = "ok"
            status["sample_rows"] = len(df)
            status["columns"] = list(df.columns)
            status["year"] = DEFAULT_YEAR
        else:
            status["status"] = "no_data"
            status["hint"] = (
                "KOSIS API 응답이 비었습니다. API Key가 유효한지, "
                "orgId=114/tblId=DT_114054_029 테이블이 존재하는지 확인하세요."
            )
    except Exception as e:
        status["status"] = "error"
        status["error"] = str(e)

    return status
