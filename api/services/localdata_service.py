"""
LOCALDATA 음식점 서비스 — seoul_restaurants.json (121K건) 기반 반경 검색
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "localdata"

# TM(EPSG:5186) → WGS84 간이 변환 상수 (서울 중심 근사)
_TM_X0 = 197500.0
_TM_Y0 = 451700.0
_WGS_LAT0 = 37.5665
_WGS_LNG0 = 126.978
_M_PER_DEG_LAT = 111320.0
_M_PER_DEG_LNG = 88800.0  # at lat ~37.5


def _tm_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """간이 TM 좌표 → WGS84 변환."""
    lat = _WGS_LAT0 + (y - _TM_Y0) / _M_PER_DEG_LAT
    lng = _WGS_LNG0 + (x - _TM_X0) / _M_PER_DEG_LNG
    return lat, lng


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


# ── 캐시 ─────────────────────────────────────────────────────────────
_restaurant_cache: list[dict[str, Any]] | None = None


def _load_restaurants() -> list[dict[str, Any]]:
    """LOCALDATA 음식점 데이터 로드 + WGS84 좌표 변환."""
    global _restaurant_cache
    if _restaurant_cache is not None:
        return _restaurant_cache

    restaurants_file = DATA_DIR / "seoul_restaurants.json"
    if not restaurants_file.exists():
        logger.warning("seoul_restaurants.json not found")
        _restaurant_cache = []
        return _restaurant_cache

    with open(restaurants_file, encoding="utf-8") as f:
        raw = json.load(f)

    result: list[dict[str, Any]] = []
    for r in raw:
        x = float(r.get("x", 0) or 0)
        y = float(r.get("y", 0) or 0)
        if x == 0 or y == 0:
            continue

        lat, lng = _tm_to_wgs84(x, y)
        result.append({
            "name": r.get("name", ""),
            "type": r.get("type", ""),
            "road_addr": r.get("road_addr", ""),
            "area_sqm": float(r.get("area_sqm", 0) or 0),
            "lat": round(lat, 6),
            "lng": round(lng, 6),
        })

    _restaurant_cache = result
    logger.info("Loaded %d restaurants from LOCALDATA", len(result))
    return result


def search_nearby_restaurants(
    lat: float,
    lng: float,
    radius_m: int = 500,
    food_type: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """반경 내 음식점 검색."""
    restaurants = _load_restaurants()

    # Pre-filter by bounding box for performance
    deg_lat = radius_m / _M_PER_DEG_LAT
    deg_lng = radius_m / _M_PER_DEG_LNG
    lat_min, lat_max = lat - deg_lat, lat + deg_lat
    lng_min, lng_max = lng - deg_lng, lng + deg_lng

    nearby: list[dict[str, Any]] = []
    type_counts: dict[str, int] = {}

    for r in restaurants:
        rlat = r["lat"]
        rlng = r["lng"]
        if not (lat_min <= rlat <= lat_max and lng_min <= rlng <= lng_max):
            continue

        dist = _haversine_m(lat, lng, rlat, rlng)
        if dist > radius_m:
            continue

        rtype = r["type"]
        type_counts[rtype] = type_counts.get(rtype, 0) + 1

        if food_type and rtype != food_type:
            continue

        nearby.append({**r, "distance_m": int(dist)})

    nearby.sort(key=lambda x: x["distance_m"])

    return {
        "total_nearby": len(nearby),
        "stores": nearby[:limit],
        "type_distribution": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
        "radius_m": radius_m,
    }
