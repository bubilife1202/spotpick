"""
카카오 로컬 API 연동 — 상권 주변 카페 검색
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


_instance: KakaoLocalService | None = None


def get_kakao_local_service() -> KakaoLocalService:
    global _instance
    if _instance is None:
        _instance = KakaoLocalService()
    return _instance
