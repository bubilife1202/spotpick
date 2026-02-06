from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.services.data_service import get_data_service

router = APIRouter()


class SuccessMetrics(BaseModel):
    survival_score: float
    review_score: float
    growth_score: float
    stability_score: float
    total_score: float


class StoreResponse(BaseModel):
    id: str
    name: str
    category: str
    address: str
    lat: float
    lng: float
    district: str
    commercial_area: str
    review_count: int
    avg_review_score: float
    survival_months: int
    is_closed: bool
    estimated_monthly_rent: int
    success_metrics: SuccessMetrics


class StoreListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[StoreResponse]


@router.get("/stores", response_model=StoreListResponse)
async def list_stores(
    district: Optional[str] = Query(None, description="지역구 필터"),
    min_score: Optional[float] = Query(None, ge=0, le=1, description="최소 성공 점수"),
    min_survival_months: Optional[int] = Query(None, ge=0, description="최소 생존 개월수"),
    include_closed: bool = Query(False, description="폐업 매장 포함"),
    lat: Optional[float] = Query(None, description="중심 위도"),
    lng: Optional[float] = Query(None, description="중심 경도"),
    radius_km: float = Query(1.0, ge=0.1, le=10, description="검색 반경 (km)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    service = get_data_service()

    stores, total = service.get_stores(
        district=district,
        min_score=min_score,
        min_survival_months=min_survival_months,
        include_closed=include_closed,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        page=page,
        page_size=page_size,
    )

    return StoreListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            StoreResponse(
                id=s["id"],
                name=s["name"],
                category=s["category_small"],
                address=s["address"],
                lat=s["lat"],
                lng=s["lng"],
                district=s["district"],
                commercial_area=s["commercial_area"],
                review_count=s["review_count"],
                avg_review_score=s["avg_review_score"],
                survival_months=s["survival_months"],
                is_closed=s["is_closed"],
                estimated_monthly_rent=s["estimated_monthly_rent"],
                success_metrics=SuccessMetrics(**s["success_metrics"]),
            )
            for s in stores
        ],
    )


@router.get("/stores/{store_id}", response_model=StoreResponse)
async def get_store(store_id: str):
    service = get_data_service()
    store = service.get_store(store_id)

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    return StoreResponse(
        id=store["id"],
        name=store["name"],
        category=store["category_small"],
        address=store["address"],
        lat=store["lat"],
        lng=store["lng"],
        district=store["district"],
        commercial_area=store["commercial_area"],
        review_count=store["review_count"],
        avg_review_score=store["avg_review_score"],
        survival_months=store["survival_months"],
        is_closed=store["is_closed"],
        estimated_monthly_rent=store["estimated_monthly_rent"],
        success_metrics=SuccessMetrics(**store["success_metrics"]),
    )


@router.get("/stores/{store_id}/details")
async def get_store_details(store_id: str):
    service = get_data_service()
    store = service.get_store(store_id)

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    area = service.get_area_by_name(store["commercial_area"])

    return {
        "store": store,
        "area_context": area,
        "success_analysis": {
            "score_breakdown": store["success_metrics"],
            "percentile": _calculate_percentile(service, store),
            "comparison": _compare_to_area_average(service, store),
        },
    }


def _calculate_percentile(service, store: dict) -> int:
    all_scores = [s["success_metrics"]["total_score"] for s in service.stores if not s["is_closed"]]
    store_score = store["success_metrics"]["total_score"]
    below = sum(1 for s in all_scores if s < store_score)
    return int((below / len(all_scores)) * 100)


def _compare_to_area_average(service, store: dict) -> dict:
    area_stores = [
        s
        for s in service.stores
        if s["commercial_area"] == store["commercial_area"] and not s["is_closed"]
    ]

    if not area_stores:
        return {"message": "비교 데이터 없음"}

    avg_score = sum(s["success_metrics"]["total_score"] for s in area_stores) / len(area_stores)
    avg_review = sum(s["avg_review_score"] for s in area_stores) / len(area_stores)
    avg_survival = sum(s["survival_months"] for s in area_stores) / len(area_stores)

    return {
        "area_name": store["commercial_area"],
        "store_count_in_area": len(area_stores),
        "your_score": store["success_metrics"]["total_score"],
        "area_avg_score": round(avg_score, 3),
        "score_diff": round(store["success_metrics"]["total_score"] - avg_score, 3),
        "your_review_score": store["avg_review_score"],
        "area_avg_review": round(avg_review, 1),
        "your_survival_months": store["survival_months"],
        "area_avg_survival": round(avg_survival, 1),
    }
