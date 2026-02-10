"""Startup blueprint API endpoints."""

from __future__ import annotations

from importlib import import_module
from typing import Awaitable, Callable, Protocol, cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/blueprint")


class _BlueprintServiceProto(Protocol):
    def generate(
        self,
        district_code: str,
        budget_man: int,
        experience_level: str | None = None,
        employee_count: str | None = None,
        area_pyeong: int = 10,
    ) -> Awaitable[object]: ...


def _get_blueprint_service(industry_code: str) -> _BlueprintServiceProto:
    module = import_module("api.services.blueprint_service")
    factory = getattr(module, "get_blueprint_service", None)
    if factory is None or not callable(factory):
        raise RuntimeError("blueprint service factory not available")
    return cast(_BlueprintServiceProto, factory(industry_code))


def _as_str(value: object, default: str = "") -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


class BlueprintResponse(BaseModel):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    concept_title: str
    recommended_business_type: str
    operation_model: dict[str, object]
    menu_strategy: dict[str, object]
    pricing_strategy: dict[str, object]
    launch_plan: list[dict[str, object]]
    financial_targets: dict[str, object]
    advisor_snapshots: dict[str, object]


@router.get("/generate", response_model=BlueprintResponse)
async def generate_blueprint(
    district_code: str = Query(..., description="상권 코드 또는 상권명"),
    industry_code: str = Query("CS100010", description="업종 코드"),
    budget_man: int = Query(5000, ge=500, le=100000, description="총 예산(만원)"),
    experience_level: str | None = Query(
        default=None, description="beginner | experienced | expert"
    ),
    employee_count: str | None = Query(default=None, description="solo | 1-2 | 3+"),
    area_pyeong: int = Query(10, ge=5, le=100, description="면적(평)"),
) -> BlueprintResponse:
    service = _get_blueprint_service(industry_code)

    result_obj = await service.generate(
        district_code=district_code,
        budget_man=budget_man,
        experience_level=experience_level,
        employee_count=employee_count,
        area_pyeong=area_pyeong,
    )
    if result_obj is None:
        raise HTTPException(status_code=404, detail=f"상권을 찾을 수 없습니다: {district_code}")
    if not isinstance(result_obj, dict):
        raise HTTPException(status_code=500, detail="창업 설계 결과 형식 오류")

    data = cast(dict[str, object], result_obj)
    return BlueprintResponse(
        district_code=_as_str(data.get("district_code", district_code), district_code),
        district_name=_as_str(data.get("district_name", "")),
        industry_code=_as_str(data.get("industry_code", industry_code), industry_code),
        industry_name=_as_str(data.get("industry_name", "")),
        concept_title=_as_str(data.get("concept_title", "")),
        recommended_business_type=_as_str(data.get("recommended_business_type", "")),
        operation_model=cast(dict[str, object], data.get("operation_model", {})),
        menu_strategy=cast(dict[str, object], data.get("menu_strategy", {})),
        pricing_strategy=cast(dict[str, object], data.get("pricing_strategy", {})),
        launch_plan=cast(list[dict[str, object]], data.get("launch_plan", [])),
        financial_targets=cast(dict[str, object], data.get("financial_targets", {})),
        advisor_snapshots=cast(dict[str, object], data.get("advisor_snapshots", {})),
    )
