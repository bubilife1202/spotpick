"""Labor advisor API endpoints."""

from __future__ import annotations

from importlib import import_module
from typing import cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/labor")


def _get_labor_service(industry_code: str) -> object:
    module = import_module("api.services.labor_advisor_service")
    factory = getattr(module, "get_labor_advisor_service", None)
    if factory is None or not callable(factory):
        raise RuntimeError("labor advisor service factory not available")
    return cast(object, factory(industry_code))


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


def _as_bool(value: object, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1", "yes", "y"):
            return True
        if lowered in ("false", "0", "no", "n"):
            return False
    return default


class WageReferenceResponse(BaseModel):
    effective_year: int
    hourly_won: int
    monthly_won_209h: int


class InsuranceRateResponse(BaseModel):
    national_pension_rate: float
    health_insurance_rate: float
    long_term_care_rate: float
    employment_insurance_rate: float
    industrial_accident_rate: float
    total_employer_rate: float


class LaborPlanResponse(BaseModel):
    employee_count: int
    monthly_gross_wage: int
    monthly_employer_insurance: int
    monthly_total_labor_cost: int


class LaborBenchmarkResponse(BaseModel):
    recommended_labor_ratio: float
    labor_budget_from_sales: int
    benchmark_source: str


class LaborAdviceResponse(BaseModel):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    monthly_revenue: int
    wage_reference: WageReferenceResponse
    insurance_rates: InsuranceRateResponse
    labor_plan: LaborPlanResponse
    labor_benchmark: LaborBenchmarkResponse
    affordable: bool
    budget_gap: int
    actions: list[str]
    glossary: dict[str, str]
    legal_meta: dict[str, str | int | float | bool]


@router.get("/advice", response_model=LaborAdviceResponse)
async def get_labor_advice(
    district_code: str = Query(..., description="상권 코드 또는 상권명"),
    industry_code: str = Query("CS100010", description="업종 코드"),
    employee_plan: str | None = Query(default=None, description="solo | 1-2 | 3+"),
    employee_count: int | None = Query(
        default=None, ge=1, le=50, description="직접 입력 고용 인원"
    ),
    monthly_revenue: int | None = Query(default=None, ge=0, description="월매출 직접 입력값(원)"),
) -> LaborAdviceResponse:
    service = _get_labor_service(industry_code)
    analyze = getattr(service, "analyze", None)
    if analyze is None or not callable(analyze):
        raise HTTPException(status_code=500, detail="노무 분석 서비스 초기화 실패")

    result_obj = analyze(
        district_code=district_code,
        employee_plan=employee_plan,
        custom_headcount=employee_count,
        monthly_revenue_override=monthly_revenue,
    )
    if result_obj is None:
        raise HTTPException(status_code=404, detail=f"상권을 찾을 수 없습니다: {district_code}")
    if not isinstance(result_obj, dict):
        raise HTTPException(status_code=500, detail="노무 분석 결과 형식 오류")
    result = cast(dict[str, object], result_obj)

    wage_ref = cast(dict[str, object], result.get("wage_reference", {}))
    insurance = cast(dict[str, object], result.get("insurance_rates", {}))
    labor_plan = cast(dict[str, object], result.get("labor_plan", {}))
    benchmark = cast(dict[str, object], result.get("labor_benchmark", {}))

    actions_raw = result.get("actions", [])
    actions = (
        [str(v) for v in cast(list[object], actions_raw)] if isinstance(actions_raw, list) else []
    )

    glossary_raw = result.get("glossary", {})
    glossary: dict[str, str] = {}
    if isinstance(glossary_raw, dict):
        for k, v in glossary_raw.items():
            if isinstance(k, str) and isinstance(v, str):
                glossary[k] = v

    legal_meta_raw = result.get("legal_meta", {})
    legal_meta: dict[str, str | int | float | bool] = {}
    if isinstance(legal_meta_raw, dict):
        for k, v in legal_meta_raw.items():
            if isinstance(k, str) and isinstance(v, (str, int, float, bool)):
                legal_meta[k] = v

    return LaborAdviceResponse(
        district_code=_as_str(result.get("district_code", district_code), district_code),
        district_name=_as_str(result.get("district_name", "")),
        industry_code=_as_str(result.get("industry_code", industry_code), industry_code),
        industry_name=_as_str(result.get("industry_name", "")),
        monthly_revenue=_as_int(result.get("monthly_revenue", 0)),
        wage_reference=WageReferenceResponse(
            effective_year=_as_int(wage_ref.get("effective_year", 2025), 2025),
            hourly_won=_as_int(wage_ref.get("hourly_won", 10_030), 10_030),
            monthly_won_209h=_as_int(wage_ref.get("monthly_won_209h", 2_096_270), 2_096_270),
        ),
        insurance_rates=InsuranceRateResponse(
            national_pension_rate=_as_float(insurance.get("national_pension_rate", 0.045), 0.045),
            health_insurance_rate=_as_float(
                insurance.get("health_insurance_rate", 0.03545), 0.03545
            ),
            long_term_care_rate=_as_float(insurance.get("long_term_care_rate", 0.00459), 0.00459),
            employment_insurance_rate=_as_float(
                insurance.get("employment_insurance_rate", 0.009), 0.009
            ),
            industrial_accident_rate=_as_float(
                insurance.get("industrial_accident_rate", 0.01), 0.01
            ),
            total_employer_rate=_as_float(insurance.get("total_employer_rate", 0.104), 0.104),
        ),
        labor_plan=LaborPlanResponse(
            employee_count=_as_int(labor_plan.get("employee_count", 1), 1),
            monthly_gross_wage=_as_int(labor_plan.get("monthly_gross_wage", 0), 0),
            monthly_employer_insurance=_as_int(labor_plan.get("monthly_employer_insurance", 0), 0),
            monthly_total_labor_cost=_as_int(labor_plan.get("monthly_total_labor_cost", 0), 0),
        ),
        labor_benchmark=LaborBenchmarkResponse(
            recommended_labor_ratio=_as_float(benchmark.get("recommended_labor_ratio", 0.27), 0.27),
            labor_budget_from_sales=_as_int(benchmark.get("labor_budget_from_sales", 0), 0),
            benchmark_source=_as_str(benchmark.get("benchmark_source", "")),
        ),
        affordable=_as_bool(result.get("affordable", False), False),
        budget_gap=_as_int(result.get("budget_gap", 0), 0),
        actions=actions,
        glossary=glossary,
        legal_meta=legal_meta,
    )
