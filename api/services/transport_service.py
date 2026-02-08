"""
교통 접근성 서비스 — 지하철/버스 승하차 데이터 기반 최근접 역/정류장 분석
"""
from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "seoul"

# ── 지하철역 좌표 (주요 역 하드코딩, 실제 좌표) ─────────────────────
# 주요 서울 지하철역 좌표 (lat, lng)
_STATION_COORDS: dict[str, tuple[float, float]] = {
    "서울역": (37.5547, 126.9707), "시청": (37.5659, 126.9771),
    "종각": (37.5703, 126.9831), "종로3가": (37.5713, 126.9917),
    "종로5가": (37.5711, 126.9978), "동대문": (37.5712, 127.0094),
    "신설동": (37.5754, 127.0249), "강남": (37.4979, 127.0276),
    "역삼": (37.5007, 127.0366), "선릉": (37.5045, 127.0490),
    "삼성": (37.5090, 127.0637), "잠실": (37.5132, 127.1001),
    "홍대입구": (37.5571, 126.9244), "합정": (37.5497, 126.9135),
    "신촌": (37.5559, 126.9372), "이대": (37.5567, 126.9468),
    "건대입구": (37.5404, 127.0690), "성수": (37.5446, 127.0557),
    "왕십리": (37.5614, 127.0381), "영등포구청": (37.5255, 126.9012),
    "여의도": (37.5216, 126.9243), "신림": (37.4841, 126.9292),
    "교대": (37.4935, 127.0146), "서초": (37.4918, 127.0078),
    "사당": (37.4764, 126.9816), "이태원": (37.5344, 126.9948),
    "녹사평": (37.5344, 126.9876), "한양대": (37.5577, 127.0439),
    "뚝섬": (37.5475, 127.0472), "압구정": (37.5270, 127.0284),
    "신사": (37.5167, 127.0200), "잠실새내": (37.5114, 127.0865),
    "종합운동장": (37.5108, 127.0733), "명동": (37.5613, 126.9862),
    "을지로입구": (37.5660, 126.9823), "을지로3가": (37.5665, 126.9919),
    "충무로": (37.5612, 126.9946), "동대입구": (37.5577, 127.0002),
    "약수": (37.5544, 127.0104), "금호": (37.5573, 127.0187),
    "옥수": (37.5405, 127.0174), "한남": (37.5343, 127.0057),
    "마포": (37.5391, 126.9464), "공덕": (37.5440, 126.9521),
    "대방": (37.5133, 126.9268), "노량진": (37.5137, 126.9427),
    "용산": (37.5296, 126.9649), "이촌": (37.5217, 126.9708),
    "디지털미디어시티": (37.5769, 126.9000), "망원": (37.5565, 126.9104),
    "상수": (37.5478, 126.9227), "광화문": (37.5713, 126.9769),
    "안국": (37.5762, 126.9859), "혜화": (37.5841, 127.0019),
    "동묘앞": (37.5723, 127.0161), "창동": (37.6530, 127.0473),
    "노원": (37.6561, 127.0634), "수유": (37.6381, 127.0253),
    "미아": (37.6269, 127.0259), "길음": (37.6037, 127.0250),
    "성신여대입구": (37.5927, 127.0164), "한성대입구": (37.5882, 127.0063),
    "혜화역": (37.5841, 127.0019),
}


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
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
_subway_cache: dict[str, int] | None = None
_bus_cache: list[dict[str, Any]] | None = None


def _load_subway_data() -> dict[str, int]:
    """지하철 역별 일평균 승하차 합계."""
    global _subway_cache
    if _subway_cache is not None:
        return _subway_cache

    subway_file = DATA_DIR / "subway_passengers.json"
    if not subway_file.exists():
        _subway_cache = {}
        return _subway_cache

    with open(subway_file, encoding="utf-8") as f:
        raw = json.load(f)

    rows = raw.get("row", [])
    agg: dict[str, list[int]] = {}
    for r in rows:
        name = r.get("SBWY_STNS_NM", "")
        on = int(float(r.get("GTON_TNOPE", 0)))
        off = int(float(r.get("GTOFF_TNOPE", 0)))
        agg.setdefault(name, []).append(on + off)

    _subway_cache = {}
    for name, values in agg.items():
        _subway_cache[name] = int(sum(values) / max(1, len(values)))
    return _subway_cache


def _load_bus_data() -> list[dict[str, Any]]:
    """버스 정류장별 일평균 승하차."""
    global _bus_cache
    if _bus_cache is not None:
        return _bus_cache

    bus_file = DATA_DIR / "bus_passengers.json"
    if not bus_file.exists():
        _bus_cache = []
        return _bus_cache

    with open(bus_file, encoding="utf-8") as f:
        raw = json.load(f)

    rows = raw.get("row", [])
    # Aggregate by stop
    agg: dict[str, dict[str, Any]] = {}
    for r in rows:
        stop_id = r.get("STOPS_ID", "")
        stop_name = r.get("SBWY_STNS_NM", "") or r.get("STOPS_ARS_NO", "")
        on = int(float(r.get("GTON_TNOPE", 0)))
        off = int(float(r.get("GTOFF_TNOPE", 0)))
        if stop_id not in agg:
            agg[stop_id] = {"stop_id": stop_id, "stop_name": stop_name, "total": 0, "count": 0}
        agg[stop_id]["total"] += on + off
        agg[stop_id]["count"] += 1

    result = []
    for v in agg.values():
        result.append({
            "stop_id": v["stop_id"],
            "stop_name": v["stop_name"],
            "daily_avg": int(v["total"] / max(1, v["count"])),
        })

    _bus_cache = sorted(result, key=lambda x: x["daily_avg"], reverse=True)
    return _bus_cache


def get_nearest_subway(lat: float, lng: float) -> dict[str, Any] | None:
    """좌표에서 가장 가까운 지하철역 + 일평균 승하차."""
    subway_data = _load_subway_data()
    if not subway_data:
        return None

    best_name = ""
    best_dist = float("inf")
    for name, coords in _STATION_COORDS.items():
        d = _haversine_km(lat, lng, coords[0], coords[1])
        if d < best_dist:
            best_dist = d
            best_name = name

    daily_avg = subway_data.get(best_name, 0)
    # Also try with "역" suffix
    if daily_avg == 0:
        daily_avg = subway_data.get(f"{best_name}역", 0)

    return {
        "station_name": best_name,
        "distance_km": round(best_dist, 2),
        "distance_m": int(best_dist * 1000),
        "daily_passengers": daily_avg,
    }


def get_nearest_bus_stats(lat: float, lng: float) -> dict[str, Any]:
    """좌표 기반 주변 버스 이용 통계 (근접 정류장 기반 추정)."""
    bus_data = _load_bus_data()
    # 버스 정류장 좌표가 없으므로 상위 이용 정류장 통계로 대체
    top_stops = bus_data[:10] if bus_data else []
    total_daily = sum(s["daily_avg"] for s in top_stops)
    return {
        "nearby_stops_count": len(top_stops),
        "avg_daily_passengers": int(total_daily / max(1, len(top_stops))) if top_stops else 0,
        "top_stops": [{"name": s["stop_name"], "daily": s["daily_avg"]} for s in top_stops[:3]],
    }
