"""Explore API — 지도탐색 페이지용 엔드포인트."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

router = APIRouter(prefix="/explore")

# ── Seoul 25개 자치구 중심 좌표 ──────────────────────────────────────────────
_GU_CENTERS: list[dict[str, Any]] = []
_GU_MAP_CACHE: dict[str, dict[str, str]] = {}  # industry_code -> {district_code: gu_name}

_INDUSTRY_NAMES: dict[str, str] = {
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


def _load_gu_centers() -> list[dict[str, Any]]:
    global _GU_CENTERS
    if _GU_CENTERS:
        return _GU_CENTERS
    geo_file = Path(__file__).parent.parent.parent / "data" / "geo" / "seoul_gu_centers.json"
    with open(geo_file, encoding="utf-8") as f:
        _GU_CENTERS = json.load(f)
    return _GU_CENTERS


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """두 좌표 간 거리 (km)."""
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = math.sin(d_lat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _assign_gu(lat: float, lng: float) -> str:
    """좌표로 가장 가까운 자치구 배정."""
    centers = _load_gu_centers()
    best_gu = "종로구"
    best_dist = float("inf")
    for c in centers:
        d = _haversine_km(lat, lng, c["lat"], c["lng"])
        if d < best_dist:
            best_dist = d
            best_gu = c["gu_name"]
    return best_gu


def _get_gu_map(industry_code: str) -> dict[str, str]:
    """district_code → gu_name 매핑 (캐시)."""
    if industry_code in _GU_MAP_CACHE:
        return _GU_MAP_CACHE[industry_code]

    from api.services.data_service import get_data_service

    svc = get_data_service(industry_code)
    mapping: dict[str, str] = {}
    for d in svc.districts:
        lat = d.get("lat", 0.0)
        lng = d.get("lng", 0.0)
        if lat > 0 and lng > 0:
            mapping[str(d["district_code"])] = _assign_gu(lat, lng)
    _GU_MAP_CACHE[industry_code] = mapping
    return mapping


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/gu-summary")
def gu_summary(
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """자치구별 요약 — 지도 오버레이용."""
    from api.services.data_service import get_data_service

    svc = get_data_service(industry_code)
    gu_map = _get_gu_map(industry_code)

    # Group districts by gu (skip districts without coordinates)
    gu_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in svc.districts:
        code = str(d["district_code"])
        gu = gu_map.get(code)
        if gu:
            gu_groups[gu].append(d)

    centers = {c["gu_name"]: c for c in _load_gu_centers()}
    results: list[dict[str, Any]] = []

    for gu_name, districts in gu_groups.items():
        n = len(districts)
        if n == 0:
            continue

        center = centers.get(gu_name, {"lat": 0, "lng": 0})

        total_sales = sum(d.get("monthly_sales", 0) for d in districts)
        total_stores = sum(d.get("store_count", 0) for d in districts)
        total_foot_traffic = sum(d.get("foot_traffic_total", 0) for d in districts)
        total_new = sum(d.get("new_stores", 0) for d in districts)
        total_closed = sum(d.get("closed_stores", 0) for d in districts)
        avg_survival = sum(d.get("survival_rate", 0) for d in districts) / n

        # Score: composite of survival, sales per store, growth
        sales_per_store = total_sales / max(1, total_stores)
        growth_ratio = (total_new + 1) / max(1, total_closed + 1)
        score = round(avg_survival * 40 + min(1.0, sales_per_store / 50_000_000) * 35 + min(1.0, growth_ratio) * 25, 1)

        results.append({
            "gu_name": gu_name,
            "center_lat": center["lat"],
            "center_lng": center["lng"],
            "avg_score": score,
            "avg_monthly_sales": round(total_sales / n),
            "total_foot_traffic": total_foot_traffic,
            "total_store_count": total_stores,
            "avg_survival_rate": round(avg_survival, 4),
            "district_count": n,
            "new_stores_total": total_new,
            "closed_stores_total": total_closed,
        })

    results.sort(key=lambda x: x["avg_score"], reverse=True)
    return {"gu_list": results, "total": len(results)}


@router.get("/districts-geo")
def districts_geo(
    industry_code: str = Query("CS100010", description="업종 코드"),
    gu: str = Query(..., description="자치구 이름 (e.g., 강남구)"),
):
    """특정 자치구 내 상권 목록 + 좌표."""
    from api.services.data_service import get_data_service

    svc = get_data_service(industry_code)
    gu_map = _get_gu_map(industry_code)

    districts: list[dict[str, Any]] = []
    for d in svc.districts:
        code = str(d["district_code"])
        if gu_map.get(code) != gu:
            continue

        sc = max(1, d.get("store_count", 1))
        districts.append({
            "district_code": d["district_code"],
            "district_name": d["district_name"],
            "district_type": d.get("district_type", ""),
            "lat": d.get("lat", 0.0),
            "lng": d.get("lng", 0.0),
            "monthly_sales": d.get("monthly_sales", 0),
            "sales_per_store": round(d.get("monthly_sales", 0) / sc),
            "store_count": d.get("store_count", 0),
            "survival_rate": d.get("survival_rate", 0),
            "foot_traffic_total": d.get("foot_traffic_total", 0),
            "new_stores": d.get("new_stores", 0),
            "closed_stores": d.get("closed_stores", 0),
            "peak_time": d.get("peak_time", ""),
            "main_age_group": d.get("main_age_group", ""),
            "change_indicator": d.get("change_indicator", ""),
        })

    districts.sort(key=lambda x: x["monthly_sales"], reverse=True)
    return {"gu": gu, "districts": districts, "total": len(districts)}


@router.get("/industry-ranking")
def industry_ranking(
    district_code: str = Query(..., description="상권 코드"),
):
    """특정 상권에서 업종별 랭킹 — '이 동네에서 뭐가 잘 될까?'"""
    stores_file = Path(__file__).parent.parent.parent / "data" / "seoul" / "stores_all.json"

    if not stores_file.exists():
        return {"district_code": district_code, "rankings": [], "error": "stores data not found"}

    with open(stores_file, encoding="utf-8") as f:
        all_stores = json.load(f)

    # Filter to our 10 food/cafe industries and the target district
    target_code = str(district_code)
    industry_data: dict[str, dict[str, Any]] = {}

    for row in all_stores:
        ind_code = row.get("SVC_INDUTY_CD", "")
        if ind_code not in _INDUSTRY_NAMES:
            continue
        row_district = str(row.get("TRDAR_CD", ""))
        if row_district != target_code:
            continue

        store_count = int(row.get("STOR_CO", 0))
        new_stores = int(row.get("OPBIZ_STOR_CO", 0))
        closed_stores = int(row.get("CLSBIZ_STOR_CO", 0))
        franchise_stores = int(row.get("FRC_STOR_CO", 0))
        similar_count = int(row.get("SIMILR_INDUTY_STOR_CO", 0))

        industry_data[ind_code] = {
            "store_count": store_count,
            "new_stores": new_stores,
            "closed_stores": closed_stores,
            "franchise_stores": franchise_stores,
            "similar_count": similar_count,
        }

    # Also try to get sales data from the coffee districts (for CS100010)
    from api.services.data_service import get_data_service

    coffee_svc = get_data_service("CS100010")
    coffee_district = coffee_svc.get_district(target_code)

    # Get district name and basic info
    district_name = ""
    district_lat = 0.0
    district_lng = 0.0
    if coffee_district:
        district_name = coffee_district.get("district_name", "")
        district_lat = coffee_district.get("lat", 0.0)
        district_lng = coffee_district.get("lng", 0.0)

    rankings: list[dict[str, Any]] = []

    for ind_code, ind_name in _INDUSTRY_NAMES.items():
        data = industry_data.get(ind_code)
        if not data:
            continue

        sc = data["store_count"]
        new = data["new_stores"]
        closed = data["closed_stores"]
        franchise = data["franchise_stores"]

        # Score: lower competition + growth = better
        # Penalize high store count, reward new > closed
        competition_score = max(0, 100 - sc * 3)  # fewer stores = better
        growth_score = 50 + (new - closed) * 10  # net positive = better
        growth_score = max(0, min(100, growth_score))
        franchise_penalty = min(30, franchise * 2)  # high franchise = harder entry

        score = round(competition_score * 0.4 + growth_score * 0.4 - franchise_penalty * 0.2, 1)
        score = max(0, min(100, score))

        # Generate reason text
        reasons: list[str] = []
        if sc <= 3:
            reasons.append("경쟁 매우 낮음")
        elif sc <= 8:
            reasons.append("경쟁 적정")
        elif sc <= 15:
            reasons.append("경쟁 보통")
        else:
            reasons.append(f"경쟁 과다 ({sc}개)")

        if new > closed:
            reasons.append("성장 추세")
        elif new < closed:
            reasons.append("축소 추세")
        else:
            reasons.append("안정세")

        if franchise > sc * 0.5 and sc > 0:
            reasons.append("프랜차이즈 밀집")

        # Add monthly_sales for coffee industry if available
        monthly_sales = 0
        survival_rate = 0.0
        if ind_code == "CS100010" and coffee_district:
            monthly_sales = coffee_district.get("monthly_sales", 0)
            survival_rate = coffee_district.get("survival_rate", 0)

        rankings.append({
            "industry_code": ind_code,
            "industry_name": ind_name,
            "score": score,
            "store_count": sc,
            "new_stores": new,
            "closed_stores": closed,
            "franchise_stores": franchise,
            "monthly_sales": monthly_sales,
            "survival_rate": survival_rate,
            "reason": " · ".join(reasons),
        })

    rankings.sort(key=lambda x: x["score"], reverse=True)

    # Add rank numbers
    for i, r in enumerate(rankings, 1):
        r["rank"] = i

    return {
        "district_code": district_code,
        "district_name": district_name,
        "lat": district_lat,
        "lng": district_lng,
        "rankings": rankings,
        "total": len(rankings),
    }
