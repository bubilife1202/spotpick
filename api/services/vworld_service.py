"""
vworld 2D Data API 서비스 — 용도지역 조회 (LT_C_UQ111)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv  # type: ignore[import-not-found]

_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")

VWORLD_API_KEY = os.getenv("VWORLD_API_KEY", "")
VWORLD_DATA_URL = "https://api.vworld.kr/req/data"

logger = logging.getLogger(__name__)


async def get_land_use(lat: float, lng: float) -> dict[str, Any]:
    """좌표 기반 용도지역 조회 (vworld LT_C_UQ111)."""
    if not VWORLD_API_KEY:
        logger.warning("VWORLD_API_KEY not set — returning fallback")
        return _fallback_land_use(lat, lng)

    params = {
        "service": "data",
        "request": "GetFeature",
        "data": "LT_C_UQ111",
        "key": VWORLD_API_KEY,
        "geomFilter": f"POINT({lng} {lat})",
        "crs": "EPSG:4326",
        "format": "json",
        "size": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(VWORLD_DATA_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

        response = data.get("response", {})
        result = response.get("result", {})
        features = result.get("featureCollection", {}).get("features", [])

        if not features:
            return _fallback_land_use(lat, lng)

        props = features[0].get("properties", {})
        return {
            "zone_name": props.get("UQ1_CD_NM", "정보없음"),
            "zone_code": props.get("UQ1_CD", ""),
            "zone_category": _categorize_zone(props.get("UQ1_CD_NM", "")),
            "source": "vworld",
        }
    except Exception as e:
        logger.error("vworld API error: %s", e)
        return _fallback_land_use(lat, lng)


def _categorize_zone(zone_name: str) -> str:
    """용도지역명을 대분류 카테고리로 변환."""
    if "상업" in zone_name:
        return "상업지역"
    if "주거" in zone_name:
        return "주거지역"
    if "공업" in zone_name:
        return "공업지역"
    if "녹지" in zone_name:
        return "녹지지역"
    return "기타"


def _fallback_land_use(lat: float, lng: float) -> dict[str, Any]:
    """API 키 없을 때 서울 주요 지역 기반 추정."""
    # 강남/서초/종로 등 주요 상업지역
    if 37.49 <= lat <= 37.52 and 126.97 <= lng <= 127.07:
        return {"zone_name": "일반상업지역 (추정)", "zone_code": "", "zone_category": "상업지역", "source": "fallback"}
    if 37.55 <= lat <= 37.58 and 126.97 <= lng <= 127.01:
        return {"zone_name": "일반상업지역 (추정)", "zone_code": "", "zone_category": "상업지역", "source": "fallback"}
    return {"zone_name": "제2종일반주거지역 (추정)", "zone_code": "", "zone_category": "주거지역", "source": "fallback"}
