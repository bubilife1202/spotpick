"""
서울시 공영주차장 서비스 — GetParkingInfo API + 좌표 기반 반경 검색
"""
from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv  # type: ignore[import-not-found]

_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")

SEOUL_API_KEY = os.getenv("SEOUL_API_KEY", "")
PARKING_URL = "http://openapi.seoul.go.kr:8088/{key}/json/GetParkingInfo/1/100/"

logger = logging.getLogger(__name__)


def _haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lng / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def get_nearby_parking(
    lat: float,
    lng: float,
    radius_m: int = 300,
) -> dict[str, Any]:
    """반경 내 공영주차장 검색."""
    if not SEOUL_API_KEY:
        logger.warning("SEOUL_API_KEY not set — returning fallback")
        return _fallback_parking(lat, lng)

    url = PARKING_URL.format(key=SEOUL_API_KEY)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        parking_info = data.get("GetParkingInfo", {})
        rows = parking_info.get("row", [])

        nearby: list[dict[str, Any]] = []
        for r in rows:
            plat = float(r.get("LAT", 0) or 0)
            plng = float(r.get("LNG", 0) or 0)
            if plat == 0 or plng == 0:
                continue

            dist = _haversine_m(lat, lng, plat, plng)
            if dist <= radius_m:
                nearby.append({
                    "name": r.get("PARKING_NAME", ""),
                    "address": r.get("ADDR", ""),
                    "capacity": int(r.get("CAPACITY", 0) or 0),
                    "type": r.get("PARKING_TYPE_NM", ""),
                    "fee": r.get("RATES", ""),
                    "distance_m": int(dist),
                    "lat": plat,
                    "lng": plng,
                })

        nearby.sort(key=lambda x: x["distance_m"])

        return {
            "total": len(nearby),
            "parking_lots": nearby[:10],
            "radius_m": radius_m,
            "source": "seoul_api",
        }
    except Exception as e:
        logger.error("Seoul parking API error: %s", e)
        return _fallback_parking(lat, lng)


def _fallback_parking(lat: float, lng: float) -> dict[str, Any]:
    """API 호출 실패 시 기본값."""
    return {
        "total": 0,
        "parking_lots": [],
        "radius_m": 300,
        "source": "fallback",
        "message": "주차장 데이터를 불러올 수 없습니다",
    }
