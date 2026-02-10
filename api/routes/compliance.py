"""Compliance advisor API endpoints."""

from __future__ import annotations

from importlib import import_module
from typing import cast

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel


router = APIRouter(prefix="/compliance")


def _get_compliance_service(industry_code: str) -> object:
    module = import_module("api.services.compliance_advisor_service")
    factory = getattr(module, "get_compliance_advisor_service", None)
    if factory is None or not callable(factory):
        raise RuntimeError("compliance advisor service factory not available")
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


class PermitItemResponse(BaseModel):
    order: int
    name: str
    agency: str
    duration: str
    cost: int
    required: bool


class BuildingCheckResponse(BaseModel):
    status: str
    compatible: bool
    reason: str
    building_main_purpose: str
    usage: str
    source: str


class ComplianceAdviceResponse(BaseModel):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    permits: list[PermitItemResponse]
    permit_cost_total: int
    permit_duration_days: int
    building_check: BuildingCheckResponse
    notes: list[str]
    actions: list[str]
    glossary: dict[str, str]
    legal_meta: dict[str, str | int | float | bool]


@router.get("/advice", response_model=ComplianceAdviceResponse)
async def get_compliance_advice(
    district_code: str = Query(..., description="상권 코드 또는 상권명"),
    industry_code: str = Query("CS100010", description="업종 코드"),
    sigungu_cd: str | None = Query(default=None, description="건축물대장 시군구 코드"),
    bjdong_cd: str | None = Query(default=None, description="건축물대장 법정동 코드"),
) -> ComplianceAdviceResponse:
    service = _get_compliance_service(industry_code)
    analyze = getattr(service, "analyze", None)
    if analyze is None or not callable(analyze):
        raise HTTPException(status_code=500, detail="인허가 분석 서비스 초기화 실패")

    result_obj = analyze(
        district_code=district_code,
        sigungu_cd=sigungu_cd,
        bjdong_cd=bjdong_cd,
    )
    if result_obj is None:
        raise HTTPException(status_code=404, detail=f"상권을 찾을 수 없습니다: {district_code}")
    if not isinstance(result_obj, dict):
        raise HTTPException(status_code=500, detail="인허가 분석 결과 형식 오류")
    result = cast(dict[str, object], result_obj)

    permits_raw = result.get("permits", [])
    permits: list[PermitItemResponse] = []
    if isinstance(permits_raw, list):
        for permit_obj in permits_raw:
            if not isinstance(permit_obj, dict):
                continue
            permit = cast(dict[str, object], permit_obj)
            permits.append(
                PermitItemResponse(
                    order=_as_int(permit.get("order", 0), 0),
                    name=_as_str(permit.get("name", "")),
                    agency=_as_str(permit.get("agency", "")),
                    duration=_as_str(permit.get("duration", "")),
                    cost=_as_int(permit.get("cost", 0), 0),
                    required=_as_bool(permit.get("required", False), False),
                )
            )

    building_raw = result.get("building_check", {})
    building = cast(dict[str, object], building_raw if isinstance(building_raw, dict) else {})

    notes_raw = result.get("notes", [])
    notes = [str(v) for v in cast(list[object], notes_raw)] if isinstance(notes_raw, list) else []

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

    return ComplianceAdviceResponse(
        district_code=_as_str(result.get("district_code", district_code), district_code),
        district_name=_as_str(result.get("district_name", "")),
        industry_code=_as_str(result.get("industry_code", industry_code), industry_code),
        industry_name=_as_str(result.get("industry_name", "")),
        permits=permits,
        permit_cost_total=_as_int(result.get("permit_cost_total", 0), 0),
        permit_duration_days=_as_int(result.get("permit_duration_days", 0), 0),
        building_check=BuildingCheckResponse(
            status=_as_str(building.get("status", "unknown"), "unknown"),
            compatible=_as_bool(building.get("compatible", False), False),
            reason=_as_str(building.get("reason", "")),
            building_main_purpose=_as_str(building.get("building_main_purpose", "")),
            usage=_as_str(building.get("usage", "")),
            source=_as_str(building.get("source", "건축물대장 API"), "건축물대장 API"),
        ),
        notes=notes,
        actions=actions,
        glossary=glossary,
        legal_meta=legal_meta,
    )
