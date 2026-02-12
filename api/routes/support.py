"""정부 창업 지원사업 API."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.services.support_program_service import (
    SupportProgram,
    get_support_program_service,
)

router = APIRouter(prefix="/support")
SUBTYPE_COSTS_PATH = Path(__file__).resolve().parent.parent / "data" / "subtype_startup_costs.json"
_subtype_costs_cache: dict[str, Any] | None = None


def _load_subtype_costs() -> dict[str, Any]:
    global _subtype_costs_cache
    if _subtype_costs_cache is not None:
        return _subtype_costs_cache
    try:
        with open(SUBTYPE_COSTS_PATH, encoding="utf-8") as f:
            _subtype_costs_cache = json.load(f)
            if isinstance(_subtype_costs_cache, dict):
                return _subtype_costs_cache
    except Exception:
        pass
    _subtype_costs_cache = {}
    return _subtype_costs_cache


class SupportProgramResponse(BaseModel):
    """지원사업 응답 모델"""

    program_id: str
    program_name: str
    category: str
    support_target: str
    support_amount: str
    application_start_date: str
    application_end_date: str
    managing_org: str
    executing_org: str
    detail_url: str
    days_until_deadline: int
    program_type: str = "기타"
    max_amount_man: int = 0


class SupportProgramListResponse(BaseModel):
    """지원사업 목록 응답"""

    programs: list[SupportProgramResponse]
    total: int


class StartupCostItem(BaseModel):
    name: str
    min: int
    max: int


class StartupSubtypeCostResponse(BaseModel):
    industry_code: str
    sub_type: str
    min_budget_man: int
    items: list[StartupCostItem]
    tip: str
    is_fallback: bool = False


@router.get("/programs/active", response_model=SupportProgramListResponse)
async def get_active_programs(
    industry_code: str = Query("CS100010", description="업종 코드"),
) -> SupportProgramListResponse:
    """
    현재 신청 가능한 전체 지원사업 목록 조회 (마감 임박순)

    - 신청종료일 >= 오늘인 사업만 반환
    - 마감 임박순 정렬 (D-day 작은 것 먼저)
    """
    service = get_support_program_service(industry_code)
    programs = service.get_active_programs()

    return SupportProgramListResponse(
        programs=[SupportProgramResponse(**p) for p in programs],
        total=len(programs),
    )


@router.get("/programs", response_model=SupportProgramListResponse)
async def get_matched_programs(
    industry_code: str = Query("CS100010", description="업종 코드"),
    district: Annotated[str | None, Query(description="지역(예: '강남')")] = None,
    budget_min: Annotated[int | None, Query(description="최소 예산(원)")] = None,
    budget_max: Annotated[int | None, Query(description="최대 예산(원)")] = None,
    target_age: Annotated[str | None, Query(description="타겟 연령(예: '청년')")] = None,
) -> SupportProgramListResponse:
    """
    사용자 조건에 매칭되는 지원사업 목록 조회

    - 창업 분야만 필터링
    - 지역/예산/연령 조건 매칭
    - 마감 임박순 정렬
    """
    service = get_support_program_service(industry_code)
    programs = service.get_matched_programs(
        district=district,
        budget_min=budget_min,
        budget_max=budget_max,
        target_age=target_age,
    )

    return SupportProgramListResponse(
        programs=[SupportProgramResponse(**p) for p in programs],
        total=len(programs),
    )


@router.get("/startup-cost/subtype", response_model=StartupSubtypeCostResponse)
async def get_subtype_startup_cost(
    industry_code: str = Query("CS100010", description="업종 코드"),
    sub_type: str = Query(..., description="세부업종 (e.g., 만화카페)"),
) -> StartupSubtypeCostResponse:
    costs = _load_subtype_costs()
    industry_costs = costs.get(industry_code)
    if not isinstance(industry_costs, dict):
        industry_costs = costs.get("CS100010", {})

    selected = industry_costs.get(sub_type)
    if not isinstance(selected, dict):
        first_entry = next(iter(industry_costs.items()), ("기본형", {}))
        fallback_subtype, fallback_payload = first_entry
        if not isinstance(fallback_payload, dict):
            fallback_payload = {}
        selected = fallback_payload
        sub_type = fallback_subtype
        is_fallback = True
    else:
        is_fallback = False

    items_raw = selected.get("items", [])
    items = [
        StartupCostItem(
            name=str(item.get("name", "")),
            min=int(item.get("min", 0) or 0),
            max=int(item.get("max", 0) or 0),
        )
        for item in items_raw
        if isinstance(item, dict)
    ]

    return StartupSubtypeCostResponse(
        industry_code=industry_code,
        sub_type=sub_type,
        min_budget_man=int(selected.get("min_budget_man", 0) or 0),
        items=items,
        tip=str(selected.get("tip", "")),
        is_fallback=is_fallback,
    )
