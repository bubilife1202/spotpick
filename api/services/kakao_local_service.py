"""
카카오 로컬 API 연동 — 상권 주변 장소 검색 (카페, 음식점 등)
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, TypedDict

import httpx

from dotenv import load_dotenv  # type: ignore[import-not-found]

_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")

KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"
KAKAO_CATEGORY_URL = "https://dapi.kakao.com/v2/local/search/category.json"

logger = logging.getLogger(__name__)


class NearbyStore(TypedDict):
    id: str
    name: str
    category: str
    address: str
    road_address: str
    phone: str
    x: float
    y: float
    place_url: str
    distance: int


class NearbyStoresResult(TypedDict):
    stores: list[NearbyStore]
    total_count: int
    query: str


class KakaoLocalService:
    def __init__(self) -> None:
        self._api_key = KAKAO_REST_API_KEY
        if not self._api_key:
            logger.warning("KAKAO_REST_API_KEY not set")

    @property
    def available(self) -> bool:
        return bool(self._api_key)

    async def search_nearby_cafes(
        self,
        query: str,
        x: float | None = None,
        y: float | None = None,
        radius: int = 1000,
        size: int = 15,
        page: int = 1,
    ) -> NearbyStoresResult:
        if not self._api_key:
            return NearbyStoresResult(stores=[], total_count=0, query=query)

        params: dict[str, Any] = {
            "query": f"카페 {query}",
            "category_group_code": "CE7",
            "size": min(size, 15),
            "page": page,
        }
        if x is not None and y is not None:
            params["x"] = str(x)
            params["y"] = str(y)
            params["radius"] = radius
            params["sort"] = "distance"

        headers = {"Authorization": f"KakaoAK {self._api_key}"}

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(KAKAO_KEYWORD_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        documents: list[dict[str, Any]] = data.get("documents", [])
        meta = data.get("meta", {})

        stores: list[NearbyStore] = []
        for doc in documents:
            stores.append(
                NearbyStore(
                    id=doc.get("id", ""),
                    name=doc.get("place_name", ""),
                    category=doc.get("category_name", ""),
                    address=doc.get("address_name", ""),
                    road_address=doc.get("road_address_name", ""),
                    phone=doc.get("phone", ""),
                    x=float(doc.get("x", 0)),
                    y=float(doc.get("y", 0)),
                    place_url=doc.get("place_url", ""),
                    distance=int(doc.get("distance", 0)) if doc.get("distance") else 0,
                )
            )

        return NearbyStoresResult(
            stores=stores,
            total_count=meta.get("total_count", len(stores)),
            query=query,
        )

    async def search_cafes_by_category(
        self,
        x: float,
        y: float,
        radius: int = 1000,
        size: int = 15,
        page: int = 1,
    ) -> NearbyStoresResult:
        if not self._api_key:
            return NearbyStoresResult(stores=[], total_count=0, query="")

        params: dict[str, Any] = {
            "category_group_code": "CE7",
            "x": str(x),
            "y": str(y),
            "radius": radius,
            "size": min(size, 15),
            "page": page,
            "sort": "distance",
        }
        headers = {"Authorization": f"KakaoAK {self._api_key}"}

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(KAKAO_CATEGORY_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        documents: list[dict[str, Any]] = data.get("documents", [])
        meta = data.get("meta", {})

        stores: list[NearbyStore] = []
        for doc in documents:
            stores.append(
                NearbyStore(
                    id=doc.get("id", ""),
                    name=doc.get("place_name", ""),
                    category=doc.get("category_name", ""),
                    address=doc.get("address_name", ""),
                    road_address=doc.get("road_address_name", ""),
                    phone=doc.get("phone", ""),
                    x=float(doc.get("x", 0)),
                    y=float(doc.get("y", 0)),
                    place_url=doc.get("place_url", ""),
                    distance=int(doc.get("distance", 0)) if doc.get("distance") else 0,
                )
            )

        return NearbyStoresResult(
            stores=stores,
            total_count=meta.get("total_count", len(stores)),
            query=f"CE7@{x},{y}",
        )


    async def search_nearby_parking(
        self,
        x: float,
        y: float,
        radius: int = 500,
        size: int = 15,
    ) -> NearbyStoresResult:
        if not self._api_key:
            return NearbyStoresResult(stores=[], total_count=0, query="")

        params: dict[str, Any] = {
            "category_group_code": "PK6",
            "x": str(x),
            "y": str(y),
            "radius": radius,
            "size": min(size, 15),
            "sort": "distance",
        }
        headers = {"Authorization": f"KakaoAK {self._api_key}"}

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(KAKAO_CATEGORY_URL, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        documents: list[dict[str, Any]] = data.get("documents", [])
        meta = data.get("meta", {})

        stores: list[NearbyStore] = []
        for doc in documents:
            stores.append(
                NearbyStore(
                    id=doc.get("id", ""),
                    name=doc.get("place_name", ""),
                    category=doc.get("category_name", ""),
                    address=doc.get("address_name", ""),
                    road_address=doc.get("road_address_name", ""),
                    phone=doc.get("phone", ""),
                    x=float(doc.get("x", 0)),
                    y=float(doc.get("y", 0)),
                    place_url=doc.get("place_url", ""),
                    distance=int(doc.get("distance", 0)) if doc.get("distance") else 0,
                )
            )

        return NearbyStoresResult(
            stores=stores,
            total_count=meta.get("total_count", len(stores)),
            query=f"PK6@{x},{y}",
        )


# ---------------------------------------------------------------------------
# 업종코드 -> 카카오 검색 키워드/카테고리 매핑
# ---------------------------------------------------------------------------

INDUSTRY_KAKAO_MAP: dict[str, dict[str, str]] = {
    "CS100001": {"keyword": "한식", "category_group": "FD6"},
    "CS100002": {"keyword": "중식", "category_group": "FD6"},
    "CS100003": {"keyword": "일식", "category_group": "FD6"},
    "CS100004": {"keyword": "양식", "category_group": "FD6"},
    "CS100005": {"keyword": "베이커리", "category_group": "FD6"},
    "CS100006": {"keyword": "패스트푸드", "category_group": "FD6"},
    "CS100007": {"keyword": "치킨", "category_group": "FD6"},
    "CS100008": {"keyword": "분식", "category_group": "FD6"},
    "CS100009": {"keyword": "호프", "category_group": "FD6"},
    "CS100010": {"keyword": "카페", "category_group": "CE7"},
}


class PlaceResult(TypedDict):
    place_name: str
    category_name: str
    phone: str
    address: str
    road_address: str
    lat: float
    lng: float
    place_url: str
    distance: int


# ---------------------------------------------------------------------------
# search_places_in_area - 범용 장소 검색
# ---------------------------------------------------------------------------

async def search_places_in_area(
    lat: float,
    lng: float,
    keyword: str = "",
    radius: int = 500,
    category_group: str = "",
    industry_code: str | None = None,
    size: int = 15,
    max_pages: int = 3,
) -> list[PlaceResult]:
    """
    카카오 로컬 키워드 검색으로 주변 장소를 반환.

    업종코드(industry_code)가 지정되면 매핑된 keyword/category_group을 사용.
    max_pages 만큼 페이징하여 최대 size*max_pages 개 결과를 수집.

    Returns:
        list of PlaceResult dicts
    """
    svc = get_kakao_local_service()
    if not svc.available:
        return []

    # 업종코드 매핑
    if industry_code and not keyword:
        mapping = INDUSTRY_KAKAO_MAP.get(industry_code, {})
        keyword = mapping.get("keyword", "카페")
        if not category_group:
            category_group = mapping.get("category_group", "")

    if not keyword:
        keyword = "카페"

    all_places: list[PlaceResult] = []
    headers = {"Authorization": f"KakaoAK {svc._api_key}"}

    for page in range(1, max_pages + 1):
        params: dict[str, Any] = {
            "query": keyword,
            "x": str(lng),
            "y": str(lat),
            "radius": radius,
            "size": min(size, 15),
            "page": page,
            "sort": "distance",
        }
        if category_group:
            params["category_group_code"] = category_group

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(KAKAO_KEYWORD_URL, params=params, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error("카카오 로컬 검색 실패: %s", e)
            break

        documents = data.get("documents", [])
        meta = data.get("meta", {})

        for doc in documents:
            all_places.append(
                PlaceResult(
                    place_name=doc.get("place_name", ""),
                    category_name=doc.get("category_name", ""),
                    phone=doc.get("phone", ""),
                    address=doc.get("address_name", ""),
                    road_address=doc.get("road_address_name", ""),
                    lat=float(doc.get("y", 0)),
                    lng=float(doc.get("x", 0)),
                    place_url=doc.get("place_url", ""),
                    distance=int(doc.get("distance", 0)) if doc.get("distance") else 0,
                )
            )

        if meta.get("is_end", True):
            break

    return all_places


_instance: KakaoLocalService | None = None


def get_kakao_local_service() -> KakaoLocalService:
    global _instance
    if _instance is None:
        _instance = KakaoLocalService()
    return _instance
