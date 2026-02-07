"""
시뮬레이션 API — 매출 예측 · 투자비 산출 · 손익분기점 분석
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.services.simulation_service import get_simulation_service

router = APIRouter(prefix="/simulation")


class SimulationRequest(BaseModel):
    district_code: str = Field(..., description="상권 코드")
    area_pyeong: int = Field(default=10, ge=5, le=100, description="매장 면적(평)")
    interior_grade: str = Field(
        default="mid",
        pattern="^(basic|mid|premium)$",
        description="인테리어 등급: basic / mid / premium",
    )
    industry_code: str = Field(default="CS100010", description="업종 코드")


class RevenueResponse(BaseModel):
    monthly_sales_per_store: int
    monthly_transactions_per_store: int
    avg_ticket: int
    pessimistic: int
    optimistic: int
    daily_sales: int
    peak_time_sales: int
    peak_time: str
    peak_day_sales: int
    peak_day: str


class StartupCostResponse(BaseModel):
    deposit: int
    interior: int
    equipment_min: int
    equipment_max: int
    initial_inventory_min: int
    initial_inventory_max: int
    permits_misc_min: int
    permits_misc_max: int
    total_min: int
    total_max: int
    interior_grade: str
    area_pyeong: int


class OperatingCostResponse(BaseModel):
    rent: int
    cogs: int
    labor: int
    utilities: int
    other: int
    total: int


class BreakEvenResponse(BaseModel):
    monthly_revenue: int
    monthly_operating_cost: int
    monthly_net_profit: int
    net_profit_margin: float
    initial_investment_min: int
    initial_investment_max: int
    break_even_months_min: int
    break_even_months_max: int
    daily_break_even_sales: int


class CompetitionResponse(BaseModel):
    store_count: int
    new_stores: int
    closed_stores: int
    franchise_stores: int
    franchise_ratio: float
    survival_rate: float


class SimulationResponse(BaseModel):
    district_name: str
    district_type: str
    district_code: str
    revenue: RevenueResponse
    startup_cost: StartupCostResponse
    operating_cost: OperatingCostResponse
    break_even: BreakEvenResponse
    competition: CompetitionResponse
    risk_summary: list[str]


@router.post("/simulate", response_model=SimulationResponse)
async def simulate(request: SimulationRequest) -> SimulationResponse:
    """
    상권 기반 창업 시뮬레이션

    매출 예측 · 초기 투자비용 · 운영비 · 손익분기점을 종합 산출합니다.
    """
    service = get_simulation_service(industry_code=request.industry_code)
    result = service.simulate(
        district_code=request.district_code,
        area_pyeong=request.area_pyeong,
        interior_grade=request.interior_grade,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"상권 코드 {request.district_code}를 찾을 수 없습니다",
        )

    return SimulationResponse(
        district_name=result["district_name"],
        district_type=result["district_type"],
        district_code=result["district_code"],
        revenue=RevenueResponse(**result["revenue"]),
        startup_cost=StartupCostResponse(**result["startup_cost"]),
        operating_cost=OperatingCostResponse(**result["operating_cost"]),
        break_even=BreakEvenResponse(**result["break_even"]),
        competition=CompetitionResponse(**result["competition"]),
        risk_summary=result["risk_summary"],
    )


@router.get("/simulate/{district_code}", response_model=SimulationResponse)
async def simulate_by_code(
    district_code: str,
    area_pyeong: int = 10,
    interior_grade: str = "mid",
    industry_code: str = "CS100010",
) -> SimulationResponse:
    """GET 방식 시뮬레이션 (간편 호출용)"""
    request = SimulationRequest(
        district_code=district_code,
        area_pyeong=area_pyeong,
        interior_grade=interior_grade,
        industry_code=industry_code,
    )
    return await simulate(request)
