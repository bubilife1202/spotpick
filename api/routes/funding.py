"""Funding planner API endpoints."""

from __future__ import annotations

from importlib import import_module
from typing import Awaitable, Protocol, cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/funding")


class _FundingServiceProto(Protocol):
    def plan(
        self,
        district_code: str,
        area_pyeong: int = 10,
        equity: int | None = None,
        loan: int | None = None,
        grants: int | None = None,
        annual_rate: float | None = None,
        term_months: int = 36,
        use_ecos: bool = True,
    ) -> Awaitable[object]: ...


def _get_funding_service(industry_code: str) -> _FundingServiceProto:
    module = import_module("api.services.funding_planner_service")
    factory = getattr(module, "get_funding_planner_service", None)
    if factory is None or not callable(factory):
        raise RuntimeError("funding planner service factory not available")
    return cast(_FundingServiceProto, factory(industry_code))


def _as_str(value: object, default: str = "") -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def _as_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except Exception:
            return default
    return default


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except Exception:
            return default
    return default


class FundingResponse(BaseModel):
    district_code: str
    industry_code: str
    area_pyeong: int
    startup_cost_total: int
    startup_cost_range: dict[str, int]
    interest_reference: dict[str, object]
    split: dict[str, int]
    loan_plan: dict[str, object]
    support_programs: list[dict[str, object]]
    actions: list[str]


@router.get("/plan", response_model=FundingResponse)
async def plan_funding(
    district_code: str = Query(..., description="상권 코드 또는 상권명"),
    industry_code: str = Query("CS100010", description="업종 코드"),
    area_pyeong: int = Query(10, ge=5, le=100, description="면적(평)"),
    equity: int | None = Query(default=None, ge=0, description="자기자본(원)"),
    loan: int | None = Query(default=None, ge=0, description="대출(원)"),
    grants: int | None = Query(default=None, ge=0, description="지원금(원)"),
    annual_rate: float | None = Query(
        default=None, ge=0.0, le=1.0, description="연 이자율(예: 0.034)"
    ),
    term_months: int = Query(36, ge=6, le=120, description="대출 기간(개월)"),
    use_ecos: bool = Query(True, description="ECOS 기준금리 참조 여부"),
) -> FundingResponse:
    service = _get_funding_service(industry_code)
    result_obj = await service.plan(
        district_code=district_code,
        area_pyeong=area_pyeong,
        equity=equity,
        loan=loan,
        grants=grants,
        annual_rate=annual_rate,
        term_months=term_months,
        use_ecos=use_ecos,
    )
    if result_obj is None:
        raise HTTPException(status_code=404, detail=f"상권을 찾을 수 없습니다: {district_code}")
    if not isinstance(result_obj, dict):
        raise HTTPException(status_code=500, detail="자금계획 결과 형식 오류")

    data = cast(dict[str, object], result_obj)

    startup_cost_range_obj = data.get("startup_cost_range", {})
    startup_cost_range = cast(
        dict[str, object],
        startup_cost_range_obj if isinstance(startup_cost_range_obj, dict) else {},
    )
    split_obj = data.get("split", {})
    split = cast(dict[str, object], split_obj if isinstance(split_obj, dict) else {})
    loan_plan_obj = data.get("loan_plan", {})
    loan_plan = cast(dict[str, object], loan_plan_obj if isinstance(loan_plan_obj, dict) else {})
    interest_obj = data.get("interest_reference", {})
    interest_reference = cast(
        dict[str, object], interest_obj if isinstance(interest_obj, dict) else {}
    )

    actions_raw = data.get("actions", [])
    actions = (
        [str(v) for v in cast(list[object], actions_raw)] if isinstance(actions_raw, list) else []
    )

    programs_raw = data.get("support_programs", [])
    support_programs: list[dict[str, object]] = []
    if isinstance(programs_raw, list):
        for row in programs_raw:
            if isinstance(row, dict):
                support_programs.append(cast(dict[str, object], row))

    return FundingResponse(
        district_code=_as_str(data.get("district_code", district_code), district_code),
        industry_code=_as_str(data.get("industry_code", industry_code), industry_code),
        area_pyeong=_as_int(data.get("area_pyeong", area_pyeong), area_pyeong),
        startup_cost_total=_as_int(data.get("startup_cost_total", 0), 0),
        startup_cost_range={
            "total_min": _as_int(startup_cost_range.get("total_min", 0), 0),
            "total_max": _as_int(startup_cost_range.get("total_max", 0), 0),
        },
        interest_reference=interest_reference,
        split={
            "equity": _as_int(split.get("equity", 0), 0),
            "loan": _as_int(split.get("loan", 0), 0),
            "grants": _as_int(split.get("grants", 0), 0),
            "gap": _as_int(split.get("gap", 0), 0),
        },
        loan_plan={
            "principal": _as_int(loan_plan.get("principal", 0), 0),
            "annual_rate": _as_float(loan_plan.get("annual_rate", 0.0), 0.0),
            "term_months": _as_int(loan_plan.get("term_months", 0), 0),
            "monthly_payment": _as_int(loan_plan.get("monthly_payment", 0), 0),
            "interest_total_estimate": _as_int(loan_plan.get("interest_total_estimate", 0), 0),
        },
        support_programs=support_programs,
        actions=actions,
    )
