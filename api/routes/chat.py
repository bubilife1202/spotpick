"""
대화형 창업 상담 API 라우트 - 스트리밍 및 Rate Limiting 지원
"""

from __future__ import annotations

import json
import time
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Request  # type: ignore[import-not-found]
from fastapi.responses import StreamingResponse  # type: ignore[import-not-found]
from pydantic import BaseModel, Field  # type: ignore[import-not-found]
from typing import Optional

from api.services.chat_service import (
    ConversationContext,
    HistoryMessage,
    StructuredChatPayload,
    get_chat_service,
)

router = APIRouter()

rate_limit_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = 20
RATE_WINDOW = 60


def check_rate_limit(client_ip: str) -> bool:
    now = time.time()
    rate_limit_store[client_ip] = [t for t in rate_limit_store[client_ip] if now - t < RATE_WINDOW]
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT:
        return False
    rate_limit_store[client_ip].append(now)
    return True


def get_context_str(context: dict[str, object], key: str) -> Optional[str]:
    value = context.get(key)
    return value if isinstance(value, str) else None


def get_context_int(context: dict[str, object], key: str) -> Optional[int]:
    value = context.get(key)
    return value if isinstance(value, int) else None


class ChatMessage(BaseModel):
    role: str = Field(..., description="메시지 역할 (user/assistant)")
    content: str = Field(..., description="메시지 내용")


class ChatRequest(BaseModel):
    message: str = Field(..., description="사용자 메시지")
    history: Optional[list[ChatMessage]] = Field(None, description="이전 대화 히스토리")
    context: Optional[dict[str, object]] = Field(
        None,
        description="클라이언트에서 제공하는 추가 컨텍스트(온보딩 등). 예: budget_min/budget_max/district/cafe_type",
    )
    industry_code: str = Field(default="CS100010", description="업종 코드")


class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI 응답")


class ChartData(BaseModel):
    type: str = Field(..., description='"time", "day", "age", "gender"')
    title: str = Field(..., description="차트 제목")
    data: list[dict[str, object]] = Field(default_factory=list, description="차트 데이터")


class RecommendationCardData(BaseModel):
    rank: int = Field(..., description="추천 순위")
    district_code: Optional[str] = Field(None, description="상권 코드")
    district_name: str = Field(..., description="상권명")
    district_type: str = Field(..., description="상권 유형")
    success_probability: float = Field(..., description="성공 확률")
    estimated_rent: int = Field(..., description="예상 월세")
    peak_time: str = Field(..., description="피크 시간대")
    main_age_group: str = Field(..., description="주요 연령대")
    risk_factors: list[str] = Field(default_factory=list, description="리스크 요인")
    recommendations: list[str] = Field(default_factory=list, description="추천 사항")
    # Optional extended fields (progressively enhanced UI)
    address: Optional[str] = Field(None, description="주소")
    monthly_sales: Optional[int] = Field(None, description="예상 월매출")
    monthly_sales_total: Optional[int] = Field(None, description="상권 월매출 총액")
    monthly_sales_per_store: Optional[int] = Field(None, description="점포당 월매출")
    monthly_transactions_total: Optional[int] = Field(None, description="상권 월 거래수")
    avg_ticket: Optional[int] = Field(None, description="평균 객단가")
    store_count: Optional[int] = Field(None, description="경쟁 점포 수")
    survival_rate: Optional[float] = Field(None, description="2년 생존율(0-1)")
    key_success_factors: list[str] = Field(default_factory=list, description="핵심 성공 요인")
    coordinates: Optional[dict[str, float]] = Field(None, description="지도 좌표 (lat/lng)")
    foot_traffic_total: Optional[int] = Field(None)
    worker_total: Optional[int] = Field(None)
    facility_subway: Optional[int] = Field(None)
    change_indicator: Optional[str] = Field(None)
    transit_percentile: Optional[float] = Field(None)
    positioning: Optional[str] = Field(None)
    positioning_detail: Optional[str] = Field(None)
    purchasing_power: Optional[float] = Field(None)


class StructuredChatResponse(BaseModel):
    reply: str = Field(..., description="AI 응답")
    recommendations: list[RecommendationCardData] = Field(default_factory=list)
    charts: list[ChartData] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    context: dict[str, object] = Field(default_factory=dict)
    competitive: Optional[dict[str, object]] = Field(None, description="경쟁 분석 데이터")
    simulation: Optional[dict[str, object]] = Field(None, description="창업 시뮬레이션 데이터")
    timeline: Optional[dict[str, object]] = Field(None, description="창업 타임라인 데이터")


@router.post("/chat", response_model=StructuredChatResponse)
async def chat(request: ChatRequest, req: Request):
    client_ip = req.client.host if req.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429, detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
        )

    try:
        service = get_chat_service(industry_code=request.industry_code)

        history: list[HistoryMessage] | None = None
        if request.history:
            history = [{"role": m.role, "content": m.content} for m in request.history]

        seed_context: ConversationContext | None = None
        if isinstance(request.context, dict):
            context = request.context
            seed_context = ConversationContext(
                district=get_context_str(context, "district"),
                budget_min=get_context_int(context, "budget_min"),
                budget_max=get_context_int(context, "budget_max"),
                area_type=get_context_str(context, "area_type"),
                time_preference=get_context_str(context, "time_preference"),
                age_target=get_context_str(context, "age_target"),
                gender_target=get_context_str(context, "gender_target"),
                cafe_type=get_context_str(context, "cafe_type"),
            )

        response: StructuredChatPayload = await service.chat(request.message, history, seed_context=seed_context)
        recommendations = [
            RecommendationCardData(**r) for r in response.get("recommendations", [])
        ]
        charts = [
            ChartData(
                type=c["type"],
                title=c["title"],
                data=[dict(d) for d in c["data"]],
            )
            for c in response.get("charts", [])
        ]

        return StructuredChatResponse(
            reply=response.get("reply", ""),
            recommendations=recommendations,
            charts=charts,
            suggested_questions=response.get("suggested_questions", []),
            context=dict(response.get("context") or {}),
            competitive=response.get("competitive"),  # type: ignore[arg-type]
            simulation=response.get("simulation"),  # type: ignore[arg-type]
            timeline=response.get("timeline"),  # type: ignore[arg-type]
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest, req: Request):
    """
    스트리밍 응답 API (Server-Sent Events)

    실시간으로 AI 응답을 스트리밍합니다.
    """
    client_ip = req.client.host if req.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429, detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
        )

    async def generate():
        try:
            service = get_chat_service(industry_code=request.industry_code)

            history: list[HistoryMessage] | None = None
            if request.history:
                history = [{"role": m.role, "content": m.content} for m in request.history]

            seed_context: ConversationContext | None = None
            if isinstance(request.context, dict):
                context = request.context
                seed_context = ConversationContext(
                    district=get_context_str(context, "district"),
                    budget_min=get_context_int(context, "budget_min"),
                    budget_max=get_context_int(context, "budget_max"),
                    area_type=get_context_str(context, "area_type"),
                    time_preference=get_context_str(context, "time_preference"),
                    age_target=get_context_str(context, "age_target"),
                    gender_target=get_context_str(context, "gender_target"),
                    cafe_type=get_context_str(context, "cafe_type"),
                )

            response: StructuredChatPayload = await service.chat(request.message, history, seed_context=seed_context)
            reply = response.get("reply", "")

            words = reply.split()
            buffer = ""
            for i, word in enumerate(words):
                buffer += word + " "
                if len(buffer) > 20 or i == len(words) - 1:
                    yield f"data: {json.dumps({'text': buffer})}\n\n"
                    buffer = ""

            yield f"data: {json.dumps({'done': True})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


@router.get("/chat/health")
async def health_check():
    """채팅 서비스 상태 확인"""
    try:
        service = get_chat_service(industry_code="CS100010")
        return {
            "status": "healthy",
            "model": service.model,
            "data_loaded": len(service.data_service.districts) > 0,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
