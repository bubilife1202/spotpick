from __future__ import annotations

import logging
import os
from typing import cast

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.kakao_local_service import (
    KAKAO_KEYWORD_URL,
    KAKAO_REST_API_KEY,
    get_kakao_local_service,
)
from api.services.trend_service import get_trend_service

NAVER_SEARCH_URL = "https://map.naver.com/v5/api/search"
NAVER_PLACE_URL = "https://map.naver.com/v5/api/sites/summary"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmark")

CATEGORY_TO_INDUSTRY: dict[str, str] = {
    "카페": "CS100010",
    "커피": "CS100010",
    "한식": "CS100001",
    "중식": "CS100002",
    "일식": "CS100003",
    "양식": "CS100004",
    "베이커리": "CS100005",
    "제과": "CS100005",
    "패스트푸드": "CS100006",
    "치킨": "CS100007",
    "분식": "CS100008",
    "호프": "CS100009",
    "술집": "CS100009",
}

INDUSTRY_NAMES: dict[str, str] = {
    "CS100001": "한식",
    "CS100002": "중식",
    "CS100003": "일식",
    "CS100004": "양식",
    "CS100005": "베이커리",
    "CS100006": "패스트푸드",
    "CS100007": "치킨",
    "CS100008": "분식",
    "CS100009": "호프/주점",
    "CS100010": "카페",
}


class BenchmarkStoreItem(BaseModel):
    id: str
    name: str
    category: str
    address: str
    road_address: str
    phone: str
    place_url: str
    x: float
    y: float
    industry_code: str
    industry_name: str


class BenchmarkSearchResponse(BaseModel):
    results: list[BenchmarkStoreItem]
    query: str


def _derive_industry_code(category_name: str) -> str:
    for keyword, industry_code in CATEGORY_TO_INDUSTRY.items():
        if keyword in category_name:
            return industry_code
    return "CS100010"


def _to_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _to_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


@router.get("/search", response_model=BenchmarkSearchResponse)
async def search_benchmark_store(
    query: str,
) -> BenchmarkSearchResponse:
    if not query.strip():
        raise HTTPException(status_code=400, detail="query는 필수입니다")

    service = get_kakao_local_service()
    if not service.available:
        raise HTTPException(status_code=503, detail="카카오 로컬 API 키가 설정되지 않았습니다")

    params = {
        "query": query,
        "size": 5,
    }
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(KAKAO_KEYWORD_URL, params=params, headers=headers)
            _ = response.raise_for_status()
            payload = cast(object, response.json())
    except Exception as exc:
        logger.error("벤치마킹 매장 검색 실패: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=502, detail="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )

    payload_dict: dict[str, object] = (
        cast(dict[str, object], payload) if isinstance(payload, dict) else {}
    )
    documents_raw = payload_dict.get("documents")
    documents: list[object] = (
        cast(list[object], documents_raw) if isinstance(documents_raw, list) else []
    )
    results: list[BenchmarkStoreItem] = []

    for raw_doc in documents:
        if not isinstance(raw_doc, dict):
            continue
        doc = cast(dict[str, object], raw_doc)
        category_name = _to_str(doc.get("category_name"))
        industry_code = _derive_industry_code(category_name)
        results.append(
            BenchmarkStoreItem(
                id=_to_str(doc.get("id")),
                name=_to_str(doc.get("place_name")),
                category=category_name,
                address=_to_str(doc.get("address_name")),
                road_address=_to_str(doc.get("road_address_name")),
                phone=_to_str(doc.get("phone")),
                place_url=_to_str(doc.get("place_url")),
                x=_to_float(doc.get("x")),
                y=_to_float(doc.get("y")),
                industry_code=industry_code,
                industry_name=INDUSTRY_NAMES.get(industry_code, "카페"),
            )
        )

    return BenchmarkSearchResponse(results=results, query=query)


# ─── Phase 2: Benchmark Analyze ──────────────────────────────────────────


class BenchmarkAnalyzeRequest(BaseModel):
    name: str
    x: float  # longitude
    y: float  # latitude
    category: str = ""
    industry_code: str = "CS100010"
    target_district_name: str = ""


class NaverPlaceProfile(BaseModel):
    naver_id: str = ""
    name: str = ""
    category: str = ""
    review_count: int = 0
    review_score: float = 0.0
    blog_review_count: int = 0
    visitor_review_count: int = 0
    keywords: list[str] = []
    business_hours: dict[str, str] = {}


class NearbyCompetitor(BaseModel):
    name: str
    category: str
    distance: int  # meters
    address: str


class DemandValidation(BaseModel):
    search_trend_keyword: str = ""
    search_trend_data: list[dict[str, object]] = []
    trend_direction: str = ""
    trend_avg_ratio: float = 0.0
    same_category_count_nearby: int = 0
    demand_verdict: str = ""
    demand_summary: str = ""


class SuccessFactor(BaseModel):
    factor: str
    category: str
    importance: str
    actionable_tip: str


class SuccessAnalysis(BaseModel):
    factors: list[SuccessFactor] = []
    summary: str = ""


class BenchmarkAnalyzeResponse(BaseModel):
    store_name: str
    store_category: str
    naver_profile: NaverPlaceProfile
    nearby_competitors: list[NearbyCompetitor]
    competitor_count: int
    location_summary: str
    demand: DemandValidation = DemandValidation()
    success_analysis: SuccessAnalysis = SuccessAnalysis()


_KEYWORD_FACTOR_MAP: dict[str, tuple[str, str]] = {
    "깨끗": ("atmosphere", "청결한 매장 관리"),
    "친절": ("service", "친절한 고객 응대"),
    "가격": ("price", "합리적 가격 정책"),
    "저렴": ("price", "가성비 좋은 가격"),
    "분위기": ("atmosphere", "좋은 매장 분위기"),
    "인테리어": ("atmosphere", "감각적 인테리어"),
    "메뉴": ("product", "다양한 메뉴 구성"),
    "맛": ("product", "맛있는 음료/음식"),
    "디저트": ("product", "매력적인 디저트"),
    "뷰": ("atmosphere", "좋은 전망/뷰"),
    "넓": ("atmosphere", "넓은 좌석 공간"),
    "조용": ("atmosphere", "조용한 분위기"),
    "만화": ("product", "풍부한 만화 장서"),
    "게임": ("product", "다양한 게임 구비"),
    "콘센트": ("service", "충전/작업 편의시설"),
    "주차": ("service", "주차 편의"),
    "위치": ("location", "좋은 접근성"),
    "역": ("location", "역세권 입지"),
}

_FACTOR_TIP_MAP: dict[str, str] = {
    "청결한 매장 관리": "매일 영업 전후 체크리스트 기반 청소를 실시하세요",
    "친절한 고객 응대": "직원 응대 스크립트와 컴플레인 대응 매뉴얼을 만들어 교육하세요",
    "합리적 가격 정책": "경쟁 매장 대비 5-10% 낮은 가격으로 시작하여 고객을 확보하세요",
    "가성비 좋은 가격": "세트 메뉴나 시간대 할인으로 체감 가성비를 높이세요",
    "좋은 매장 분위기": "조명·음악·좌석 배치를 통일해 매장 콘셉트를 명확히 하세요",
    "감각적 인테리어": "포토존 1곳을 만들고 SNS 업로드 유도 문구를 배치하세요",
    "다양한 메뉴 구성": "핵심 메뉴 3종과 계절 한정 메뉴를 함께 운영해 선택 폭을 넓히세요",
    "맛있는 음료/음식": "대표 메뉴 레시피를 표준화하고 주 1회 품질 점검을 진행하세요",
    "매력적인 디저트": "비주얼 중심 디저트 2-3종을 시그니처로 고정 운영하세요",
    "좋은 전망/뷰": "창가 좌석 예약/안내를 강화해 체류 만족도를 높이세요",
    "넓은 좌석 공간": "테이블 간 최소 간격을 확보해 쾌적한 동선을 유지하세요",
    "조용한 분위기": "시간대별 볼륨 기준을 정하고 소음 유발 구역을 분리하세요",
    "풍부한 만화 장서": "오픈 시 최소 500~1000권 구비하고, 월 신간 업데이트 예산을 책정하세요",
    "다양한 게임 구비": "입문/전략/파티 게임을 균형 있게 100종 이상 구성하세요",
    "충전/작업 편의시설": "좌석별 콘센트와 와이파이 안내를 명확히 제공하세요",
    "주차 편의": "가까운 제휴 주차장을 확보하고 무료 주차 조건을 안내하세요",
    "좋은 접근성": "유동인구 많은 동선과 출입구 가시성을 우선 확보하세요",
    "역세권 입지": "도보 5분 이내 역 출구 기준으로 점포를 우선 검토하세요",
    "만화/콘텐츠 큐레이션이 핵심 경쟁력": "장르별 인기작과 신간을 월 단위로 큐레이션해 재방문을 유도하세요",
    "게임 다양성과 진행 도우미가 핵심": "난이도별 추천표와 룰 설명 가능 직원을 운영해 첫 방문 장벽을 낮추세요",
    "비주얼 디저트와 SNS 노출이 핵심": "사진 촬영 동선을 고려한 플레이팅과 업로드 이벤트를 운영하세요",
    "경쟁 치열 — 차별화 포인트 1가지 이상 필수": "가격·상품·공간 중 한 영역에서 명확한 1등 포인트를 설계하세요",
    "높은 고객 만족도 — 같은 수준 유지 필수": "리뷰 모니터링과 즉시 피드백 대응으로 평점 4.5+를 유지하세요",
    "양호한 평점 — 서비스 품질 관리 중요": "주간 CS 점검으로 평점 하락 요소를 선제적으로 개선하세요",
    "평점 개선 여지 있음 — 차별화 기회": "저평점 리뷰 원인을 분류해 2주 단위 개선 과제를 실행하세요",
}


def _extract_success_factors(
    naver_profile: NaverPlaceProfile,
    category: str,
    competitor_count: int,
) -> SuccessAnalysis:
    factors: list[SuccessFactor] = []
    seen_factors: set[str] = set()

    def add_factor(factor: str, factor_category: str, importance: str) -> None:
        if factor in seen_factors:
            return
        seen_factors.add(factor)
        factors.append(
            SuccessFactor(
                factor=factor,
                category=factor_category,
                importance=importance,
                actionable_tip=_FACTOR_TIP_MAP.get(
                    factor,
                    "벤치마크 매장의 강점을 기준으로 실행 가능한 운영 체크리스트를 만들어 적용하세요",
                ),
            )
        )

    for keyword in naver_profile.keywords:
        for token, (factor_category, factor) in _KEYWORD_FACTOR_MAP.items():
            if token in keyword:
                add_factor(factor, factor_category, "high")
                break

    if "만화" in category:
        add_factor("만화/콘텐츠 큐레이션이 핵심 경쟁력", "product", "high")
    if "보드게임" in category:
        add_factor("게임 다양성과 진행 도우미가 핵심", "service", "high")
    if "디저트" in category:
        add_factor("비주얼 디저트와 SNS 노출이 핵심", "product", "high")

    if competitor_count > 8:
        add_factor("경쟁 치열 — 차별화 포인트 1가지 이상 필수", "location", "high")

    if naver_profile.review_score > 0:
        if naver_profile.review_score >= 4.5:
            add_factor("높은 고객 만족도 — 같은 수준 유지 필수", "service", "high")
        elif naver_profile.review_score >= 4.0:
            add_factor("양호한 평점 — 서비스 품질 관리 중요", "service", "medium")
        else:
            add_factor("평점 개선 여지 있음 — 차별화 기회", "service", "medium")

    importance_order = {"high": 0, "medium": 1}
    factors = sorted(factors, key=lambda item: importance_order.get(item.importance, 2))[:5]

    top_factors = [item.factor for item in factors[:3]]
    factor_text = ", ".join(top_factors) if top_factors else "핵심 운영 요소"
    advice_text = (
        factors[0].actionable_tip
        if factors
        else "고객 리뷰와 경쟁 환경을 함께 반영해 운영 전략을 구체화하세요"
    )
    summary = f"캣툰 성수점의 핵심 성공 요인은 {factor_text} 입니다. {advice_text}"

    return SuccessAnalysis(factors=factors, summary=summary)


async def _search_naver_place(name: str) -> NaverPlaceProfile:
    """Search Naver Map for a place and return its profile data."""
    try:
        async with httpx.AsyncClient(
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Referer": "https://map.naver.com/",
            },
        ) as client:
            search_resp = await client.get(
                NAVER_SEARCH_URL,
                params={"query": name, "type": "all", "page": 1, "displayCount": 5},
            )
            if search_resp.status_code != 200:
                logger.warning("Naver search HTTP %s for %s", search_resp.status_code, name)
                return NaverPlaceProfile(name=name)

            search_data = search_resp.json()
            place_list = search_data.get("result", {}).get("place", {}).get("list", [])
            if not place_list:
                logger.info("No Naver Place results for: %s", name)
                return NaverPlaceProfile(name=name)

            place = place_list[0]
            place_id = str(place.get("id", ""))
            if not place_id:
                return NaverPlaceProfile(name=name)

            detail_resp = await client.get(
                f"{NAVER_PLACE_URL}/{place_id}",
                params={"lang": "ko"},
            )
            if search_resp.status_code != 200:
                logger.warning("Naver search HTTP %s for %s", search_resp.status_code, name)
                return NaverPlaceProfile(name=name)

            search_data = search_resp.json()
            place_list = search_data.get("result", {}).get("place", {}).get("list", [])
            if not place_list:
                logger.info("No Naver Place results for: %s", name)
                return NaverPlaceProfile(name=name)

            # Take the first result
            place = place_list[0]
            place_id = str(place.get("id", ""))
            if not place_id:
                return NaverPlaceProfile(name=name)

            # Step 2: Get place detail
            detail_resp = await client.get(
                f"{NAVER_PLACE_URL}/{place_id}",
                params={"lang": "ko"},
            )
            if detail_resp.status_code != 200:
                return NaverPlaceProfile(naver_id=place_id, name=name)

            d = detail_resp.json()
            return NaverPlaceProfile(
                naver_id=place_id,
                name=d.get("name", name),
                category=d.get("category", ""),
                review_count=int(d.get("reviewCount", 0) or 0),
                review_score=float(d.get("reviewScore", 0) or 0),
                blog_review_count=int(d.get("blogReviewCount", 0) or 0),
                visitor_review_count=int(d.get("visitorReviewCount", 0) or 0),
                keywords=d.get("keywords", []) or [],
                business_hours=d.get("businessHours", {}) or {},
            )
    except Exception as exc:
        logger.warning("Naver Place lookup failed for %s: %s", name, exc)
        return NaverPlaceProfile(name=name)


async def _search_kakao_competitors(
    x: float, y: float, industry_code: str, radius: int = 500
) -> list[NearbyCompetitor]:
    """Search Kakao for nearby competitors within radius."""
    if not KAKAO_REST_API_KEY:
        return []

    category_group_map: dict[str, str] = {
        "CS100010": "CE7",
        "CS100001": "FD6",
        "CS100002": "FD6",
        "CS100003": "FD6",
        "CS100004": "FD6",
        "CS100005": "FD6",
        "CS100006": "FD6",
        "CS100007": "FD6",
        "CS100008": "FD6",
        "CS100009": "FD6",
    }
    category_group = category_group_map.get(industry_code, "FD6")

    try:
        headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://dapi.kakao.com/v2/local/search/category.json",
                params={
                    "category_group_code": category_group,
                    "x": str(x),
                    "y": str(y),
                    "radius": radius,
                    "size": 15,
                    "sort": "distance",
                },
                headers=headers,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            documents = data.get("documents", [])
            results: list[NearbyCompetitor] = []
            for doc in documents:
                results.append(
                    NearbyCompetitor(
                        name=doc.get("place_name", ""),
                        category=doc.get("category_name", ""),
                        distance=int(doc.get("distance", 0) or 0),
                        address=doc.get("road_address_name", "") or doc.get("address_name", ""),
                    )
                )
            return results
    except Exception as exc:
        logger.warning("Kakao competitor search failed: %s", exc)
        return []


async def _validate_demand(
    sub_category: str,
    target_area: str,
    industry_code: str,
) -> DemandValidation:
    keyword = sub_category.strip()
    if " > " in keyword:
        keyword = keyword.split(" > ")[-1].strip()
    if not keyword:
        keyword = INDUSTRY_NAMES.get(industry_code, "카페")

    try:
        service = get_trend_service()
        trend_result = await service.get_search_trend(keywords=[keyword])
        results = trend_result.get("results", [])
        first_result = results[0] if isinstance(results, list) and results else {}
        trend_data_raw = first_result.get("data", []) if isinstance(first_result, dict) else []
        trend_data: list[dict[str, object]] = (
            trend_data_raw if isinstance(trend_data_raw, list) else []
        )
    except Exception as exc:
        logger.warning("Demand trend lookup failed for %s: %s", keyword, exc)
        return DemandValidation(
            search_trend_keyword=keyword,
            demand_summary="검색 트렌드 데이터를 불러오지 못해 수요 검증 결과를 제공할 수 없습니다.",
        )

    ratios = [_to_float(point.get("ratio", 0.0)) for point in trend_data]
    trend_avg_ratio = round(sum(ratios) / len(ratios), 1) if ratios else 0.0

    window = min(3, len(ratios))
    first_avg = (sum(ratios[:window]) / window) if window else 0.0
    last_avg = (sum(ratios[-window:]) / window) if window else 0.0
    if window == 0:
        trend_direction = "stable"
    elif last_avg > first_avg + 3:
        trend_direction = "rising"
    elif last_avg < first_avg - 3:
        trend_direction = "declining"
    else:
        trend_direction = "stable"

    same_category_count = 0
    if target_area.strip() and KAKAO_REST_API_KEY:
        try:
            headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    KAKAO_KEYWORD_URL,
                    params={"query": f"{target_area} {keyword}", "size": 15},
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    documents = data.get("documents", [])
                    same_category_count = len(documents) if isinstance(documents, list) else 0
        except Exception as exc:
            logger.warning("Demand supply lookup failed for %s %s: %s", target_area, keyword, exc)

    if trend_avg_ratio >= 60 and same_category_count <= 3:
        demand_verdict = "충분"
    elif trend_avg_ratio >= 40 or same_category_count <= 5:
        demand_verdict = "보통"
    else:
        demand_verdict = "부족"

    if target_area.strip():
        base_summary = (
            f'"{keyword}" 검색량이 최근 1년간 평균 {trend_avg_ratio:.1f}이며, '
            f"{target_area} 지역에 {keyword}는 {same_category_count}곳으로 파악됩니다."
        )
    else:
        base_summary = f'"{keyword}" 검색량이 최근 1년간 평균 {trend_avg_ratio:.1f}입니다.'

    if trend_direction == "declining":
        demand_summary = f"{base_summary} 검색량이 하락 추세이므로 신중한 검토가 필요합니다."
    elif demand_verdict == "충분":
        demand_summary = f"{base_summary} 수요 대비 공급이 부족해 진입 여건이 좋습니다."
    elif demand_verdict == "보통":
        demand_summary = f"{base_summary} 수요와 공급이 균형에 가까워 차별화 전략이 중요합니다."
    else:
        demand_summary = f"{base_summary} 공급이 상대적으로 많아 입지·콘셉트 차별화가 필요합니다."

    return DemandValidation(
        search_trend_keyword=keyword,
        search_trend_data=trend_data,
        trend_direction=trend_direction,
        trend_avg_ratio=trend_avg_ratio,
        same_category_count_nearby=same_category_count,
        demand_verdict=demand_verdict,
        demand_summary=demand_summary,
    )


@router.post("/analyze", response_model=BenchmarkAnalyzeResponse)
async def analyze_benchmark_store(
    req: BenchmarkAnalyzeRequest,
) -> BenchmarkAnalyzeResponse:
    """Analyze a benchmark store: Naver Place reviews + nearby competitors."""
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="매장 이름은 필수입니다")

    import asyncio

    naver_task = _search_naver_place(req.name)
    competitor_task = _search_kakao_competitors(req.x, req.y, req.industry_code)
    sub_cat = req.category.split(" > ")[-1] if " > " in req.category else ""
    demand_task = _validate_demand(sub_cat or "카페", req.target_district_name, req.industry_code)

    naver_profile, competitors, demand = await asyncio.gather(
        naver_task, competitor_task, demand_task
    )

    comp_count = len(competitors)
    success_analysis = _extract_success_factors(naver_profile, req.category, comp_count)
    if comp_count == 0:
        location_summary = "반경 500m 내 동종 업종 경쟁 매장이 없습니다."
    elif comp_count <= 3:
        location_summary = f"반경 500m 내 동종 업종 {comp_count}개 — 경쟁이 적은 편입니다."
    elif comp_count <= 8:
        location_summary = f"반경 500m 내 동종 업종 {comp_count}개 — 보통 수준의 경쟁입니다."
    else:
        location_summary = f"반경 500m 내 동종 업종 {comp_count}개 — 경쟁이 치열합니다."

    return BenchmarkAnalyzeResponse(
        store_name=req.name,
        store_category=req.category,
        naver_profile=naver_profile,
        nearby_competitors=competitors[:10],
        competitor_count=comp_count,
        location_summary=location_summary,
        demand=demand,
        success_analysis=success_analysis,
    )


# ─── Phase 3: Benchmark Similarity ──────────────────────────────────────


class BenchmarkSimilarityRequest(BaseModel):
    benchmark_name: str
    benchmark_x: float
    benchmark_y: float
    benchmark_category: str = ""
    district_code: str
    district_name: str
    industry_code: str = "CS100010"


class SimilarityResult(BaseModel):
    district_code: str
    district_name: str
    similarity_score: int  # 0-100
    match_factors: list[str]


@router.post("/similarity", response_model=SimilarityResult)
async def compute_similarity(
    req: BenchmarkSimilarityRequest,
) -> SimilarityResult:
    """Compare a TOP-3 district to the benchmark store's district characteristics."""

    benchmark_competitors = await _search_kakao_competitors(
        req.benchmark_x, req.benchmark_y, req.industry_code, radius=500
    )
    benchmark_density = len(benchmark_competitors)

    district_competitors: list[NearbyCompetitor] = []
    if KAKAO_REST_API_KEY:
        try:
            industry_name = INDUSTRY_NAMES.get(req.industry_code, "카페")
            headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    KAKAO_KEYWORD_URL,
                    params={
                        "query": f"{req.district_name} {industry_name}",
                        "size": 15,
                    },
                    headers=headers,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    documents = data.get("documents", [])
                    district_competitors = [
                        NearbyCompetitor(
                            name=doc.get("place_name", ""),
                            category=doc.get("category_name", ""),
                            distance=0,
                            address=doc.get("road_address_name", ""),
                        )
                        for doc in documents
                    ]
        except Exception as exc:
            logger.warning("District competitor search failed: %s", exc)

    district_density = len(district_competitors)

    factors: list[str] = []
    score = 50
    if benchmark_density > 0 and district_density > 0:
        density_ratio = min(benchmark_density, district_density) / max(
            benchmark_density, district_density
        )
        density_pts = int(density_ratio * 30)
        score += density_pts
        if density_ratio >= 0.7:
            factors.append("경쟁 밀도 유사")
        elif density_ratio >= 0.4:
            factors.append("경쟁 밀도 보통")
        else:
            factors.append("경쟁 밀도 차이 큼")
    else:
        factors.append("경쟁 데이터 부족")

    benchmark_cat = req.benchmark_category.lower()
    district_cat_names = [c.category.lower() for c in district_competitors[:10]]
    cat_matches = sum(
        1
        for c in district_cat_names
        if benchmark_cat and any(kw in c for kw in benchmark_cat.split(" > "))
    )
    if cat_matches >= 3:
        score += 20
        factors.append("업종 카테고리 일치")
    elif cat_matches >= 1:
        score += 10
        factors.append("업종 카테고리 부분 일치")

    score = max(0, min(100, score))

    return SimilarityResult(
        district_code=req.district_code,
        district_name=req.district_name,
        similarity_score=score,
        match_factors=factors,
    )


# ─── Phase 4: Benchmark Tips ────────────────────────────────────────────


class BenchmarkTipsRequest(BaseModel):
    benchmark_name: str
    benchmark_category: str = ""
    industry_code: str = "CS100010"
    sub_category: str = ""
    district_name: str = ""


class PhaseTip(BaseModel):
    phase_key: str  # design, funding, taxlabor, compliance, launch
    title: str
    description: str


class BenchmarkTipsResponse(BaseModel):
    benchmark_name: str
    tips: list[PhaseTip]


_CATEGORY_TIPS: dict[str, list[PhaseTip]] = {
    "카페": [
        PhaseTip(
            phase_key="design",
            title="벤치마크 카페의 인테리어 톤 참고",
            description="성공한 카페는 조명·좌석 배치·동선이 핵심입니다. 벤치마크 매장을 직접 방문해 사진을 찍어두세요.",
        ),
        PhaseTip(
            phase_key="funding",
            title="카페 특화 장비 예산 확인",
            description="에스프레소 머신·그라인더·제빙기 등 초기 장비 투자가 큽니다. 벤치마크 매장의 장비 수준을 확인하세요.",
        ),
        PhaseTip(
            phase_key="taxlabor",
            title="파트타임 바리스타 시급 기준",
            description="카페 업종은 파트타임 비율이 높습니다. 주휴수당 포함 시급을 미리 계산하세요.",
        ),
        PhaseTip(
            phase_key="compliance",
            title="식품제조가공업 신고 확인",
            description="카페에서 직접 디저트를 만들어 판매할 경우 식품제조가공업 신고가 필요할 수 있습니다.",
        ),
        PhaseTip(
            phase_key="launch",
            title="오픈 전 메뉴 테스트 필수",
            description="벤치마크 매장의 시그니처 메뉴를 분석하고, 차별화된 시그니처를 개발하세요.",
        ),
    ],
    "한식": [
        PhaseTip(
            phase_key="design",
            title="벤치마크 매장의 메뉴 구성 분석",
            description="한식은 메뉴 수가 수익에 직결됩니다. 벤치마크 매장의 메뉴 수와 가격대를 분석하세요.",
        ),
        PhaseTip(
            phase_key="funding",
            title="주방 설비 투자 비중 확인",
            description="한식은 화력·배기 시설 투자가 큽니다. 벤치마크 매장 규모에 맞는 주방 설비 예산을 책정하세요.",
        ),
        PhaseTip(
            phase_key="launch",
            title="단골 확보 전략 수립",
            description="한식은 재방문율이 핵심입니다. 오픈 1개월 내 단골 50명 확보를 목표로 이벤트를 기획하세요.",
        ),
    ],
    "베이커리": [
        PhaseTip(
            phase_key="design",
            title="생산 동선과 판매 동선 분리",
            description="벤치마크 베이커리의 주방-판매 동선을 참고하세요. 오픈 주방은 신뢰감을 높입니다.",
        ),
        PhaseTip(
            phase_key="funding",
            title="오븐·발효기 투자 계획",
            description="베이커리 장비는 고가입니다. 신품 vs 중고, 리스 vs 구매를 비교 검토하세요.",
        ),
        PhaseTip(
            phase_key="launch",
            title="시그니처 빵 3종 필수",
            description="벤치마크 매장의 인기 메뉴를 파악하고, 차별화된 시그니처 빵 3종을 개발하세요.",
        ),
    ],
    "치킨": [
        PhaseTip(
            phase_key="design",
            title="배달 vs 홀 비중 결정",
            description="벤치마크 매장의 배달 비중을 파악하세요. 배달 중심이면 홀 크기를 줄이고 주방을 넓힐 수 있습니다.",
        ),
        PhaseTip(
            phase_key="funding",
            title="배달앱 수수료 감안한 가격 설정",
            description="배달앱 수수료 15-25%를 감안한 메뉴 가격을 설정하세요.",
        ),
        PhaseTip(
            phase_key="launch",
            title="오픈 이벤트로 배달앱 랭킹 확보",
            description="오픈 초기 2주간 공격적 할인으로 배달앱 노출 순위를 올리세요.",
        ),
    ],
}

_DEFAULT_TIPS: list[PhaseTip] = [
    PhaseTip(
        phase_key="design",
        title="벤치마크 매장 직접 방문 권장",
        description="온라인 리뷰만으로는 한계가 있습니다. 직접 방문하여 고객 동선, 피크 시간대, 서비스 방식을 관찰하세요.",
    ),
    PhaseTip(
        phase_key="funding",
        title="벤치마크 매장 규모 대비 예산 조정",
        description="벤치마크 매장의 평수·인테리어 수준을 기준으로 현실적인 예산을 역산하세요.",
    ),
    PhaseTip(
        phase_key="launch",
        title="벤치마크와의 차별점 명확히",
        description="벤치마크 매장을 그대로 따라하지 말고, 한 가지 이상 뚜렷한 차별점을 만드세요.",
    ),
]

_SUB_CATEGORY_TIPS: dict[str, list[PhaseTip]] = {
    "만화카페": [
        PhaseTip(
            phase_key="design",
            title="만화 장서 구매 계획 필수",
            description="만화카페의 핵심 자산은 장서입니다. 인기 만화 500~1000권 이상 초기 구비가 필요하며, 월 10~20만원의 신간 구매 예산을 별도로 책정하세요.",
        ),
        PhaseTip(
            phase_key="design",
            title="좌석 배치: 1인석 + 소파석 혼합",
            description="만화카페 고객은 혼자 오는 비율이 높습니다. 1인 독서석 60% + 소파/커플석 40% 비율을 권장합니다.",
        ),
        PhaseTip(
            phase_key="funding",
            title="시간제 과금 모델 검토",
            description="음료만 판매 vs 시간제 이용료 + 음료 포함 모델을 비교하세요. 캣툰 같은 만화카페는 시간제 모델이 일반적입니다.",
        ),
        PhaseTip(
            phase_key="compliance",
            title="청소년 이용 가능 여부 확인",
            description="만화카페는 청소년보호법 대상이 될 수 있습니다. 영업시간 제한과 성인 만화 구역 분리가 필요한지 확인하세요.",
        ),
        PhaseTip(
            phase_key="launch",
            title="만화 카테고리 큐레이션",
            description="장르별(액션/로맨스/일상/추리) 코너를 만들고 '이달의 추천' 코너를 운영하면 재방문율이 높아집니다.",
        ),
    ],
    "보드게임카페": [
        PhaseTip(
            phase_key="design",
            title="보드게임 100종 이상 구비",
            description="인기 보드게임 100~200종을 초기 구비하세요. 월 5~10만원의 신규 게임 구매 예산을 책정하세요.",
        ),
        PhaseTip(
            phase_key="funding",
            title="테이블당 수익 모델 설계",
            description="시간제 이용료 + 음료 주문이 일반적입니다. 테이블당 4인 기준 시간당 수익을 계산하세요.",
        ),
        PhaseTip(
            phase_key="launch",
            title="게임 마스터 채용 고려",
            description="게임 룰 설명이 가능한 직원이 있으면 고객 만족도가 크게 올라갑니다.",
        ),
    ],
    "디저트카페": [
        PhaseTip(
            phase_key="design",
            title="쇼케이스 배치가 핵심",
            description="디저트 쇼케이스는 입구에서 바로 보이는 위치에 배치하세요. 시각적 임팩트가 매출에 직결됩니다.",
        ),
        PhaseTip(
            phase_key="compliance",
            title="식품제조가공업 필수 신고",
            description="디저트를 직접 만들어 판매하면 식품제조가공업 신고가 반드시 필요합니다.",
        ),
        PhaseTip(
            phase_key="launch",
            title="인스타그래머블 메뉴 3종 필수",
            description="SNS 공유되는 비주얼 디저트 메뉴를 최소 3종 개발하세요.",
        ),
    ],
}


@router.post("/tips", response_model=BenchmarkTipsResponse)
async def get_benchmark_tips(
    req: BenchmarkTipsRequest,
) -> BenchmarkTipsResponse:
    """Return rule-based benchmark tips per execution phase."""
    sub_category = req.sub_category.strip()
    if not sub_category:
        sub_category = (
            req.benchmark_category.split(" > ")[-1].strip() if req.benchmark_category else ""
        )

    industry_name = INDUSTRY_NAMES.get(req.industry_code, "")
    industry_tips = _CATEGORY_TIPS.get(industry_name, _DEFAULT_TIPS)
    sub_category_tips = _SUB_CATEGORY_TIPS.get(sub_category, [])
    tips = [*sub_category_tips, *industry_tips]

    personalized: list[PhaseTip] = []
    for tip in tips:
        title = tip.title.replace("벤치마크 매장", f"'{req.benchmark_name}'")
        desc = tip.description.replace("벤치마크 매장", f"'{req.benchmark_name}'")
        personalized.append(
            PhaseTip(
                phase_key=tip.phase_key,
                title=title,
                description=desc,
            )
        )

    return BenchmarkTipsResponse(
        benchmark_name=req.benchmark_name,
        tips=personalized,
    )
