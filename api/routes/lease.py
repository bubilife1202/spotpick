"""Lease advisor API endpoints."""

from __future__ import annotations

from importlib import import_module
from typing import cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/lease")


def _get_lease_service(industry_code: str) -> object:
    module = import_module("api.services.lease_advisor_service")
    factory = getattr(module, "get_lease_advisor_service", None)
    if factory is None or not callable(factory):
        raise RuntimeError("lease advisor service factory not available")
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


class RentEstimateResponse(BaseModel):
    monthly_rent: int
    deposit: int
    source: str


class LegalProtectionResponse(BaseModel):
    converted_deposit: int
    threshold: int
    protected: bool
    region: str
    monthly_multiplier: int
    renewal_request_years: int
    rent_increase_cap_rate: float


class LeaseAdviceResponse(BaseModel):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    rent_estimate: RentEstimateResponse
    legal_protection: LegalProtectionResponse
    contract_checklist: list[str]
    actions: list[str]
    glossary: dict[str, str]
    legal_meta: dict[str, str | int | float | bool]


@router.get("/advice", response_model=LeaseAdviceResponse)
async def get_lease_advice(
    district_code: str = Query(..., description="상권 코드 또는 상권명"),
    industry_code: str = Query("CS100010", description="업종 코드"),
    region: str = Query(
        "seoul", description="seoul | metropolitan_overconcentration | metropolitan_city | etc"
    ),
    monthly_rent: int | None = Query(default=None, ge=0, description="월세 직접 입력값(원)"),
    deposit: int | None = Query(default=None, ge=0, description="보증금 직접 입력값(원)"),
) -> LeaseAdviceResponse:
    service = _get_lease_service(industry_code)
    analyze = getattr(service, "analyze", None)
    if analyze is None or not callable(analyze):
        raise HTTPException(status_code=500, detail="임대차 분석 서비스 초기화 실패")

    result_obj = analyze(
        district_code=district_code,
        region=region,
        monthly_rent_override=monthly_rent,
        deposit_override=deposit,
    )
    if result_obj is None:
        raise HTTPException(status_code=404, detail=f"상권을 찾을 수 없습니다: {district_code}")
    if not isinstance(result_obj, dict):
        raise HTTPException(status_code=500, detail="임대차 분석 결과 형식 오류")
    result = cast(dict[str, object], result_obj)

    rent_raw = result.get("rent_estimate", {})
    rent_estimate = cast(dict[str, object], rent_raw if isinstance(rent_raw, dict) else {})

    legal_raw = result.get("legal_protection", {})
    legal_protection = cast(dict[str, object], legal_raw if isinstance(legal_raw, dict) else {})

    checklist_raw = result.get("contract_checklist", [])
    checklist = (
        [str(v) for v in cast(list[object], checklist_raw)]
        if isinstance(checklist_raw, list)
        else []
    )

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

    return LeaseAdviceResponse(
        district_code=_as_str(result.get("district_code", district_code), district_code),
        district_name=_as_str(result.get("district_name", "")),
        industry_code=_as_str(result.get("industry_code", industry_code), industry_code),
        industry_name=_as_str(result.get("industry_name", "")),
        rent_estimate=RentEstimateResponse(
            monthly_rent=_as_int(rent_estimate.get("monthly_rent", 0), 0),
            deposit=_as_int(rent_estimate.get("deposit", 0), 0),
            source=_as_str(rent_estimate.get("source", "")),
        ),
        legal_protection=LegalProtectionResponse(
            converted_deposit=_as_int(legal_protection.get("converted_deposit", 0), 0),
            threshold=_as_int(legal_protection.get("threshold", 0), 0),
            protected=_as_bool(legal_protection.get("protected", False), False),
            region=_as_str(legal_protection.get("region", "seoul"), "seoul"),
            monthly_multiplier=_as_int(legal_protection.get("monthly_multiplier", 100), 100),
            renewal_request_years=_as_int(legal_protection.get("renewal_request_years", 10), 10),
            rent_increase_cap_rate=_as_float(
                legal_protection.get("rent_increase_cap_rate", 0.05), 0.05
            ),
        ),
        contract_checklist=checklist,
        actions=actions,
        glossary=glossary,
        legal_meta=legal_meta,
    )
