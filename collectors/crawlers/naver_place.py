from datetime import datetime
from typing import Any
from dataclasses import dataclass, field
import json
import re

from collectors.common.base import BaseCollector, CollectionResult
from collectors.common.rate_limiter import RateLimiter


@dataclass
class NaverPlaceInfo:
    id: str
    name: str
    category: str
    address: str
    road_address: str
    coordinates: tuple[float, float]
    phone: str | None

    review_count: int
    review_score: float
    blog_review_count: int
    visitor_review_count: int

    business_hours: dict[str, str] = field(default_factory=dict)
    menu_items: list[dict[str, Any]] = field(default_factory=list)

    keywords: list[str] = field(default_factory=list)

    first_seen: datetime | None = None
    estimated_open_date: datetime | None = None


class NaverPlaceCrawler(BaseCollector):
    SEARCH_URL = "https://map.naver.com/v5/api/search"
    PLACE_URL = "https://map.naver.com/v5/api/sites/summary"

    def __init__(self):
        super().__init__(name="naver_place")
        self.rate_limiter = RateLimiter(
            requests_per_second=0.5,
            min_delay=2.0,
            max_delay=5.0,
        )

    async def collect(self, **params: Any) -> CollectionResult[NaverPlaceInfo]:
        query = params.get("query", "")
        region = params.get("region", "")
        max_results = params.get("max_results", 100)

        search_query = f"{region} {query}".strip()
        places: list[NaverPlaceInfo] = []
        errors: list[str] = []

        async with self.rate_limiter:
            try:
                search_results = await self._search_places(search_query, max_results)

                for result in search_results:
                    place_id = result.get("id")
                    if place_id:
                        async with self.rate_limiter:
                            try:
                                place_info = await self._get_place_detail(place_id)
                                if place_info:
                                    places.append(place_info)
                            except Exception as e:
                                errors.append(f"Place {place_id}: {str(e)}")

            except Exception as e:
                errors.append(f"Search error: {str(e)}")

        return CollectionResult(
            data=places,
            source="naver_place",
            collected_at=datetime.now(),
            total_count=len(places) + len(errors),
            success_count=len(places),
            error_count=len(errors),
            errors=errors,
        )

    async def _search_places(self, query: str, max_results: int) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        page = 1

        while len(results) < max_results:
            response = await self.fetch_json(
                self.SEARCH_URL,
                params={
                    "query": query,
                    "type": "all",
                    "page": page,
                    "displayCount": 20,
                },
            )

            place_list = response.get("result", {}).get("place", {}).get("list", [])
            if not place_list:
                break

            results.extend(place_list)
            page += 1

            if len(place_list) < 20:
                break

        return results[:max_results]

    async def _get_place_detail(self, place_id: str) -> NaverPlaceInfo | None:
        response = await self.fetch_json(
            f"{self.PLACE_URL}/{place_id}",
            params={"lang": "ko"},
        )

        return self._parse_place_detail(response)

    def _parse_place_detail(self, data: dict[str, Any]) -> NaverPlaceInfo | None:
        try:
            return NaverPlaceInfo(
                id=str(data.get("id", "")),
                name=data.get("name", ""),
                category=data.get("category", ""),
                address=data.get("address", ""),
                road_address=data.get("roadAddress", ""),
                coordinates=(
                    float(data.get("y", 0)),
                    float(data.get("x", 0)),
                ),
                phone=data.get("phone"),
                review_count=data.get("reviewCount", 0),
                review_score=float(data.get("reviewScore", 0)),
                blog_review_count=data.get("blogReviewCount", 0),
                visitor_review_count=data.get("visitorReviewCount", 0),
                business_hours=data.get("businessHours", {}),
                menu_items=data.get("menuInfo", {}).get("menuList", []),
                keywords=data.get("keywords", []),
            )
        except (ValueError, TypeError):
            return None

    async def validate(self, data: Any) -> bool:
        if isinstance(data, NaverPlaceInfo):
            return bool(data.id and data.name and data.coordinates[0] != 0)
        return False
