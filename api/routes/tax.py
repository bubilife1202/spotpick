"""Tax advisor API endpoints."""

from __future__ import annotations

from importlib import import_module
from typing import cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/tax")


def _get_tax_service(industry_code: str) -> object:
    module = import_module("api.services.tax_advisor_service")
    factory = getattr(module, "get_tax_advisor_service", None)
    if factory is None or not callable(factory):
        raise RuntimeError("tax advisor service factory not available")
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


class RevenueBasisResponse(BaseModel):
    monthly_revenue: int
    annual_revenue: int
    source: str


class TaxRegimeResponse(BaseModel):
    regime: str
    threshold_won: int
    reason: str


class VatEstimateResponse(BaseModel):
    vat_rate: float
    annual_output_vat: int
    annual_input_vat_credit: int
    annual_estimated_payable_vat: int
    exempt: bool
    exempt_threshold_won: int


class FilingCalendarItemResponse(BaseModel):
    name: str
    period: str
    typical_months: list[str | int]


class TaxAdviceResponse(BaseModel):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    revenue_basis: RevenueBasisResponse
    tax_regime: TaxRegimeResponse
    vat: VatEstimateResponse
    filing_calendar: list[FilingCalendarItemResponse]
    actions: list[str]
    glossary: dict[str, str]
    legal_meta: dict[str, str | int | float | bool]


@router.get("/advice", response_model=TaxAdviceResponse)
async def get_tax_advice(
    district_code: str = Query(..., description="상권 코드 또는 상권명"),
    industry_code: str = Query("CS100010", description="업종 코드"),
    monthly_revenue: int | None = Query(
        default=None,
        ge=0,
        description="월매출 직접 입력값(원). 입력 시 상권기반 추정 대신 사용",
    ),
) -> TaxAdviceResponse:
    service = _get_tax_service(industry_code)
    analyze = getattr(service, "analyze", None)
    if analyze is None or not callable(analyze):
        raise HTTPException(status_code=500, detail="세무 분석 서비스 초기화 실패")

    result_obj = analyze(
        district_code=district_code,
        monthly_revenue_override=monthly_revenue,
    )
    if result_obj is None:
        raise HTTPException(status_code=404, detail=f"상권을 찾을 수 없습니다: {district_code}")
    if not isinstance(result_obj, dict):
        raise HTTPException(status_code=500, detail="세무 분석 결과 형식 오류")
    result = cast(dict[str, object], result_obj)

    filing_calendar_raw = result.get("filing_calendar", [])
    calendar_rows: list[dict[str, object]] = []
    if isinstance(filing_calendar_raw, list):
        for item_obj in cast(list[object], filing_calendar_raw):
            if isinstance(item_obj, dict):
                calendar_rows.append(cast(dict[str, object], item_obj))

    filing_calendar = [
        FilingCalendarItemResponse(
            name=str(item.get("name", "")),
            period=str(item.get("period", "")),
            typical_months=[
                str(v)
                for v in cast(
                    list[object],
                    (
                        item.get("typical_months", [])
                        if isinstance(item.get("typical_months", []), list)
                        else []
                    ),
                )
                if isinstance(v, (str, int))
            ],
        )
        for item in calendar_rows
    ]

    legal_meta_raw_obj = result.get("legal_meta", {})
    legal_meta_raw = cast(
        dict[str, object], legal_meta_raw_obj if isinstance(legal_meta_raw_obj, dict) else {}
    )
    legal_meta: dict[str, str | int | float | bool] = {}
    for k, v in legal_meta_raw.items():
        if isinstance(v, (str, int, float, bool)):
            legal_meta[k] = v

    revenue_basis = cast(dict[str, object], result.get("revenue_basis", {}))
    tax_regime = cast(dict[str, object], result.get("tax_regime", {}))
    vat = cast(dict[str, object], result.get("vat", {}))

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

    return TaxAdviceResponse(
        district_code=str(result.get("district_code", district_code)),
        district_name=str(result.get("district_name", "")),
        industry_code=str(result.get("industry_code", industry_code)),
        industry_name=str(result.get("industry_name", "")),
        revenue_basis=RevenueBasisResponse(
            monthly_revenue=_as_int(revenue_basis.get("monthly_revenue", 0)),
            annual_revenue=_as_int(revenue_basis.get("annual_revenue", 0)),
            source=_as_str(revenue_basis.get("source", "")),
        ),
        tax_regime=TaxRegimeResponse(
            regime=_as_str(tax_regime.get("regime", "")),
            threshold_won=_as_int(tax_regime.get("threshold_won", 0)),
            reason=_as_str(tax_regime.get("reason", "")),
        ),
        vat=VatEstimateResponse(
            vat_rate=_as_float(vat.get("vat_rate", 0.0)),
            annual_output_vat=_as_int(vat.get("annual_output_vat", 0)),
            annual_input_vat_credit=_as_int(vat.get("annual_input_vat_credit", 0)),
            annual_estimated_payable_vat=_as_int(vat.get("annual_estimated_payable_vat", 0)),
            exempt=_as_bool(vat.get("exempt", False)),
            exempt_threshold_won=_as_int(vat.get("exempt_threshold_won", 0)),
        ),
        filing_calendar=filing_calendar,
        actions=actions,
        glossary=glossary,
        legal_meta=legal_meta,
    )
