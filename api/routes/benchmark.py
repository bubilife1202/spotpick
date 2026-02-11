from __future__ import annotations

import logging
from typing import cast

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api.services.kakao_local_service import (
    KAKAO_KEYWORD_URL,
    KAKAO_REST_API_KEY,
    get_kakao_local_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmark")

CATEGORY_TO_INDUSTRY: dict[str, str] = {
    "카페": "CS100010",
    "커피": "CS100010",
    "한식": "CS100001",
    "중식": "CS100002",
    "일식": "CS100003",
    "양식": "CS100004",
    "베이커리": "CS100005",
    "제과": "CS100005",
    "패스트푸드": "CS100006",
    "치킨": "CS100007",
    "분식": "CS100008",
    "호프": "CS100009",
    "술집": "CS100009",
}

INDUSTRY_NAMES: dict[str, str] = {
    "CS100001": "한식",
    "CS100002": "중식",
    "CS100003": "일식",
    "CS100004": "양식",
    "CS100005": "베이커리",
    "CS100006": "패스트푸드",
    "CS100007": "치킨",
    "CS100008": "분식",
    "CS100009": "호프/주점",
    "CS100010": "카페",
}


class BenchmarkStoreItem(BaseModel):
    id: str
    name: str
    category: str
    address: str
    road_address: str
    phone: str
    place_url: str
    x: float
    y: float
    industry_code: str
    industry_name: str


class BenchmarkSearchResponse(BaseModel):
    results: list[BenchmarkStoreItem]
    query: str


def _derive_industry_code(category_name: str) -> str:
    for keyword, industry_code in CATEGORY_TO_INDUSTRY.items():
        if keyword in category_name:
            return industry_code
    return "CS100010"


def _to_str(value: object) -> str:
    return value if isinstance(value, str) else ""


def _to_float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


@router.get("/search", response_model=BenchmarkSearchResponse)
async def search_benchmark_store(
    query: str,
) -> BenchmarkSearchResponse:
    if not query.strip():
        raise HTTPException(status_code=400, detail="query는 필수입니다")

    service = get_kakao_local_service()
    if not service.available:
        raise HTTPException(status_code=503, detail="카카오 로컬 API 키가 설정되지 않았습니다")

    params = {
        "query": query,
        "size": 5,
    }
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(KAKAO_KEYWORD_URL, params=params, headers=headers)
            _ = response.raise_for_status()
            payload = cast(object, response.json())
    except Exception as exc:
        logger.error("벤치마킹 매장 검색 실패: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=502, detail="처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."
        )

    payload_dict: dict[str, object] = (
        cast(dict[str, object], payload) if isinstance(payload, dict) else {}
    )
    documents_raw = payload_dict.get("documents")
    documents: list[object] = (
        cast(list[object], documents_raw) if isinstance(documents_raw, list) else []
    )
    results: list[BenchmarkStoreItem] = []

    for raw_doc in documents:
        if not isinstance(raw_doc, dict):
            continue
        doc = cast(dict[str, object], raw_doc)
        category_name = _to_str(doc.get("category_name"))
        industry_code = _derive_industry_code(category_name)
        results.append(
            BenchmarkStoreItem(
                id=_to_str(doc.get("id")),
                name=_to_str(doc.get("place_name")),
                category=category_name,
                address=_to_str(doc.get("address_name")),
                road_address=_to_str(doc.get("road_address_name")),
                phone=_to_str(doc.get("phone")),
                place_url=_to_str(doc.get("place_url")),
                x=_to_float(doc.get("x")),
                y=_to_float(doc.get("y")),
                industry_code=industry_code,
                industry_name=INDUSTRY_NAMES.get(industry_code, "카페"),
            )
        )

    return BenchmarkSearchResponse(results=results, query=query)
