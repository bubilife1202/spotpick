"""Location Profile API — 상권 좌표 기반 입지 프로필 (6개 데이터 소스 병렬 호출)"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/location")

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "seoul"

# ── 생활인구 캐시 ────────────────────────────────────────────────────
_living_pop_cache: dict[str, dict[str, Any]] | None = None


def _load_living_population() -> dict[str, dict[str, Any]]:
    """행정동별 생활인구 데이터 로드."""
    global _living_pop_cache
    if _living_pop_cache is not None:
        return _living_pop_cache

    pop_file = DATA_DIR / "living_population.json"
    if not pop_file.exists():
        _living_pop_cache = {}
        return _living_pop_cache

    with open(pop_file, encoding="utf-8") as f:
        raw = json.load(f)

    rows = raw.get("row", [])
    result: dict[str, dict[str, Any]] = {}
    for r in rows:
        dong_code = r.get("ADSTRD_CODE_SE", "")
        total = float(r.get("TOT_LVPOP_CO", 0) or 0)
        # 시간대별 (TMZON_PD_SE: 0-23)
        time_zone = r.get("TMZON_PD_SE", "")

        if dong_code not in result:
            result[dong_code] = {"total": 0, "by_time": {}, "male_total": 0, "female_total": 0}

        result[dong_code]["total"] += total
        result[dong_code]["by_time"][time_zone] = total

        # 연령/성별 합산
        for age_prefix in ["F0T9", "F10T14", "F15T19", "F20T24", "F25T29", "F30T34",
                           "F35T39", "F40T44", "F45T49", "F50T54", "F55T59", "F60T64",
                           "F65T69", "F70T74", "F75T79", "F80_"]:
            male_key = f"MALE_{age_prefix}_LVPOP_CO"
            female_key = f"FEMALE_{age_prefix}_LVPOP_CO"
            result[dong_code]["male_total"] += float(r.get(male_key, 0) or 0)
            result[dong_code]["female_total"] += float(r.get(female_key, 0) or 0)

    _living_pop_cache = result
    return result


def _get_district_coords(district_code: str) -> tuple[float, float]:
    """상권 코드로 좌표 조회."""
    from api.services.data_service import get_data_service
    svc = get_data_service("CS100010")
    district = svc.get_district(district_code)
    if district:
        return district.get("lat", 0.0), district.get("lng", 0.0)
    return 0.0, 0.0


@router.get("/profile")
async def get_location_profile(
    district_code: str = Query(..., description="상권 코드"),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """
    상권 입지 프로필 — 용도지역, 학교, 주차장, 교통, 생활인구를 병렬 조회.
    """
    lat, lng = _get_district_coords(district_code)
    if lat == 0 or lng == 0:
        return {"error": "상권 좌표를 찾을 수 없습니다", "district_code": district_code}

    # 병렬 호출
    results = await asyncio.gather(
        _get_land_use(lat, lng),
        _get_school_proximity(lat, lng),
        _get_parking(lat, lng),
        _get_subway(lat, lng),
        return_exceptions=True,
    )

    land_use = results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])}
    school = results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])}
    parking = results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])}
    subway = results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])}

    # 생활인구 (동기)
    living_pop = _get_living_pop_summary(district_code)

    # 버스 (동기)
    bus = _get_bus_stats(lat, lng)

    return {
        "district_code": district_code,
        "lat": lat,
        "lng": lng,
        "land_use": land_use,
        "school_proximity": school,
        "parking": parking,
        "subway": subway,
        "bus": bus,
        "living_population": living_pop,
    }


async def _get_land_use(lat: float, lng: float) -> dict[str, Any]:
    from api.services.vworld_service import get_land_use
    return await get_land_use(lat, lng)


async def _get_school_proximity(lat: float, lng: float) -> dict[str, Any]:
    """학교 근접도 (카카오 SC4 카테고리)."""
    from api.services.kakao_local_service import get_kakao_local_service
    svc = get_kakao_local_service()
    if not svc.available:
        return {"nearby_schools": [], "in_restricted_zone": False, "source": "unavailable"}

    try:
        import httpx
        params = {
            "category_group_code": "SC4",
            "x": str(lng),
            "y": str(lat),
            "radius": 200,
            "size": 15,
            "sort": "distance",
        }
        headers = {"Authorization": f"KakaoAK {svc._api_key}"}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://dapi.kakao.com/v2/local/search/category.json",
                params=params, headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()

        schools = []
        for doc in data.get("documents", []):
            schools.append({
                "name": doc.get("place_name", ""),
                "category": doc.get("category_name", ""),
                "distance_m": int(doc.get("distance", 0)),
            })

        return {
            "nearby_schools": schools,
            "count": len(schools),
            "in_restricted_zone": len(schools) > 0,
            "source": "kakao",
        }
    except Exception as e:
        logger.error("School proximity error: %s", e)
        return {"nearby_schools": [], "in_restricted_zone": False, "source": "error"}


async def _get_parking(lat: float, lng: float) -> dict[str, Any]:
    from api.services.parking_service import get_nearby_parking
    return await get_nearby_parking(lat, lng, radius_m=300)


async def _get_subway(lat: float, lng: float) -> dict[str, Any]:
    from api.services.transport_service import get_nearest_subway
    result = get_nearest_subway(lat, lng)
    return result or {"station_name": "", "distance_km": 0, "daily_passengers": 0}


def _get_bus_stats(lat: float, lng: float) -> dict[str, Any]:
    from api.services.transport_service import get_nearest_bus_stats
    return get_nearest_bus_stats(lat, lng)


def _get_living_pop_summary(district_code: str) -> dict[str, Any]:
    """행정동 기반 생활인구 요약."""
    pop_data = _load_living_population()
    # 상권 코드의 앞 5자리가 행정동 코드에 근접
    dong_prefix = district_code[:5] if len(district_code) >= 5 else district_code

    # 해당 행정동 찾기
    matched = None
    for dong_code, data in pop_data.items():
        if dong_code.startswith(dong_prefix):
            matched = data
            break

    if not matched:
        return {"total": 0, "male_ratio": 0.5, "female_ratio": 0.5, "source": "no_match"}

    total = matched["male_total"] + matched["female_total"]
    male_ratio = matched["male_total"] / max(1, total) if total > 0 else 0.5
    return {
        "total": int(matched["total"]),
        "male_ratio": round(male_ratio, 2),
        "female_ratio": round(1 - male_ratio, 2),
        "by_time": matched.get("by_time", {}),
        "source": "living_population",
    }
