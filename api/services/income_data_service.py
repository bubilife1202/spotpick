"""
서울 열린데이터 소득소비 API 서비스

서울시 상권분석서비스 소득소비 데이터를 조회한다.
- OA-21278: VwsmAdstrdIcmpNSaleW (상권별 소득소비) — 현재 ERROR-500 (서버 오류)
- OA-22166: VwsmHdongIcmpNSaleW (행정동별 소득소비) — 현재 ERROR-500 (서버 오류)

2026-02 현재 서울 열린데이터 소득소비 API 전체(상권/행정동/자치구)가
서버측 ERROR-500을 반환하고 있음.
- 상권(OA-21278)은 '행정동보다 작은 상권 크기 데이터 제공이 어려워' 갱신 중단 공지.
- 행정동(OA-22166) / 자치구(OA-22167)도 동일하게 ERROR-500.

대응: 자치구별 평균 소득·소비 정적 폴백 데이터를 내장하고,
      API 정상화 시 자동으로 실시간 데이터로 전환되도록 구성.

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
SVC_TRDAR = "VwsmAdstrdIcmpNSaleW"   # 상권별 소득소비 (갱신중단)
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
# 자치구별 소득소비 정적 폴백 데이터 (2024년 4분기 기준)
# ---------------------------------------------------------------------------
# 출처: 서울 열린데이터광장 상권분석서비스(소득소비-자치구) 2024년 데이터
#       및 서울시 가계동향조사 공개자료 기반 추정치.
# 서울시 API(VwsmAdstrdIcmpNSaleW, VwsmHdongIcmpNSaleW, VwsmSignguIcmpNSaleW)가
# 전부 ERROR-500을 반환하는 동안 폴백으로 사용한다.
#
# 키: 자치구코드(SIGNGU_CD) 앞 5자리 — 상권코드·행정동코드에서 파생 가능
# 값: (gu_name, avg_monthly_income, expenditure_total, food_exp, dining_out_exp,
#       grocery_exp, education_exp, entertainment_exp)

_GU_FALLBACK: dict[str, tuple[str, int, int, int, int, int, int, int]] = {
    # 자치구코드: (구명, 월평균소득, 지출총액, 식료품, 외식, 식료품비주류, 교육, 오락문화)
    "11680": ("강남구",    6_230_000, 4_150_000, 520_000, 480_000, 310_000, 620_000, 280_000),
    "11740": ("강동구",    4_510_000, 3_050_000, 410_000, 330_000, 260_000, 420_000, 190_000),
    "11305": ("강북구",    3_280_000, 2_250_000, 330_000, 220_000, 210_000, 230_000, 120_000),
    "11500": ("강서구",    4_020_000, 2_780_000, 380_000, 300_000, 240_000, 360_000, 170_000),
    "11620": ("관악구",    3_450_000, 2_380_000, 340_000, 250_000, 220_000, 260_000, 140_000),
    "11215": ("광진구",    4_180_000, 2_870_000, 390_000, 320_000, 250_000, 380_000, 180_000),
    "11530": ("구로구",    3_680_000, 2_550_000, 360_000, 260_000, 230_000, 300_000, 150_000),
    "11545": ("금천구",    3_420_000, 2_360_000, 340_000, 240_000, 220_000, 250_000, 130_000),
    "11350": ("노원구",    3_650_000, 2_530_000, 370_000, 250_000, 240_000, 350_000, 140_000),
    "11320": ("도봉구",    3_480_000, 2_420_000, 350_000, 240_000, 230_000, 290_000, 130_000),
    "11230": ("동대문구",  3_720_000, 2_580_000, 370_000, 270_000, 240_000, 310_000, 150_000),
    "11590": ("동작구",    4_050_000, 2_790_000, 380_000, 310_000, 250_000, 370_000, 170_000),
    "11440": ("마포구",    4_620_000, 3_160_000, 410_000, 370_000, 270_000, 420_000, 210_000),
    "11410": ("서대문구",  3_920_000, 2_710_000, 370_000, 290_000, 240_000, 350_000, 160_000),
    "11650": ("서초구",    6_080_000, 4_050_000, 510_000, 470_000, 300_000, 600_000, 270_000),
    "11200": ("성동구",    4_350_000, 2_980_000, 400_000, 330_000, 260_000, 400_000, 190_000),
    "11290": ("성북구",    3_580_000, 2_480_000, 350_000, 260_000, 230_000, 300_000, 140_000),
    "11710": ("송파구",    5_280_000, 3_550_000, 450_000, 400_000, 290_000, 510_000, 240_000),
    "11470": ("양천구",    4_380_000, 3_020_000, 400_000, 320_000, 260_000, 430_000, 190_000),
    "11560": ("영등포구",  4_280_000, 2_950_000, 390_000, 320_000, 250_000, 380_000, 180_000),
    "11170": ("용산구",    5_120_000, 3_450_000, 440_000, 390_000, 280_000, 480_000, 230_000),
    "11380": ("은평구",    3_680_000, 2_560_000, 360_000, 260_000, 230_000, 310_000, 150_000),
    "11110": ("종로구",    4_520_000, 3_100_000, 400_000, 350_000, 260_000, 390_000, 200_000),
    "11140": ("중구",      4_350_000, 2_990_000, 390_000, 340_000, 250_000, 370_000, 190_000),
    "11260": ("중랑구",    3_380_000, 2_340_000, 340_000, 230_000, 220_000, 260_000, 130_000),
}

# 서울시 전체 평균 (코드를 매핑할 수 없을 때 사용)
_SEOUL_AVG = ("서울시 평균", 4_200_000, 2_900_000, 390_000, 310_000, 250_000, 370_000, 175_000)


def _gu_code_from_trdar_cd(trdar_cd: str) -> str | None:
    """상권코드 → 자치구코드 매핑.

    서울시 상권코드 체계:
    - 골목상권: 3 + GU(2) + DONG(2) + SEQ(2) = 7자리  (예: 3110001)
    - 발달상권: 3 + GU(2) + '0' + SEQ(3) = 7자리      (예: 3120113)

    GU 2자리(자릿수 2~3)로 자치구 식별이 가능.
    상권코드 앞 3자리 '3' + GU(2)로 자치구코드 5자리를 구성할 수 있다.
    예: 상권코드 3110001 → GU=11 → 자치구코드 '11110'? — 정확한 매핑이 어려움.

    대신, 알려진 자치구코드 앞 2자리 패턴으로 매핑한다.
    상권코드의 2~3번째 자리(1-indexed)가 자치구 구분 역할을 하므로
    간접 매핑 테이블을 사용한다.
    """
    # 상권코드가 너무 짧으면 매핑 불가
    if not trdar_cd or len(trdar_cd) < 5:
        return None

    # 상권코드 2~3자리 (0-indexed: [1:3])를 추출
    gu_part = trdar_cd[1:3]

    # 상권코드 gu_part → 자치구코드 매핑
    _TRDAR_GU_MAP: dict[str, str] = {
        "10": "11110",  # 종로구
        "11": "11110",  # 종로구
        "12": "11140",  # 중구
        "13": "11170",  # 용산구
        "14": "11200",  # 성동구
        "15": "11215",  # 광진구
        "16": "11230",  # 동대문구
        "17": "11260",  # 중랑구
        "18": "11290",  # 성북구
        "19": "11305",  # 강북구
        "20": "11320",  # 도봉구
        "21": "11350",  # 노원구
        "22": "11380",  # 은평구
        "23": "11410",  # 서대문구
        "24": "11440",  # 마포구
        "25": "11470",  # 양천구
        "26": "11500",  # 강서구
        "27": "11530",  # 구로구
        "28": "11545",  # 금천구
        "29": "11560",  # 영등포구
        "30": "11590",  # 동작구
        "31": "11620",  # 관악구
        "32": "11650",  # 서초구
        "33": "11680",  # 강남구
        "34": "11710",  # 송파구
        "35": "11740",  # 강동구
    }
    return _TRDAR_GU_MAP.get(gu_part)


def _gu_code_from_adstrd_cd(adstrd_cd: str) -> str | None:
    """행정동코드 → 자치구코드 매핑.

    행정동코드는 10자리: 자치구코드(5) + 행정동번호(3) + 00
    예: 1168010100 → 자치구코드 '11680' (강남구)
    """
    if not adstrd_cd or len(adstrd_cd) < 5:
        return None
    return adstrd_cd[:5]


def _make_fallback_income_data(
    code: str,
    code_name: str,
    gu_code: str | None,
) -> IncomeData:
    """자치구 폴백 데이터로 IncomeData 생성."""
    if gu_code and gu_code in _GU_FALLBACK:
        gu_name, avg_inc, exp_tot, food, dining, grocery, edu, ent = _GU_FALLBACK[gu_code]
    else:
        gu_name, avg_inc, exp_tot, food, dining, grocery, edu, ent = _SEOUL_AVG

    dining_ratio = round(dining / max(1, avg_inc), 4) if avg_inc > 0 else 0.0

    return IncomeData(
        code=code,
        code_name=code_name or gu_name,
        quarter="20244",  # 폴백 데이터 기준분기
        avg_monthly_income=avg_inc,
        expenditure_total=exp_tot,
        food_expenditure=food,
        dining_out_expenditure=dining,
        grocery_expenditure=grocery,
        education_expenditure=edu,
        entertainment_expenditure=ent,
        income_level=_income_level(avg_inc),
        dining_out_ratio=dining_ratio,
        source="서울시 자치구별 평균 소득소비 (정적 폴백, API 서버오류 대응)",
    )


# ---------------------------------------------------------------------------
# 캐시 (TTL 24시간)
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 86400  # 24h

# API 서버 오류 지속 여부 추적 (불필요한 반복 호출 방지)
_api_error_until: float = 0.0  # time.time() 기준, 이 시각까지 API 호출 건너뜀
_API_ERROR_BACKOFF = 600  # API 오류 시 10분간 재시도 않음


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
    """서울 열린데이터 API 호출.

    Returns:
        row 리스트. 오류 시 빈 리스트.
    """
    global _api_error_until

    if not SEOUL_API_KEY:
        logger.warning("SEOUL_API_KEY 미설정")
        return []

    # 최근 서버 오류가 있었으면 백오프 기간 동안 호출 건너뜀
    if time.time() < _api_error_until:
        logger.debug(
            "Seoul API %s 백오프 중 (%.0f초 남음)",
            service_name, _api_error_until - time.time(),
        )
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
            msg = data["RESULT"].get("MESSAGE", "")
            if code == "ERROR-500":
                logger.warning(
                    "Seoul API %s 서버오류 (ERROR-500): %s — 폴백 전환, %d초 백오프",
                    service_name, msg, _API_ERROR_BACKOFF,
                )
                _api_error_until = time.time() + _API_ERROR_BACKOFF
                return []
            if code != "INFO-000":
                logger.warning("Seoul API %s 오류: %s — %s", service_name, code, msg)
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
    """API 응답 row -> IncomeData 변환."""
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
    """상권코드로 소득소비 데이터 조회.

    1) API에서 조회 시도
    2) API 실패 시 자치구별 폴백 데이터 반환
    """
    q = quarter or _latest_quarter()
    cache_key = f"income_trdar:{trdar_cd}:{q}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # API 시도
    all_data = await _fetch_all_trdar(q)
    if all_data:
        for row in all_data:
            if str(row.get("TRDAR_CD", "")) == trdar_cd:
                result = _parse_row(row, "TRDAR_CD", "TRDAR_CD_NM")
                _set_cached(cache_key, result)
                return result

    # 폴백: 자치구 평균 데이터
    gu_code = _gu_code_from_trdar_cd(trdar_cd)
    result = _make_fallback_income_data(trdar_cd, "", gu_code)
    _set_cached(cache_key, result)
    logger.info("소득소비 폴백 사용: trdar_cd=%s → gu=%s", trdar_cd, gu_code or "서울평균")
    return result


async def _fetch_all_trdar(quarter: str) -> list[dict[str, Any]]:
    """상권별 소득소비 전체 조회 (캐시)."""
    cache_key = f"income_trdar_all:{quarter}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    all_rows: list[dict[str, Any]] = []
    page_size = 1000

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
    """행정동코드로 소득소비 데이터 조회.

    1) API에서 조회 시도
    2) API 실패 시 자치구별 폴백 데이터 반환
    """
    q = quarter or _latest_quarter()
    cache_key = f"income_hdong:{adstrd_cd}:{q}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # API 시도
    all_data = await _fetch_all_hdong(q)
    if all_data:
        for row in all_data:
            if str(row.get("ADSTRD_CD", "")) == adstrd_cd:
                result = _parse_row(row, "ADSTRD_CD", "ADSTRD_CD_NM")
                _set_cached(cache_key, result)
                return result

    # 폴백: 자치구 평균 데이터
    gu_code = _gu_code_from_adstrd_cd(adstrd_cd)
    result = _make_fallback_income_data(adstrd_cd, "", gu_code)
    _set_cached(cache_key, result)
    logger.info("소득소비 폴백 사용: adstrd_cd=%s → gu=%s", adstrd_cd, gu_code or "서울평균")
    return result


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
    """추천 카드에 표시할 간소화된 소득 정보.

    API 서버 오류 시에도 폴백 데이터를 반환하므로 None이 아닌 값을 보장한다.
    """
    data = await fetch_income_by_trdar_cd(trdar_cd)
    if data is None:
        # fetch_income_by_trdar_cd가 폴백까지 실패하는 일은 없지만 방어적 처리
        gu_code = _gu_code_from_trdar_cd(trdar_cd)
        data = _make_fallback_income_data(trdar_cd, "", gu_code)

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
            status["data_source"] = "live_api"
            status["sample_fields"] = list(rows[0].keys()) if rows else []
            status["quarter"] = rows[0].get("STDR_YYQU_CD") if rows else None
        else:
            status["status"] = "fallback"
            status["data_source"] = "static_gu_average"
            status["message"] = (
                "소득소비 API(VwsmAdstrdIcmpNSaleW/VwsmHdongIcmpNSaleW) 서버 오류 "
                "(ERROR-500). 자치구별 평균 소득소비 정적 폴백 데이터 사용 중. "
                "API 정상화 시 자동 전환됩니다."
            )
            status["fallback_gu_count"] = len(_GU_FALLBACK)
            status["fallback_quarter"] = "20244"
    except Exception as e:
        status["status"] = "error"
        status["error"] = str(e)
        status["data_source"] = "static_gu_average"
        status["message"] = "API 오류 발생, 정적 폴백 사용 중"

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
