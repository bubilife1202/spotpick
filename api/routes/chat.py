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


class ChatResponse(BaseModel):
    reply: str = Field(..., description="AI 응답")


class ChartData(BaseModel):
    type: str = Field(..., description='"time", "day", "age", "gender"')
    title: str = Field(..., description="차트 제목")
    data: list[dict[str, object]] = Field(default_factory=list, description="차트 데이터")


class RecommendationCardData(BaseModel):
    rank: int = Field(..., description="추천 순위")
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
    store_count: Optional[int] = Field(None, description="경쟁 점포 수")
    survival_rate: Optional[float] = Field(None, description="2년 생존율(0-1)")
    key_success_factors: list[str] = Field(default_factory=list, description="핵심 성공 요인")
    coordinates: Optional[dict[str, float]] = Field(None, description="지도 좌표 (lat/lng)")


class StructuredChatResponse(BaseModel):
    reply: str = Field(..., description="AI 응답")
    recommendations: list[RecommendationCardData] = Field(default_factory=list)
    charts: list[ChartData] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    context: dict[str, object] = Field(default_factory=dict)


@router.post("/chat", response_model=StructuredChatResponse)
async def chat(request: ChatRequest, req: Request):
    client_ip = req.client.host if req.client else "unknown"
    if not check_rate_limit(client_ip):
        raise HTTPException(
            status_code=429, detail="요청이 너무 많습니다. 잠시 후 다시 시도해주세요."
        )

    try:
        service = get_chat_service()

        history: list[HistoryMessage] | None = None
        if request.history:
            history = [{"role": m.role, "content": m.content} for m in request.history]

        seed_context: ConversationContext | None = None
        if request.context and isinstance(request.context, dict):
            seed_context = ConversationContext(
                district=(request.context.get("district") if isinstance(request.context.get("district"), str) else None),
                budget_min=(request.context.get("budget_min") if isinstance(request.context.get("budget_min"), int) else None),
                budget_max=(request.context.get("budget_max") if isinstance(request.context.get("budget_max"), int) else None),
                area_type=(request.context.get("area_type") if isinstance(request.context.get("area_type"), str) else None),
                time_preference=(
                    request.context.get("time_preference")
                    if isinstance(request.context.get("time_preference"), str)
                    else None
                ),
                age_target=(request.context.get("age_target") if isinstance(request.context.get("age_target"), str) else None),
                gender_target=(
                    request.context.get("gender_target")
                    if isinstance(request.context.get("gender_target"), str)
                    else None
                ),
                cafe_type=(request.context.get("cafe_type") if isinstance(request.context.get("cafe_type"), str) else None),
            )

        response: StructuredChatPayload = await service.chat(request.message, history, seed_context=seed_context)
        recommendations = [RecommendationCardData(**r) for r in response["recommendations"]]
        charts = [
            ChartData(
                type=c["type"],
                title=c["title"],
                data=[dict(d) for d in c["data"]],
            )
            for c in response["charts"]
        ]

        return StructuredChatResponse(
            reply=response["reply"],
            recommendations=recommendations,
            charts=charts,
            suggested_questions=response["suggested_questions"],
            context=dict(response["context"]),
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
            service = get_chat_service()

            history: list[HistoryMessage] | None = None
            if request.history:
                history = [{"role": m.role, "content": m.content} for m in request.history]

            seed_context: ConversationContext | None = None
            if request.context and isinstance(request.context, dict):
                seed_context = ConversationContext(
                    district=(
                        request.context.get("district")
                        if isinstance(request.context.get("district"), str)
                        else None
                    ),
                    budget_min=(
                        request.context.get("budget_min")
                        if isinstance(request.context.get("budget_min"), int)
                        else None
                    ),
                    budget_max=(
                        request.context.get("budget_max")
                        if isinstance(request.context.get("budget_max"), int)
                        else None
                    ),
                    area_type=(
                        request.context.get("area_type")
                        if isinstance(request.context.get("area_type"), str)
                        else None
                    ),
                    time_preference=(
                        request.context.get("time_preference")
                        if isinstance(request.context.get("time_preference"), str)
                        else None
                    ),
                    age_target=(
                        request.context.get("age_target")
                        if isinstance(request.context.get("age_target"), str)
                        else None
                    ),
                    gender_target=(
                        request.context.get("gender_target")
                        if isinstance(request.context.get("gender_target"), str)
                        else None
                    ),
                    cafe_type=(
                        request.context.get("cafe_type")
                        if isinstance(request.context.get("cafe_type"), str)
                        else None
                    ),
                )

            response: StructuredChatPayload = await service.chat(request.message, history, seed_context=seed_context)
            reply = response["reply"]

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
        service = get_chat_service()
        return {
            "status": "healthy",
            "model": service.model,
            "data_loaded": len(service.data_service.districts) > 0,
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
