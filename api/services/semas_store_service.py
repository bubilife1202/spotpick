"""
SEMAS (소상공인시장진흥공단) Store API Service

개별 점포 데이터 조회: 상권 내 점포 목록, 반경 검색.
API: apis.data.go.kr/B553077/api/open/sdsc2

NOTE: 2025년 하반기 SEMAS API가 /sdsc → /sdsc2 로 마이그레이션됨.
  - 업종분류: 837개 → 247개 (표준산업분류 10차 기반)
  - 상가업소번호 재생성 (과거 데이터와 비호환)
  - 응답 필드명은 동일 유지 (bizesNm, lat, lon 등)
"""

from __future__ import annotations

import logging
import math
import os
import random
import time
from pathlib import Path
from typing import Any

import httpx  # type: ignore[import-not-found]

logger = logging.getLogger(__name__)

DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY", "")

SEMAS_BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2"

# ---------------------------------------------------------------------------
# 업종 매핑: SEMAS 대분류코드 <-> 우리 CS 코드
# ---------------------------------------------------------------------------

# SEMAS indsLclsCd (대분류코드) 매핑
SEMAS_INDUSTRY_MAP: dict[str, dict[str, Any]] = {
    "CS100001": {"lclsCd": "Q", "keywords": ["한식"], "category": "음식"},
    "CS100002": {"lclsCd": "Q", "keywords": ["중식", "중화"], "category": "음식"},
    "CS100003": {"lclsCd": "Q", "keywords": ["일식", "일본"], "category": "음식"},
    "CS100004": {"lclsCd": "Q", "keywords": ["양식", "서양", "이탈리"], "category": "음식"},
    "CS100005": {"lclsCd": "Q", "keywords": ["제과", "베이커리", "빵"], "category": "음식"},
    "CS100006": {"lclsCd": "Q", "keywords": ["패스트", "피자", "햄버거", "버거"], "category": "음식"},
    "CS100007": {"lclsCd": "Q", "keywords": ["치킨", "닭"], "category": "음식"},
    "CS100008": {"lclsCd": "Q", "keywords": ["분식", "떡볶이", "김밥"], "category": "음식"},
    "CS100009": {"lclsCd": "Q", "keywords": ["주점", "호프", "맥주", "술집"], "category": "음식"},
    "CS100010": {"lclsCd": "Q", "keywords": ["커피", "카페", "음료"], "category": "음식"},
}

# ---------------------------------------------------------------------------
# 업종별 프랜차이즈 브랜드 리스트 (config 파일에서 추출)
# ---------------------------------------------------------------------------

FRANCHISE_BRANDS: dict[str, list[str]] = {
    "CS100001": ["한솥", "본죽", "김밥천국", "한식뷔페", "계절밥상", "큰집", "새마을식당", "백종원", "놀부", "명륜진사갈비"],
    "CS100002": ["홍콩반점", "미스터셰프", "차이홍", "짬뽕지존"],
    "CS100003": ["스시로", "쿠시카츠", "하나미"],
    "CS100004": ["빕스", "아웃백", "애슐리", "TGI", "매드포갈릭"],
    "CS100005": ["파리바게뜨", "뚜레쥬르", "성심당", "삼송빵집"],
    "CS100006": ["맥도날드", "버거킹", "롯데리아", "KFC", "맘스터치", "쉐이크쉑", "파이브가이즈", "노브랜드버거"],
    "CS100007": ["BBQ", "BHC", "교촌", "네네", "굽네", "호식이", "처갓집", "페리카나", "지코바"],
    "CS100008": ["신전떡볶이", "죠스떡볶이", "동대문엽기떡볶이", "국대떡볶이", "청년다방", "김밥천국", "김가네"],
    "CS100009": ["포차어게인", "삼거리포차", "한신포차"],
    "CS100010": [
        "스타벅스", "투썸", "이디야", "메가", "컴포즈", "빽다방", "할리스",
        "폴바셋", "파스쿠찌", "엔제리너스", "커피빈", "탐앤탐스", "더벤티",
        "매머드", "감성커피", "커피에반하다", "요거프레소",
    ],
}

# 전 업종 통합 프랜차이즈 목록 (빠른 look-up)
ALL_FRANCHISE_NAMES: list[str] = []
for _brands in FRANCHISE_BRANDS.values():
    ALL_FRANCHISE_NAMES.extend(_brands)
ALL_FRANCHISE_NAMES = list(set(ALL_FRANCHISE_NAMES))


def is_franchise(store_name: str, industry_code: str | None = None) -> bool:
    """점포명이 프랜차이즈 브랜드에 해당하는지 판별."""
    name_lower = store_name.strip()
    brands = FRANCHISE_BRANDS.get(industry_code, ALL_FRANCHISE_NAMES) if industry_code else ALL_FRANCHISE_NAMES
    for brand in brands:
        if brand in name_lower:
            return True
    return False


# ---------------------------------------------------------------------------
# 캐시 (TTL 24h)
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, Any]] = {}
CACHE_TTL = 86400  # 24h


def _get_cached(key: str) -> Any | None:
    if key in _cache:
        ts, val = _cache[key]
        if time.time() - ts < CACHE_TTL:
            return val
        del _cache[key]
    return None


def _set_cached(key: str, val: Any) -> None:
    _cache[key] = (time.time(), val)


# ---------------------------------------------------------------------------
# API 호출
# ---------------------------------------------------------------------------

async def _call_semas_api(
    endpoint: str,
    params: dict[str, str],
) -> list[dict[str, Any]]:
    """SEMAS API 호출 -> items 리스트 반환."""
    if not DATA_GO_KR_API_KEY:
        logger.warning("DATA_GO_KR_API_KEY 미설정 — SEMAS API 사용 불가")
        return []

    url = f"{SEMAS_BASE_URL}/{endpoint}"
    query_params = {
        "serviceKey": DATA_GO_KR_API_KEY,
        "type": "json",
        "numOfRows": "100",
        **params,
    }

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=query_params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("SEMAS API HTTP 오류: %s %s", e.response.status_code, url)
        return []
    except Exception as e:
        logger.error("SEMAS API 호출 실패: %s", e)
        return []

    # 응답 파싱: body.items
    try:
        body = data.get("body", data)
        if isinstance(body, dict):
            items = body.get("items", [])
        else:
            items = []
        if isinstance(items, dict):
            items = items.get("item", [])
        if isinstance(items, dict):
            items = [items]
        return items if isinstance(items, list) else []
    except Exception:
        logger.error("SEMAS API 파싱 실패: %s", str(data)[:300])
        return []


def _parse_store(item: dict[str, Any], industry_code: str | None = None) -> dict[str, Any]:
    """SEMAS API 응답 항목을 표준 store dict로 변환."""
    store_name = item.get("bizesNm", "")
    lat = float(item.get("lat", 0) or 0)
    lng = float(item.get("lon", 0) or 0)

    # 주소: 도로명 > 지번
    address = item.get("rdnmAdr", "") or item.get("lnmAdr", "")

    # 카테고리
    category_parts = [
        item.get("indsLclsNm", ""),
        item.get("indsMclsNm", ""),
        item.get("indsSclsNm", ""),
    ]
    category = " > ".join(p for p in category_parts if p)

    return {
        "store_name": store_name,
        "category": category,
        "address": address,
        "lat": lat,
        "lng": lng,
        "is_franchise": is_franchise(store_name, industry_code),
        "place_url": None,
        "phone": None,
        "semas_raw": {
            "indsLclsCd": item.get("indsLclsCd", ""),
            "indsMclsCd": item.get("indsMclsCd", ""),
            "indsSclsCd": item.get("indsSclsCd", ""),
        },
    }


def _matches_industry(item: dict[str, Any], industry_code: str) -> bool:
    """SEMAS 항목이 우리 업종에 매칭되는지 판별."""
    mapping = SEMAS_INDUSTRY_MAP.get(industry_code)
    if not mapping:
        return True  # 매핑 없으면 전부 포함

    keywords = mapping["keywords"]
    name_fields = [
        str(item.get("indsLclsNm", "")),
        str(item.get("indsMclsNm", "")),
        str(item.get("indsSclsNm", "")),
    ]
    for kw in keywords:
        if any(kw in f for f in name_fields):
            return True
    return False


# ---------------------------------------------------------------------------
# Public API: 반경 검색
# ---------------------------------------------------------------------------

async def fetch_stores_in_district(
    district_code: str,
    industry_code: str = "CS100010",
) -> list[dict[str, Any]]:
    """
    상권 중심 좌표 기준 반경 500m 내 점포 검색.

    1. data_service에서 상권 중심 좌표 가져오기
    2. SEMAS storeListInRadius API 호출
    3. 업종 필터링
    4. 프랜차이즈 판별
    """
    cache_key = f"semas_district:{district_code}:{industry_code}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    # 상권 좌표 가져오기
    from api.services.data_service import get_data_service
    svc = get_data_service("CS100010")  # 좌표는 카페 데이터에 있음
    district = svc.get_district(district_code)
    if not district:
        return []

    lat = district.get("lat", 0.0)
    lng = district.get("lng", 0.0)
    if lat == 0 or lng == 0:
        return []

    items = await _call_semas_api(
        "storeListInRadius",
        {
            "cx": str(lng),
            "cy": str(lat),
            "radius": "500",
            "numOfRows": "100",
        },
    )

    stores = []
    for item in items:
        if _matches_industry(item, industry_code):
            stores.append(_parse_store(item, industry_code))

    _set_cached(cache_key, stores)
    return stores


# ---------------------------------------------------------------------------
# Public API: 상권 코드 기반 검색
# ---------------------------------------------------------------------------

async def fetch_stores_by_area(district_code: str) -> list[dict[str, Any]]:
    """
    SEMAS storeListInArea API — 상권 코드 기반 전체 업종 점포 조회.
    """
    cache_key = f"semas_area:{district_code}"
    cached = _get_cached(cache_key)
    if cached is not None:
        return cached

    items = await _call_semas_api(
        "storeListInArea",
        {
            "key": district_code,
            "numOfRows": "100",
        },
    )

    stores = [_parse_store(item) for item in items]
    _set_cached(cache_key, stores)
    return stores


# ---------------------------------------------------------------------------
# Mock data fallback
# ---------------------------------------------------------------------------

# 업종별 인디 점포명 후보 (Mock)
_INDIE_NAMES: dict[str, list[str]] = {
    "CS100001": [
        "엄마손밥상", "시골집", "소담한상", "옛날집", "명가한식", "우리집밥",
        "일미반상", "봄날의집", "정성가득", "미소한상", "대박식당", "맛나식당",
        "아침고요", "초가집", "바른밥상", "온누리식당", "시래기집", "산들밥상",
    ],
    "CS100002": [
        "일품중화", "청룡", "금룡", "황용", "진원", "복성루",
        "만리장성", "중화반점", "대성각", "금성각", "향미각", "용문",
    ],
    "CS100003": [
        "오마카세히든", "스시마루", "이자카야별", "텐동하나", "사쿠라", "모리",
        "타쿠미", "유키노하나", "카이센", "라멘고쿠", "우오", "하쿠",
    ],
    "CS100004": [
        "테이블로", "르봉뗀", "파스타나무", "올리브가든", "피아트", "비스트로M",
        "레스토엘", "프리모", "라쿠치나", "더키친", "포레스트", "미오",
    ],
    "CS100005": [
        "밀도", "오월의빵", "카페도르", "나뚜르", "아티장", "르뺑도레",
        "빵명장", "마이플라워", "꿀빵", "온도베이커리", "모닝빵집", "하루빵",
    ],
    "CS100006": [
        "수제버거랩", "크런치타운", "더그릴", "번스앤비프", "프라이하우스", "팟타이",
    ],
    "CS100007": [
        "황금올리브", "장모님치킨", "참숯통닭", "1등치킨", "크런치팝", "도리치킨",
        "바삭한형제", "골든후라이드", "치킨마을", "시골치킨", "왕치킨", "앙념치킨집",
    ],
    "CS100008": [
        "학교앞분식", "엄마손떡볶이", "종로분식", "해피분식", "맛있는분식", "모꼬지",
        "추억의국물떡볶이", "서울분식", "분식대장", "동네분식", "아이러브분식", "소풍분식",
    ],
    "CS100009": [
        "달빛포차", "별밤주점", "잔술집", "어디야", "골목집", "오늘한잔",
        "그대에게", "이층집", "청춘술집", "바람", "옥상야경", "한잔의추억",
    ],
    "CS100010": [
        "언힐커피", "모먼트커피", "그라운드커피", "해피빈", "카페숲", "릴리카페",
        "바리스타하우스", "달빛커피", "아로마빈", "커피숨", "잔잔한커피", "일상카페",
        "카페오드", "브루잉데이", "비니스커피", "포레스트커피", "모카포인트", "카페달",
    ],
}


def _generate_mock_stores(
    lat: float,
    lng: float,
    industry_code: str,
    count: int | None = None,
) -> list[dict[str, Any]]:
    """Mock 점포 데이터 생성 (SEMAS API 불가 시 폴백)."""
    rng = random.Random(hash(f"{lat:.4f}{lng:.4f}{industry_code}"))
    if count is None:
        count = rng.randint(15, 25)

    franchise_count = int(count * 0.3)
    indie_count = count - franchise_count

    brands = FRANCHISE_BRANDS.get(industry_code, FRANCHISE_BRANDS.get("CS100010", []))
    indie_names = _INDIE_NAMES.get(industry_code, _INDIE_NAMES["CS100010"])

    stores: list[dict[str, Any]] = []

    # 프랜차이즈 점포
    selected_brands = rng.sample(brands, min(franchise_count, len(brands)))
    for i, brand in enumerate(selected_brands):
        offset_lat = rng.uniform(-0.0027, 0.0027)  # ~300m
        offset_lng = rng.uniform(-0.0034, 0.0034)
        stores.append({
            "store_name": f"{brand} {rng.choice(['역삼점', '강남점', '본점', '직영점', '1호점', '2호점', '중앙점'])}",
            "category": SEMAS_INDUSTRY_MAP.get(industry_code, {}).get("keywords", ["카페"])[0],
            "address": "",
            "lat": round(lat + offset_lat, 7),
            "lng": round(lng + offset_lng, 7),
            "is_franchise": True,
            "place_url": None,
            "phone": None,
        })

    # 추가 프랜차이즈 (부족분)
    while len([s for s in stores if s["is_franchise"]]) < franchise_count:
        brand = rng.choice(brands)
        offset_lat = rng.uniform(-0.0027, 0.0027)
        offset_lng = rng.uniform(-0.0034, 0.0034)
        stores.append({
            "store_name": f"{brand} {rng.choice(['서초점', '역삼점', '신사점'])}",
            "category": SEMAS_INDUSTRY_MAP.get(industry_code, {}).get("keywords", ["카페"])[0],
            "address": "",
            "lat": round(lat + offset_lat, 7),
            "lng": round(lng + offset_lng, 7),
            "is_franchise": True,
            "place_url": None,
            "phone": None,
        })

    # 인디 점포
    selected_indie = rng.sample(indie_names, min(indie_count, len(indie_names)))
    for name in selected_indie:
        offset_lat = rng.uniform(-0.0027, 0.0027)
        offset_lng = rng.uniform(-0.0034, 0.0034)
        stores.append({
            "store_name": name,
            "category": SEMAS_INDUSTRY_MAP.get(industry_code, {}).get("keywords", ["카페"])[0],
            "address": "",
            "lat": round(lat + offset_lat, 7),
            "lng": round(lng + offset_lng, 7),
            "is_franchise": False,
            "place_url": None,
            "phone": None,
        })

    # 추가 인디 (부족분)
    while len(stores) < count:
        name = rng.choice(indie_names) + str(rng.randint(1, 9))
        offset_lat = rng.uniform(-0.0027, 0.0027)
        offset_lng = rng.uniform(-0.0034, 0.0034)
        stores.append({
            "store_name": name,
            "category": SEMAS_INDUSTRY_MAP.get(industry_code, {}).get("keywords", ["카페"])[0],
            "address": "",
            "lat": round(lat + offset_lat, 7),
            "lng": round(lng + offset_lng, 7),
            "is_franchise": False,
            "place_url": None,
            "phone": None,
        })

    return stores[:count]
