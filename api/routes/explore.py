"""Explore API — 지도탐색 페이지용 엔드포인트."""

from __future__ import annotations

import json
import logging
import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/explore")

# ── Seoul 25개 자치구 중심 좌표 ──────────────────────────────────────────────
_GU_CENTERS: list[dict[str, Any]] = []
_GU_MAP_CACHE: dict[str, dict[str, str]] = {}  # industry_code -> {district_code: gu_name}

# stores_all.json 캐시: {industry_code -> {district_code -> {...}}}
_STORES_CACHE: dict[str, dict[str, dict[str, Any]]] = {}


def _load_stores_by_industry(industry_code: str) -> dict[str, dict[str, Any]]:
    """stores_all.json에서 특정 업종의 상권별 점포 데이터 로드 (캐시)."""
    if industry_code in _STORES_CACHE:
        return _STORES_CACHE[industry_code]

    stores_file = Path(__file__).parent.parent.parent / "data" / "seoul" / "stores_all.json"
    if not stores_file.exists():
        _STORES_CACHE[industry_code] = {}
        return {}

    # 전체 로드 후 업종별 캐시 (처음 한 번만)
    if not _STORES_CACHE:
        with open(stores_file, encoding="utf-8") as f:
            all_rows = json.load(f)

        by_industry: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
        for row in all_rows:
            ind = row.get("SVC_INDUTY_CD", "")
            if ind not in _INDUSTRY_NAMES:
                continue
            dc = str(row.get("TRDAR_CD", ""))
            store_count = int(row.get("STOR_CO", 0) or 0)
            # FRC_STOR_CO is district-wide franchise count (not per-industry)
            # Clamp to store_count to prevent franchise > total stores
            raw_franchise = int(row.get("FRC_STOR_CO", 0) or 0)
            franchise = min(raw_franchise, store_count)
            by_industry[ind][dc] = {
                "store_count": store_count,
                "new_stores": int(row.get("OPBIZ_STOR_CO", 0) or 0),
                "closed_stores": int(row.get("CLSBIZ_STOR_CO", 0) or 0),
                "franchise_stores": franchise,
                "similar_stores": int(row.get("SIMILR_INDUTY_STOR_CO", 0) or 0),
                "industry_name": row.get("SVC_INDUTY_CD_NM", ""),
            }
        for k, v in by_industry.items():
            _STORES_CACHE[k] = v

    return _STORES_CACHE.get(industry_code, {})

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
    """자치구별 요약 — 업종별 점포 데이터 + 공유 유동인구/시설 데이터."""
    from api.services.data_service import get_data_service

    # 카페 데이터 서비스 (공유 데이터: 좌표, 유동인구, 시설)
    base_svc = get_data_service("CS100010")
    gu_map = _get_gu_map("CS100010")

    # 업종별 점포 데이터
    stores_data = _load_stores_by_industry(industry_code)

    # Group base districts by gu
    gu_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in base_svc.districts:
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

        # 공유 데이터 (유동인구 — 업종 무관)
        total_foot_traffic = sum(d.get("foot_traffic_total", 0) for d in districts)

        # 업종별 데이터 from stores_all.json
        total_stores = 0
        total_new = 0
        total_closed = 0
        total_franchise = 0
        districts_with_stores = 0
        for d in districts:
            code = str(d["district_code"])
            sd = stores_data.get(code)
            if sd:
                total_stores += sd["store_count"]
                total_new += sd["new_stores"]
                total_closed += sd["closed_stores"]
                total_franchise += sd["franchise_stores"]
                districts_with_stores += 1

        # 매출: 카페만 실데이터, 나머지는 점포당 추정
        if industry_code == "CS100010":
            total_sales = sum(d.get("monthly_sales", 0) for d in districts)
            avg_survival = sum(d.get("survival_rate", 0) for d in districts) / n
        else:
            # 업종별 추정 매출 (점포당 평균 * 점포수)
            industry_avg_sales = {
                "CS100001": 28_000_000, "CS100002": 32_000_000, "CS100003": 35_000_000,
                "CS100004": 30_000_000, "CS100005": 25_000_000, "CS100006": 38_000_000,
                "CS100007": 22_000_000, "CS100008": 18_000_000, "CS100009": 20_000_000,
            }
            per_store = industry_avg_sales.get(industry_code, 25_000_000)
            total_sales = total_stores * per_store
            # 생존율: 점포 성장률 기반 추정
            growth = (total_new + 1) / max(1, total_closed + 1)
            avg_survival = min(1.0, max(0.3, 0.5 + (growth - 1) * 0.15))

        # Score
        sales_per_store = total_sales / max(1, total_stores)
        growth_ratio = (total_new + 1) / max(1, total_closed + 1)
        score = round(
            avg_survival * 40
            + min(1.0, sales_per_store / 50_000_000) * 35
            + min(1.0, growth_ratio) * 25,
            1,
        )

        results.append({
            "gu_name": gu_name,
            "center_lat": center["lat"],
            "center_lng": center["lng"],
            "avg_score": score,
            "avg_monthly_sales": round(total_sales / max(1, n)),
            "total_foot_traffic": total_foot_traffic,
            "total_store_count": total_stores,
            "avg_survival_rate": round(avg_survival, 4),
            "district_count": districts_with_stores if districts_with_stores > 0 else n,
            "new_stores_total": total_new,
            "closed_stores_total": total_closed,
            "franchise_ratio": min(100.0, round(total_franchise / max(1, total_stores) * 100, 1)),
        })

    results.sort(key=lambda x: x["avg_score"], reverse=True)
    return {"gu_list": results, "total": len(results)}


@router.get("/districts-geo")
def districts_geo(
    industry_code: str = Query("CS100010", description="업종 코드"),
    gu: str = Query(..., description="자치구 이름 (e.g., 강남구)"),
):
    """특정 자치구 내 상권 목록 + 업종별 점포 데이터."""
    from api.services.data_service import get_data_service

    base_svc = get_data_service("CS100010")
    gu_map = _get_gu_map("CS100010")
    stores_data = _load_stores_by_industry(industry_code)

    industry_avg_sales = {
        "CS100001": 28_000_000, "CS100002": 32_000_000, "CS100003": 35_000_000,
        "CS100004": 30_000_000, "CS100005": 25_000_000, "CS100006": 38_000_000,
        "CS100007": 22_000_000, "CS100008": 18_000_000, "CS100009": 20_000_000,
        "CS100010": 0,  # use real data
    }

    districts: list[dict[str, Any]] = []
    for d in base_svc.districts:
        code = str(d["district_code"])
        if gu_map.get(code) != gu:
            continue

        sd = stores_data.get(code, {})
        store_count = sd.get("store_count", 0) if sd else d.get("store_count", 0)
        new_stores = sd.get("new_stores", 0) if sd else d.get("new_stores", 0)
        closed_stores = sd.get("closed_stores", 0) if sd else d.get("closed_stores", 0)

        if industry_code == "CS100010":
            monthly_sales = d.get("monthly_sales", 0)
            survival_rate = d.get("survival_rate", 0)
        else:
            per_store = industry_avg_sales.get(industry_code, 25_000_000)
            monthly_sales = store_count * per_store
            growth = (new_stores + 1) / max(1, closed_stores + 1)
            survival_rate = min(1.0, max(0.3, 0.5 + (growth - 1) * 0.15))

        sc = max(1, store_count)
        districts.append({
            "district_code": d["district_code"],
            "district_name": d["district_name"],
            "district_type": d.get("district_type", ""),
            "lat": d.get("lat", 0.0),
            "lng": d.get("lng", 0.0),
            "monthly_sales": monthly_sales,
            "sales_per_store": round(monthly_sales / sc),
            "store_count": store_count,
            "survival_rate": survival_rate,
            "foot_traffic_total": d.get("foot_traffic_total", 0),
            "new_stores": new_stores,
            "closed_stores": closed_stores,
            "franchise_stores": sd.get("franchise_stores", 0) if sd else 0,
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
        raw_franchise = int(row.get("FRC_STOR_CO", 0))
        franchise_stores = min(raw_franchise, store_count)  # clamp
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


# ── Store-level endpoints ─────────────────────────────────────────────────


_FRANCHISE_BRANDS: dict[str, list[str]] = {
    "CS100001": ["본죽", "김가네", "한솥도시락", "명랑핫도그", "놀부부대찌개"],
    "CS100002": ["홍콩반점", "진짬뽕", "짬뽕지존"],
    "CS100003": ["스시로", "미소야", "하나미"],
    "CS100004": ["빕스", "아웃백", "매드포갈릭", "피자헛"],
    "CS100005": ["파리바게뜨", "뚜레쥬르", "브레댄코"],
    "CS100006": ["맥도날드", "버거킹", "롯데리아", "맘스터치", "KFC"],
    "CS100007": ["BBQ", "BHC", "교촌", "굽네치킨", "네네치킨", "페리카나"],
    "CS100008": ["죠스떡볶이", "국대떡볶이", "신전떡볶이"],
    "CS100009": ["장수생맥주", "호프집"],
    "CS100010": ["스타벅스", "투썸플레이스", "이디야", "메가커피", "컴포즈커피", "빽다방", "할리스"],
}

_INDIE_NAMES: dict[str, list[str]] = {
    "CS100001": ["엄마손밥집", "고향식당", "정성한상", "황금솥", "우리집밥상", "시골보리밥", "착한정식", "맛있는집"],
    "CS100002": ["동방반점", "황궁짬뽕", "용문중화", "진미반점"],
    "CS100003": ["도쿄라멘", "사쿠라스시", "하루이자카야", "미소라멘"],
    "CS100004": ["로마키친", "파스타팩토리", "리틀다이닝", "그린테이블"],
    "CS100005": ["달콤빵집", "행복베이커리", "마을제과", "해피브레드"],
    "CS100006": ["퀵버거", "파워치킨", "빅원버거"],
    "CS100007": ["황금치킨", "바삭통닭", "맛나치킨", "우리동네치킨", "참좋은치킨"],
    "CS100008": ["엄마떡볶이", "할머니분식", "왕김밥", "고향분식"],
    "CS100009": ["별밤호프", "달빛포차", "오늘밤한잔", "소나무맥주"],
    "CS100010": ["마을커피", "숲속카페", "언덕로스터스", "하늘브루잉", "감성카페", "작은찻집"],
}


def _generate_mock_stores_inline(
    lat: float,
    lng: float,
    industry_code: str,
    store_count_stat: int,
) -> list[dict[str, Any]]:
    """현실적 Mock 점포 데이터 생성 (SEMAS API 불가 시 폴백)."""
    try:
        from api.services.semas_store_service import _generate_mock_stores
        return _generate_mock_stores(lat, lng, industry_code, count=None)
    except Exception:
        pass

    rng = random.Random(hash(f"{lat:.4f}{lng:.4f}{industry_code}"))
    count = max(8, min(30, store_count_stat + rng.randint(-3, 5)))
    industry_name = _INDUSTRY_NAMES.get(industry_code, "카페")

    franchises = _FRANCHISE_BRANDS.get(industry_code, [])
    indies = _INDIE_NAMES.get(industry_code, [f"{industry_name}가게"])

    n_fc = max(1, int(count * 0.3))
    stores: list[dict[str, Any]] = []
    used_names: set[str] = set()

    for i in range(count):
        is_fc = i < n_fc and len(franchises) > 0
        if is_fc:
            name = franchises[i % len(franchises)]
            if name in used_names:
                name = f"{name} {rng.choice(['역점', '본점', '2호점'])}"
            cat = f"프랜차이즈 {industry_name}"
        else:
            name = rng.choice(indies)
            if name in used_names:
                name = f"{name} {rng.choice(['본점', '역전점', '중앙점'])}"
            cat = industry_name
        used_names.add(name)

        dlat = rng.uniform(-0.003, 0.003)
        dlng = rng.uniform(-0.004, 0.004)
        stores.append({
            "store_name": name,
            "category": cat,
            "address": "",
            "lat": round(lat + dlat, 7),
            "lng": round(lng + dlng, 7),
            "is_franchise": is_fc,
            "place_url": None,
            "phone": None,
        })
    return stores


@router.get("/stores")
async def get_stores(
    district_code: str = Query(..., description="상권 코드"),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """
    상권 내 개별 점포 목록.

    Flow:
    1. data_service에서 상권 좌표/매출 가져오기
    2. SEMAS API로 점포 목록 시도
    3. 카카오 로컬로 place_url 보강
    4. 실패 시 Mock 데이터 fallback
    """
    from api.services.data_service import get_data_service

    # Use cafe data_service for shared location data (lat/lng/district_name)
    base_svc = get_data_service("CS100010")
    district = base_svc.get_district(str(district_code))
    if not district:
        return {"stores": [], "total": 0, "district_name": "", "error": "상권을 찾을 수 없습니다"}

    district_name = district.get("district_name", "")
    lat = district.get("lat", 0.0)
    lng = district.get("lng", 0.0)

    # Per-industry store count from stores_all.json (not cafe data!)
    stores_data = _load_stores_by_industry(industry_code)
    sd = stores_data.get(str(district_code), {})
    store_count_stat = sd.get("store_count", 0) if sd else 0

    # Per-industry estimated monthly sales
    if industry_code == "CS100010":
        monthly_sales = district.get("monthly_sales", 0)
    else:
        industry_avg_sales = {
            "CS100001": 28_000_000, "CS100002": 32_000_000, "CS100003": 35_000_000,
            "CS100004": 30_000_000, "CS100005": 25_000_000, "CS100006": 38_000_000,
            "CS100007": 22_000_000, "CS100008": 18_000_000, "CS100009": 20_000_000,
        }
        per_store = industry_avg_sales.get(industry_code, 25_000_000)
        monthly_sales = store_count_stat * per_store

    # If 0 stores for this industry in this district, return empty
    if store_count_stat == 0:
        return {
            "stores": [],
            "total": 0,
            "district_name": district_name,
            "is_mock": False,
            "message": f"이 상권에 {_INDUSTRY_NAMES.get(industry_code, '')} 업종 점포 데이터가 없습니다",
        }

    # Step 1: Try SEMAS API (if service exists)
    stores: list[dict[str, Any]] = []
    try:
        from api.services.semas_store_service import fetch_stores_in_district
        stores = await fetch_stores_in_district(str(district_code), industry_code)
    except Exception as e:
        logger.info("SEMAS API 사용 불가 (mock fallback): %s", e)

    # Step 2: If SEMAS returned nothing, generate realistic mock stores
    use_mock = len(stores) == 0
    if use_mock:
        stores = _generate_mock_stores_inline(lat, lng, industry_code, store_count_stat)

    # Step 3: Try Kakao Local enrichment (if service exists)
    try:
        from api.services.kakao_local_service import search_places_in_area
        kakao_places = await search_places_in_area(
            lat=lat, lng=lng,
            industry_code=industry_code,
            radius=500,
            max_pages=3,
        )
        kakao_lookup: dict[str, dict[str, Any]] = {}
        for p in kakao_places:
            kakao_lookup[p["place_name"]] = p
        for store in stores:
            name = store["store_name"]
            matched = kakao_lookup.get(name)
            if not matched:
                for kname, kdata in kakao_lookup.items():
                    if name in kname or kname in name:
                        matched = kdata
                        break
            if matched:
                store["place_url"] = matched.get("place_url") or store.get("place_url")
                store["phone"] = matched.get("phone") or store.get("phone")
    except Exception as e:
        logger.info("카카오 로컬 보강 사용 불가: %s", e)

    # Step 4: Compute estimated_monthly_sales per store
    estimated_sales = int(monthly_sales / max(1, store_count_stat)) if monthly_sales > 0 else 0

    result_stores: list[dict[str, Any]] = []
    for s in stores:
        result_stores.append({
            "store_name": s.get("store_name", ""),
            "category": s.get("category", ""),
            "address": s.get("address", ""),
            "lat": s.get("lat", 0.0),
            "lng": s.get("lng", 0.0),
            "is_franchise": s.get("is_franchise", False),
            "place_url": s.get("place_url"),
            "phone": s.get("phone"),
            "estimated_monthly_sales": estimated_sales,
        })

    return {
        "stores": result_stores,
        "total": len(result_stores),
        "district_name": district_name,
        "is_mock": use_mock,
    }


# ── Sales Breakdown ───────────────────────────────────────────────────────

# 업종별 현실적 매출 패턴 기본값
_INDUSTRY_SALES_PATTERNS: dict[str, dict[str, Any]] = {
    "CS100001": {  # 한식
        "by_gender": {"male_pct": 48, "female_pct": 52},
        "by_age": {"10s": 3, "20s": 18, "30s": 25, "40s": 28, "50s": 18, "60s_plus": 8},
        "by_time": {"00_06": 1, "06_11": 10, "11_14": 38, "14_17": 15, "17_21": 28, "21_24": 8},
        "by_day": {"mon": 14, "tue": 14, "wed": 15, "thu": 15, "fri": 16, "sat": 15, "sun": 11},
    },
    "CS100002": {  # 중식
        "by_gender": {"male_pct": 52, "female_pct": 48},
        "by_age": {"10s": 3, "20s": 20, "30s": 28, "40s": 26, "50s": 16, "60s_plus": 7},
        "by_time": {"00_06": 1, "06_11": 5, "11_14": 40, "14_17": 12, "17_21": 32, "21_24": 10},
        "by_day": {"mon": 13, "tue": 14, "wed": 14, "thu": 15, "fri": 16, "sat": 16, "sun": 12},
    },
    "CS100003": {  # 일식
        "by_gender": {"male_pct": 45, "female_pct": 55},
        "by_age": {"10s": 2, "20s": 22, "30s": 30, "40s": 25, "50s": 14, "60s_plus": 7},
        "by_time": {"00_06": 1, "06_11": 3, "11_14": 35, "14_17": 12, "17_21": 38, "21_24": 11},
        "by_day": {"mon": 12, "tue": 13, "wed": 14, "thu": 15, "fri": 17, "sat": 17, "sun": 12},
    },
    "CS100004": {  # 양식
        "by_gender": {"male_pct": 42, "female_pct": 58},
        "by_age": {"10s": 4, "20s": 28, "30s": 30, "40s": 22, "50s": 11, "60s_plus": 5},
        "by_time": {"00_06": 1, "06_11": 5, "11_14": 32, "14_17": 15, "17_21": 35, "21_24": 12},
        "by_day": {"mon": 12, "tue": 13, "wed": 14, "thu": 14, "fri": 17, "sat": 18, "sun": 12},
    },
    "CS100005": {  # 베이커리
        "by_gender": {"male_pct": 35, "female_pct": 65},
        "by_age": {"10s": 5, "20s": 25, "30s": 28, "40s": 24, "50s": 13, "60s_plus": 5},
        "by_time": {"00_06": 2, "06_11": 22, "11_14": 20, "14_17": 25, "17_21": 22, "21_24": 9},
        "by_day": {"mon": 13, "tue": 13, "wed": 14, "thu": 14, "fri": 16, "sat": 17, "sun": 13},
    },
    "CS100006": {  # 패스트푸드
        "by_gender": {"male_pct": 48, "female_pct": 52},
        "by_age": {"10s": 12, "20s": 32, "30s": 22, "40s": 18, "50s": 10, "60s_plus": 6},
        "by_time": {"00_06": 3, "06_11": 12, "11_14": 30, "14_17": 18, "17_21": 25, "21_24": 12},
        "by_day": {"mon": 13, "tue": 13, "wed": 14, "thu": 14, "fri": 16, "sat": 17, "sun": 13},
    },
    "CS100007": {  # 치킨
        "by_gender": {"male_pct": 50, "female_pct": 50},
        "by_age": {"10s": 8, "20s": 28, "30s": 25, "40s": 22, "50s": 12, "60s_plus": 5},
        "by_time": {"00_06": 3, "06_11": 2, "11_14": 15, "14_17": 12, "17_21": 40, "21_24": 28},
        "by_day": {"mon": 12, "tue": 12, "wed": 13, "thu": 14, "fri": 18, "sat": 18, "sun": 13},
    },
    "CS100008": {  # 분식
        "by_gender": {"male_pct": 42, "female_pct": 58},
        "by_age": {"10s": 15, "20s": 30, "30s": 22, "40s": 18, "50s": 10, "60s_plus": 5},
        "by_time": {"00_06": 2, "06_11": 8, "11_14": 28, "14_17": 22, "17_21": 28, "21_24": 12},
        "by_day": {"mon": 14, "tue": 14, "wed": 14, "thu": 14, "fri": 15, "sat": 16, "sun": 13},
    },
    "CS100009": {  # 호프/주점
        "by_gender": {"male_pct": 62, "female_pct": 38},
        "by_age": {"10s": 1, "20s": 25, "30s": 28, "40s": 25, "50s": 15, "60s_plus": 6},
        "by_time": {"00_06": 8, "06_11": 1, "11_14": 5, "14_17": 5, "17_21": 35, "21_24": 46},
        "by_day": {"mon": 10, "tue": 11, "wed": 13, "thu": 15, "fri": 20, "sat": 19, "sun": 12},
    },
    "CS100010": {  # 카페
        "by_gender": {"male_pct": 42, "female_pct": 58},
        "by_age": {"10s": 5, "20s": 32, "30s": 28, "40s": 20, "50s": 10, "60s_plus": 5},
        "by_time": {"00_06": 2, "06_11": 25, "11_14": 22, "14_17": 20, "17_21": 22, "21_24": 9},
        "by_day": {"mon": 14, "tue": 14, "wed": 15, "thu": 15, "fri": 16, "sat": 15, "sun": 11},
    },
}


def _compute_sales_breakdown_from_district(
    district: dict[str, Any],
) -> dict[str, Any]:
    """실제 coffee_districts.json 데이터에서 매출 비율 계산."""
    total = max(1, district.get("monthly_sales", 1))

    # Gender
    male_ratio = district.get("male_ratio", 0.42)
    female_ratio = district.get("female_ratio", 0.58)
    # Normalize — sometimes male_ratio + female_ratio < 1 (missing data)
    g_sum = male_ratio + female_ratio
    if g_sum > 0:
        male_pct = round(male_ratio / g_sum * 100)
        female_pct = 100 - male_pct
    else:
        male_pct, female_pct = 42, 58

    # Age
    age_fields = [
        ("10s", "age_10_sales"),
        ("20s", "age_20_sales"),
        ("30s", "age_30_sales"),
        ("40s", "age_40_sales"),
        ("50s", "age_50_sales"),
        ("60s_plus", "age_60_sales"),
    ]
    by_age: dict[str, int] = {}
    age_total = sum(district.get(f, 0) for _, f in age_fields)
    if age_total > 0:
        for label, field in age_fields:
            by_age[label] = round(district.get(field, 0) / age_total * 100)
    else:
        by_age = {"10s": 5, "20s": 32, "30s": 28, "40s": 20, "50s": 10, "60s_plus": 5}
    # Ensure sums to 100
    diff = 100 - sum(by_age.values())
    if diff != 0:
        # Adjust the largest bucket
        largest_key = max(by_age, key=lambda k: by_age[k])
        by_age[largest_key] += diff

    # Time
    time_fields = [
        ("00_06", "time_00_06_sales"),
        ("06_11", "time_06_11_sales"),
        ("11_14", "time_11_14_sales"),
        ("14_17", "time_14_17_sales"),
        ("17_21", "time_17_21_sales"),
        ("21_24", "time_21_24_sales"),
    ]
    by_time: dict[str, int] = {}
    time_total = sum(district.get(f, 0) for _, f in time_fields)
    if time_total > 0:
        for label, field in time_fields:
            by_time[label] = round(district.get(field, 0) / time_total * 100)
    else:
        by_time = {"00_06": 2, "06_11": 25, "11_14": 22, "14_17": 20, "17_21": 22, "21_24": 9}
    diff = 100 - sum(by_time.values())
    if diff != 0:
        largest_key = max(by_time, key=lambda k: by_time[k])
        by_time[largest_key] += diff

    # Day
    day_fields = [
        ("mon", "mon_sales"),
        ("tue", "tue_sales"),
        ("wed", "wed_sales"),
        ("thu", "thu_sales"),
        ("fri", "fri_sales"),
        ("sat", "sat_sales"),
        ("sun", "sun_sales"),
    ]
    by_day: dict[str, int] = {}
    day_total = sum(district.get(f, 0) for _, f in day_fields)
    if day_total > 0:
        for label, field in day_fields:
            by_day[label] = round(district.get(field, 0) / day_total * 100)
    else:
        by_day = {"mon": 14, "tue": 14, "wed": 15, "thu": 15, "fri": 16, "sat": 15, "sun": 11}
    diff = 100 - sum(by_day.values())
    if diff != 0:
        largest_key = max(by_day, key=lambda k: by_day[k])
        by_day[largest_key] += diff

    return {
        "by_gender": {"male_pct": male_pct, "female_pct": female_pct},
        "by_age": by_age,
        "by_time": by_time,
        "by_day": by_day,
    }


def _generate_mock_sales_breakdown(
    industry_code: str,
    district_code: str,
) -> dict[str, Any]:
    """업종별 현실적 Mock 매출 분석 데이터 생성."""
    base = _INDUSTRY_SALES_PATTERNS.get(industry_code, _INDUSTRY_SALES_PATTERNS["CS100010"])

    # Deterministic but varied per district
    rng = random.Random(hash(f"{district_code}:{industry_code}"))

    def _jitter(d: dict[str, int], amount: int = 3) -> dict[str, int]:
        """Add small random variation while maintaining sum = 100."""
        result = {}
        for k, v in d.items():
            result[k] = max(0, v + rng.randint(-amount, amount))
        total = sum(result.values())
        if total > 0:
            # Normalize to 100
            factor = 100.0 / total
            normalized = {k: max(0, round(v * factor)) for k, v in result.items()}
            diff = 100 - sum(normalized.values())
            if diff != 0:
                largest = max(normalized, key=lambda k: normalized[k])
                normalized[largest] += diff
            return normalized
        return dict(d)

    return {
        "by_gender": {
            "male_pct": max(15, min(85, base["by_gender"]["male_pct"] + rng.randint(-3, 3))),
            "female_pct": 0,  # filled below
        },
        "by_age": _jitter(base["by_age"], 3),
        "by_time": _jitter(base["by_time"], 3),
        "by_day": _jitter(base["by_day"], 2),
    }


@router.get("/sales-breakdown")
def sales_breakdown(
    district_code: str = Query(..., description="상권 코드"),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """
    상권의 성별/연령/시간대/요일별 매출 비율.

    카페(CS100010)는 coffee_districts.json의 실데이터를 사용.
    다른 업종은 업종 특성에 맞는 현실적 패턴을 생성.
    """
    from api.services.data_service import get_data_service

    svc = get_data_service("CS100010")
    district = svc.get_district(str(district_code))
    if not district:
        return {
            "district_code": district_code,
            "district_name": "",
            "industry_code": industry_code,
            "breakdown": {},
            "is_real_data": False,
            "error": "상권을 찾을 수 없습니다",
        }

    district_name = district.get("district_name", "")
    is_real_data = False

    # 카페(CS100010)는 실데이터 사용
    if industry_code == "CS100010":
        breakdown = _compute_sales_breakdown_from_district(district)
        is_real_data = True
    else:
        # 다른 업종은 업종 전용 데이터 파일이 있을 때만 실데이터 사용
        # (data_service는 카페 데이터로 폴백하므로, 파일 존재 여부를 직접 확인)
        industry_file = Path(__file__).parent.parent.parent / "data" / "processed" / f"{industry_code}_districts.json"
        if industry_file.exists():
            try:
                ind_svc = get_data_service(industry_code)
                ind_district = ind_svc.get_district(str(district_code))
                if ind_district and ind_district.get("monthly_sales", 0) > 0:
                    breakdown = _compute_sales_breakdown_from_district(ind_district)
                    is_real_data = True
                else:
                    breakdown = _generate_mock_sales_breakdown(industry_code, str(district_code))
            except Exception:
                breakdown = _generate_mock_sales_breakdown(industry_code, str(district_code))
        else:
            breakdown = _generate_mock_sales_breakdown(industry_code, str(district_code))

    # Ensure female_pct = 100 - male_pct
    gender = breakdown.get("by_gender", {})
    if gender.get("female_pct", 0) == 0:
        gender["female_pct"] = 100 - gender.get("male_pct", 50)

    return {
        "district_code": district_code,
        "district_name": district_name,
        "industry_code": industry_code,
        "industry_name": _INDUSTRY_NAMES.get(industry_code, ""),
        "breakdown": breakdown,
        "is_real_data": is_real_data,
    }


# ── Sales Trend (quarterly) ──────────────────────────────────────────
_SALES_TREND_CACHE: dict[str, list[dict[str, Any]]] = {}


def _load_all_sales_data() -> dict[str, list[dict[str, Any]]]:
    """Load all quarterly sales files and index by district_code+industry_code."""
    global _SALES_TREND_CACHE
    if _SALES_TREND_CACHE:
        return _SALES_TREND_CACHE

    sales_dir = Path(__file__).parent.parent.parent / "data" / "seoul"
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for f in sorted(sales_dir.glob("sales_*.json")):
        try:
            with open(f, encoding="utf-8") as fp:
                raw = json.load(fp)
            rows = raw if isinstance(raw, list) else raw.get("row", [])
            for r in rows:
                key = f"{r.get('TRDAR_CD', '')}_{r.get('SVC_INDUTY_CD', '')}"
                period_raw = r.get("STDR_YYQU_CD", "")
                if len(period_raw) >= 5:
                    year = period_raw[:4]
                    quarter = period_raw[4:]
                    period = f"{year}Q{quarter}"
                else:
                    period = period_raw
                result[key].append({
                    "period": period,
                    "monthly_sales": float(r.get("THSMON_SELNG_AMT", 0) or 0),
                    "transactions": int(float(r.get("THSMON_SELNG_CO", 0) or 0)),
                })
        except Exception as e:
            logger.warning("Failed to load %s: %s", f.name, e)

    _SALES_TREND_CACHE = dict(result)
    return _SALES_TREND_CACHE


@router.get("/sales-trend")
def sales_trend(
    district_code: str = Query(..., description="상권 코드"),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """상권의 분기별 매출 트렌드 (최근 12분기)."""
    all_data = _load_all_sales_data()
    key = f"{district_code}_{industry_code}"
    quarters = all_data.get(key, [])

    # Sort by period and take last 12
    quarters.sort(key=lambda x: x["period"])
    recent = quarters[-12:] if len(quarters) > 12 else quarters

    # Calculate YoY change
    yoy_change = 0.0
    if len(recent) >= 5:
        current = recent[-1]["monthly_sales"]
        year_ago = recent[-5]["monthly_sales"]
        if year_ago > 0:
            yoy_change = round((current - year_ago) / year_ago * 100, 1)

    return {
        "district_code": district_code,
        "industry_code": industry_code,
        "quarters": recent,
        "yoy_change": yoy_change,
        "total_quarters": len(quarters),
    }
