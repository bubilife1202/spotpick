"""정부 창업 지원사업 API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query
from pydantic import BaseModel

from api.services.support_program_service import (
    SupportProgram,
    get_support_program_service,
)

router = APIRouter(prefix="/support")


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


class SupportProgramListResponse(BaseModel):
    """지원사업 목록 응답"""
    programs: list[SupportProgramResponse]
    total: int


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
