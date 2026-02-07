"""
PDF 리포트 내보내기 API 라우트
"""

from __future__ import annotations

import logging
from fastapi import APIRouter, HTTPException  # type: ignore[import-not-found]
from fastapi.responses import Response  # type: ignore[import-not-found]
from pydantic import BaseModel, Field  # type: ignore[import-not-found]
from typing import Any, Optional

from api.services.pdf_service import get_pdf_service

router = APIRouter()
logger = logging.getLogger(__name__)


class PDFReportRequest(BaseModel):
    """PDF 리포트 생성 요청"""

    conversation_data: dict[str, Any] = Field(
        ...,
        description="대화에서 수집한 데이터 (recommendations, charts, competitive, simulation, context)",
    )
    industry_name: str = Field(default="카페", description="업종명 (예: 카페, 한식)")
    filename: Optional[str] = Field(
        None, description="다운로드 파일명 (미지정 시 자동 생성)"
    )


@router.post("/pdf/report")
async def generate_pdf_report(request: PDFReportRequest):
    """
    대화 기반 창업 분석 리포트 PDF 생성

    Args:
        request: PDF 생성 요청 데이터
            - conversation_data: 추천, 차트, 경쟁분석, 시뮬레이션 등
            - industry_name: 업종명
            - filename: 다운로드 파일명 (선택)

    Returns:
        PDF 파일 (application/pdf)
    """
    try:
        pdf_service = get_pdf_service()

        pdf_bytes = await pdf_service.generate_report_pdf(
            conversation_data=request.conversation_data,
            industry_name=request.industry_name,
        )

        # 파일명 생성
        filename = request.filename or f"{request.industry_name}_창업_리포트.pdf"
        if not filename.endswith(".pdf"):
            filename += ".pdf"

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "application/pdf",
            },
        )

    except Exception as e:
        logger.error(f"PDF 생성 실패: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF 생성 중 오류가 발생했습니다: {str(e)}")


@router.get("/pdf/health")
async def pdf_health_check():
    """PDF 서비스 상태 확인"""
    try:
        pdf_service = get_pdf_service()
        return {
            "status": "healthy",
            "service": "pdf_service",
            "template_dir": str(pdf_service.template_dir),
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }
