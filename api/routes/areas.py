from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel
from typing import Optional

from api.services.data_service import get_data_service

router = APIRouter()


class AreaStatsResponse(BaseModel):
    id: str
    name: str
    type: str
    district: str
    lat: float
    lng: float
    floating_population: int
    avg_rent_price: int
    coffee_shop_count: int
    avg_success_score: float
    survival_rate_1y: float
    survival_rate_3y: float


class AreaListResponse(BaseModel):
    total: int
    items: list[AreaStatsResponse]


@router.get("/areas", response_model=AreaListResponse)
async def list_areas(
    district: Optional[str] = Query(None, description="지역구 필터"),
    sort_by: str = Query("avg_success_score", description="정렬 기준"),
    order: str = Query("desc", regex="^(asc|desc)$"),
):
    service = get_data_service()

    areas = service.get_areas(
        district=district,
        sort_by=sort_by,
        ascending=(order == "asc"),
    )

    return AreaListResponse(
        total=len(areas),
        items=[
            AreaStatsResponse(
                id=a["id"],
                name=a["name"],
                type=a["type"],
                district=a["district"],
                lat=a["lat"],
                lng=a["lng"],
                floating_population=a["floating_population"],
                avg_rent_price=a["avg_rent_price"],
                coffee_shop_count=a["coffee_shop_count"],
                avg_success_score=a["avg_success_score"],
                survival_rate_1y=a["survival_rate_1y"],
                survival_rate_3y=a["survival_rate_3y"],
            )
            for a in areas
        ],
    )


@router.get("/areas/compare")
async def compare_areas(
    area_names: str = Query(..., description="비교할 지역명 (쉼표 구분)"),
):
    service = get_data_service()
    names = [n.strip() for n in area_names.split(",")]

    results = []
    for name in names:
        area = service.get_area_by_name(name)
        if area:
            results.append(
                {
                    "name": area["name"],
                    "district": area["district"],
                    "type": area["type"],
                    "floating_population": area["floating_population"],
                    "avg_rent_price": area["avg_rent_price"],
                    "competitor_count": area["coffee_shop_count"],
                    "survival_rate_3y": area["survival_rate_3y"],
                    "avg_success_score": area["avg_success_score"],
                }
            )

    if not results:
        raise HTTPException(status_code=404, detail="No matching areas found")

    best_survival = max(results, key=lambda x: x["survival_rate_3y"])
    best_rent = min(results, key=lambda x: x["avg_rent_price"])
    best_population = max(results, key=lambda x: x["floating_population"])

    return {
        "areas": results,
        "analysis": {
            "best_survival_rate": best_survival["name"],
            "lowest_rent": best_rent["name"],
            "highest_traffic": best_population["name"],
            "recommendation": _recommend_best(results),
        },
    }


def _recommend_best(areas: list[dict]) -> str:
    def score(a):
        rent_score = 1 - (a["avg_rent_price"] / 6000000)
        survival_score = a["survival_rate_3y"]
        pop_score = min(a["floating_population"] / 100000, 1)
        return rent_score * 0.3 + survival_score * 0.4 + pop_score * 0.3

    best = max(areas, key=score)
    return f"{best['name']} - 생존율과 임대료 대비 유동인구 균형이 가장 좋습니다"


@router.get("/areas/{area_id}")
async def get_area(area_id: str):
    service = get_data_service()
    area = service.get_area(area_id)

    if not area:
        raise HTTPException(status_code=404, detail="Area not found")

    stores, _ = service.get_stores(include_closed=False, page_size=1000)
    area_stores = [s for s in stores if s["commercial_area"] == area["name"]]

    return {
        **area,
        "stores_summary": {
            "total": len(area_stores),
            "avg_score": round(
                sum(s["success_metrics"]["total_score"] for s in area_stores) / len(area_stores), 3
            )
            if area_stores
            else 0,
            "top_stores": [
                {"name": s["name"], "score": s["success_metrics"]["total_score"]}
                for s in sorted(
                    area_stores, key=lambda x: x["success_metrics"]["total_score"], reverse=True
                )[:5]
            ],
        },
    }


@router.get("/districts")
async def list_districts():
    service = get_data_service()
    return {
        "districts": service.district_summary,
    }
