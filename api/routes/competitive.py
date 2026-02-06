"""경쟁/차별화 분석 + 메뉴 원가계산 API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.services.competitive_analysis_service import (
    CompetitiveAnalysisService,
    get_competitive_analysis_service,
)

router = APIRouter(prefix="/competitive")


class CafeTypeBreakdownItem(BaseModel):
    type: str
    count: int
    ratio: float
    examples: list[str]


class MarketGapItem(BaseModel):
    gap_type: str
    description: str
    opportunity_score: float


class DifferentiationStrategyItem(BaseModel):
    strategy: str
    reason: str
    priority: str


class TopCompetitorItem(BaseModel):
    name: str
    category: str
    address: str
    place_url: str


class CompetitiveAnalysisResponse(BaseModel):
    total_nearby_cafes: int
    cafe_types: list[CafeTypeBreakdownItem]
    market_gaps: list[MarketGapItem]
    strategies: list[DifferentiationStrategyItem]
    top_competitors: list[TopCompetitorItem]


@router.get("/analyze", response_model=CompetitiveAnalysisResponse)
async def analyze_competition(
    query: Annotated[str, Query(description="검색 키워드(예: '강남역', '홍대입구역')")],
    x: Annotated[float | None, Query(description="경도(lng)")] = None,
    y: Annotated[float | None, Query(description="위도(lat)")] = None,
) -> CompetitiveAnalysisResponse:
    service = get_competitive_analysis_service()
    try:
        result = await service.analyze_competition(query=query, x=x, y=y)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"경쟁 분석 실패: {e}")

    return CompetitiveAnalysisResponse(
        total_nearby_cafes=int(result.get("total_nearby_cafes", 0)),
        cafe_types=[CafeTypeBreakdownItem(**i) for i in result.get("cafe_types", [])],
        market_gaps=[MarketGapItem(**i) for i in result.get("market_gaps", [])],
        strategies=[DifferentiationStrategyItem(**i) for i in result.get("strategies", [])],
        top_competitors=[TopCompetitorItem(**i) for i in result.get("top_competitors", [])],
    )


class MenuCostItemResponse(BaseModel):
    menu: str
    selling_price: int
    cost: int
    margin: int
    margin_rate: float
    category: str
    ingredients: dict[str, dict[str, object]]


class CostSimulationResponse(BaseModel):
    menu_costs: list[MenuCostItemResponse]
    avg_margin_rate: float
    raw_material_prices: dict[str, dict[str, object]]
    daily_sales_scenario: dict[str, object]


@router.get("/menu-costs", response_model=CostSimulationResponse)
async def get_menu_costs() -> CostSimulationResponse:
    try:
        result = CompetitiveAnalysisService.get_menu_costs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"원가 데이터 생성 실패: {e}")

    return CostSimulationResponse(
        menu_costs=[MenuCostItemResponse(**i) for i in result.get("menu_costs", [])],
        avg_margin_rate=float(result.get("avg_margin_rate", 0.0)),
        raw_material_prices=dict(result.get("raw_material_prices", {})),
        daily_sales_scenario=dict(result.get("daily_sales_scenario", {})),
    )


class CustomMenuCostRequest(BaseModel):
    selling_price: int
    ingredients: dict[str, int]


@router.post("/menu-costs/custom", response_model=MenuCostItemResponse)
async def calculate_custom_menu_cost(payload: CustomMenuCostRequest) -> MenuCostItemResponse:
    if payload.selling_price < 0:
        raise HTTPException(status_code=422, detail="selling_price must be >= 0")
    if any(v < 0 for v in payload.ingredients.values()):
        raise HTTPException(status_code=422, detail="ingredient costs must be >= 0")
    try:
        result = CompetitiveAnalysisService.calculate_custom_menu_cost(
            selling_price=payload.selling_price,
            ingredients=payload.ingredients,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"커스텀 원가 계산 실패: {e}")

    return MenuCostItemResponse(**result)
