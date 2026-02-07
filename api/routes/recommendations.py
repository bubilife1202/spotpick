from __future__ import annotations

import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.services.data_service import get_data_service
from api.services.geocoding_service import get_geocoding_service

router = APIRouter()


class RecommendationRequestBody(BaseModel):
    category: str = Field(default="coffee", description="업종 카테고리")
    budget_min: int = Field(..., ge=0, description="최소 예산 (월 임대료)")
    budget_max: int = Field(..., description="최대 예산 (월 임대료)")
    preferred_district: Optional[str] = Field(None, description="선호 지역구 (예: 강남, 마포)")
    preferred_area_type: Optional[str] = Field(
        None, description="선호 상권 유형 (골목상권, 발달상권, 전통시장, 관광특구)"
    )
    min_survival_rate: float = Field(0.0, ge=0.0, le=1.0, description="최소 생존율 (0~1)")
    top_n: int = Field(5, ge=1, le=10, description="추천 개수 (베타에서는 최대 10)")
    has_takeout: Optional[bool] = Field(
        default=None, description="(호환성) 테이크아웃 여부. 현재는 추천 로직에 직접 반영하지 않습니다."
    )
    industry_code: str = Field(default="CS100010", description="업종 코드")


class AreaStats(BaseModel):
    floating_population: int
    competitor_count: int
    survival_rate_1y: float
    survival_rate_2y: float
    survival_rate_3y: float
    weekday_sales_ratio: float = 0.0
    weekend_sales_ratio: float = 0.0
    franchise_ratio: float = 0.0


class NearbyStore(BaseModel):
    name: str
    score: float


class TimeAnalysis(BaseModel):
    peak_time: str
    time_00_06: float
    time_06_11: float
    time_11_14: float
    time_14_17: float
    time_17_21: float
    time_21_24: float


class DayAnalysis(BaseModel):
    peak_day: str
    weekday_ratio: float
    weekend_ratio: float
    mon: float
    tue: float
    wed: float
    thu: float
    fri: float
    sat: float
    sun: float


class CustomerAnalysis(BaseModel):
    main_age_group: str
    male_ratio: float
    female_ratio: float
    age_10: float
    age_20: float
    age_30: float
    age_40: float
    age_50: float
    age_60: float


class Competition(BaseModel):
    store_count: int
    new_stores: int
    closed_stores: int
    franchise_stores: int
    franchise_ratio: float


class LocationResponse(BaseModel):
    rank: int
    lat: float
    lng: float
    address: str
    area_name: str
    area_type: str
    success_probability: float
    confidence: float
    estimated_monthly_rent: int
    estimated_monthly_sales: int = 0
    survival_rate_2y: Optional[float] = None
    risk_factors: list[str]
    recommendations: list[str]
    key_success_factors: list[str]
    nearby_successful_stores: list[NearbyStore]
    area_stats: AreaStats
    time_analysis: Optional[TimeAnalysis] = None
    day_analysis: Optional[DayAnalysis] = None
    customer_analysis: Optional[CustomerAnalysis] = None
    competition: Optional[Competition] = None


class RecommendationResponse(BaseModel):
    total_candidates: int
    recommendations: list[LocationResponse]


def _build_geocoding_queries(district_name: str, address: str) -> list[str]:
    # Keep in sync with chat enrichment heuristics (best-effort).
    district_name = (district_name or "").strip()
    address = (address or "").strip()

    queries: list[str] = []

    def add(q: str) -> None:
        q = (q or "").strip()
        if q and q not in queries:
            queries.append(q)

    if address:
        add(address)
    if district_name:
        add(f"서울 {district_name}")

    base = re.sub(r"\(.*?\)", "", district_name).strip()
    add(f"서울 {base}")
    add(base)

    no_num = re.sub(r"\s+\d+번$", "", base).strip()
    add(f"서울 {no_num}")
    add(no_num)

    m_station = re.search(r"(.+?역)", no_num)
    if m_station:
        station = m_station.group(1).strip()
        add(f"서울 {station}")
        add(station)

    seoul_prefixes = [
        "강남",
        "서초",
        "마포",
        "홍대",
        "이태원",
        "성수",
        "용산",
        "종로",
        "강동",
        "송파",
        "영등포",
        "구로",
        "관악",
        "동대문",
        "성북",
        "노원",
        "강북",
        "은평",
        "서대문",
        "양천",
        "강서",
        "금천",
        "성동",
        "광진",
        "중랑",
        "도봉",
        "중구",
    ]
    for p in seoul_prefixes:
        if no_num.startswith(p) and len(no_num) > len(p):
            rest = no_num[len(p) :].strip()
            if rest and not rest.startswith("구"):
                add(f"서울 {p} {rest}")
                add(f"{p} {rest}")
            break

    m_inner = re.search(r"\((.*?)\)", district_name)
    if m_inner:
        inner = m_inner.group(1).replace("_", " ")
        for part in inner.split(","):
            token = part.strip()
            if not token:
                continue
            token = re.sub(r"\s*\d+번", "", token).strip()
            if token:
                add(f"서울 {token}")
                add(token)

    # Stable fallback
    add("서울특별시")
    return queries


@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(body: RecommendationRequestBody):
    """
    예산과 조건에 맞는 최적의 창업 위치를 추천합니다.

    - **budget_min/max**: 월 임대료 예산 범위 (원)
    - **preferred_district**: 선호 지역 (예: "강남", "마포", "홍대")
    - **preferred_area_type**: 상권 유형 (골목상권, 발달상권, 전통시장, 관광특구)
    - **min_survival_rate**: 최소 생존율 필터 (0.5 = 50% 이상)
    """
    service = get_data_service(industry_code=body.industry_code)

    preferred = (body.preferred_district or "").strip() or None
    # UI 호환: "강남구" -> "강남" (단, "중구" 처럼 2글자+구는 제거하지 않음)
    if preferred and preferred.endswith("구") and len(preferred) >= 3:
        preferred = preferred[:-1]

    # 베타: 지도 좌표를 함께 제공하기 위해 top_n을 제한 (지오코딩 요청 수/지연 관리)
    top_n = max(1, min(int(body.top_n or 5), 10))

    results = service.get_recommendations(
        budget_min=body.budget_min,
        budget_max=body.budget_max,
        category=body.category,
        preferred_district=preferred,
        preferred_area_type=body.preferred_area_type,
        min_survival_rate=body.min_survival_rate,
        top_n=top_n,
    )

    geocoder = get_geocoding_service()

    recommendations: list[LocationResponse] = []
    for r in results:
        district_name = str(r.get("district_name") or "").strip()
        address = str(r.get("address") or f"서울특별시 {district_name}").strip()

        coords = None
        for q in _build_geocoding_queries(district_name=district_name, address=address):
            coords = await geocoder.geocode(q)
            if coords is not None:
                break

        lat = coords.lat if coords is not None else 37.5665
        lng = coords.lng if coords is not None else 126.9780

        store_count = int((r.get("competition") or {}).get("store_count") or 0)
        survival_2y = min(float(r.get("survival_rate_2y") or 0.0), 1.0)
        area_stats = {
            "floating_population": 0,
            "competitor_count": store_count,
            "survival_rate_1y": survival_2y,
            "survival_rate_2y": survival_2y,
            "survival_rate_3y": max(0.0, survival_2y - 0.05),
            "weekday_sales_ratio": float((r.get("day_analysis") or {}).get("weekday_ratio") or 0.0),
            "weekend_sales_ratio": float((r.get("day_analysis") or {}).get("weekend_ratio") or 0.0),
            "franchise_ratio": float((r.get("competition") or {}).get("franchise_ratio") or 0.0),
        }

        recommendations.append(
            LocationResponse(
                rank=int(r["rank"]),
                lat=lat,
                lng=lng,
                address=address,
                area_name=district_name,
                area_type=str(r.get("district_type") or ""),
                success_probability=float(r.get("success_probability") or 0.0),
                confidence=0.8,
                estimated_monthly_rent=int(r.get("estimated_monthly_rent") or 0),
                estimated_monthly_sales=int(r.get("estimated_monthly_sales") or 0),
                survival_rate_2y=survival_2y,
                risk_factors=[str(x) for x in (r.get("risk_factors") or [])],
                recommendations=[str(x) for x in (r.get("recommendations") or [])],
                key_success_factors=[str(x) for x in (r.get("key_success_factors") or [])],
                nearby_successful_stores=[],
                area_stats=AreaStats(**area_stats),
                time_analysis=TimeAnalysis(**r["time_analysis"]) if r.get("time_analysis") else None,
                day_analysis=DayAnalysis(**r["day_analysis"]) if r.get("day_analysis") else None,
                customer_analysis=CustomerAnalysis(**r["customer_analysis"])
                if r.get("customer_analysis")
                else None,
                competition=Competition(**r["competition"]) if r.get("competition") else None,
            )
        )

    return RecommendationResponse(
        total_candidates=len(service.districts),
        recommendations=recommendations,
    )


@router.get("/recommendations/analyze")
async def analyze_location(
    lat: float = Query(..., description="위도"),
    lng: float = Query(..., description="경도"),
    category: str = Query("coffee", description="업종"),
):
    """특정 좌표의 창업 적합도를 분석합니다."""
    raise HTTPException(
        status_code=501,
        detail="현재 베타 데이터(상권 단위 집계)에서는 좌표 기반 분석을 제공하지 않습니다.",
    )


@router.get("/recommendations/quick")
async def quick_recommendation(
    budget: int = Query(..., description="월 예산 (임대료)"),
    district: Optional[str] = Query(None, description="선호 지역구"),
    area_type: Optional[str] = Query(None, description="상권 유형"),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """
    간단한 조건으로 빠르게 추천받습니다.

    예: /recommendations/quick?budget=3000000&district=강남
    """
    service = get_data_service(industry_code=industry_code)

    budget_min = int(budget * 0.7)
    budget_max = int(budget * 1.3)

    results = service.get_recommendations(
        budget_min=budget_min,
        budget_max=budget_max,
        preferred_district=district,
        preferred_area_type=area_type,
        top_n=5,
    )

    if not results:
        return {
            "message": "조건에 맞는 추천 위치가 없습니다. 예산을 조정해보세요.",
            "suggestions": [
                f"예산 범위: {budget_min:,}원 ~ {budget_max:,}원",
                "다른 지역을 고려해보세요",
            ],
        }

    top = results[0]
    return {
        "recommendation": {
            "area_name": top["district_name"],
            "area_type": top["district_type"],
            "district": district or "",
            "success_probability": f"{top['success_probability'] * 100:.0f}%",
            "monthly_rent": f"{top['estimated_monthly_rent']:,}원",
            "monthly_sales": f"{top.get('estimated_monthly_sales', 0):,}원",
            "survival_rate": f"{top.get('survival_rate_2y', 0) * 100:.0f}%",
            "key_factors": top.get("key_success_factors", [])[:3],
            "main_risk": top["risk_factors"][0] if top.get("risk_factors") else "특별한 리스크 없음",
            "tip": top["recommendations"][0] if top.get("recommendations") else None,
        },
        "alternatives": [
            {
                "area_name": r["district_name"],
                "area_type": r["district_type"],
                "success_probability": f"{r['success_probability'] * 100:.0f}%",
                "monthly_rent": f"{r['estimated_monthly_rent']:,}원",
            }
            for r in results[1:4]
        ],
    }


@router.get("/recommendations/summary")
async def get_summary(
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """전체 데이터 요약 통계를 반환합니다."""
    service = get_data_service(industry_code=industry_code)
    return service.get_summary()
