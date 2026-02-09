"""상가 매물 검색 서비스 — 네이버 지역검색 + 카카오 부동산 중개소 폴백."""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

import httpx

from dotenv import load_dotenv  # type: ignore[import-not-found]

_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")

logger = logging.getLogger(__name__)


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


async def search_naver_properties(
    query: str, display: int = 10,
) -> list[dict[str, Any]]:
    """네이버 지역 검색 API로 상가 임대 매물/부동산 검색."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return []

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {"query": f"상가임대 {query}", "display": display, "sort": "comment"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("items", []):
            results.append({
                "name": _strip_html(item.get("title", "")),
                "address": item.get("roadAddress") or item.get("address", ""),
                "category": item.get("category", ""),
                "phone": item.get("telephone", ""),
                "link": item.get("link", ""),
                "mapx": item.get("mapx", ""),
                "mapy": item.get("mapy", ""),
                "source": "naver",
            })
        return results
    except Exception as e:
        logger.warning(f"Naver property search failed: {e}")
        return []


async def search_kakao_realtors(
    lat: float, lng: float, radius: int = 1000,
) -> list[dict[str, Any]]:
    """카카오 로컬 API로 인근 부동산 중개소 검색."""
    if not KAKAO_REST_API_KEY:
        return []

    url = "https://dapi.kakao.com/v2/local/search/category.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {
        "category_group_code": "AG2",  # 부동산
        "x": str(lng),
        "y": str(lat),
        "radius": radius,
        "sort": "distance",
        "size": 10,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            data = resp.json()

        results = []
        for doc in data.get("documents", []):
            results.append({
                "name": doc.get("place_name", ""),
                "address": doc.get("road_address_name") or doc.get("address_name", ""),
                "phone": doc.get("phone", ""),
                "distance": int(doc.get("distance", 0)),
                "place_url": doc.get("place_url", ""),
                "source": "kakao",
            })
        return results
    except Exception as e:
        logger.warning(f"Kakao realtor search failed: {e}")
        return []
