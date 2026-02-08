"""
소상공인시장진흥공단 (SEMAS) 상권정보 API
https://www.data.go.kr/data/15083033/openapi.do
"""

from datetime import datetime
from typing import Any
from dataclasses import dataclass

from collectors.common.base import BaseCollector, CollectionResult
from collectors.common.rate_limiter import RateLimiter


@dataclass
class CommercialArea:
    id: str
    name: str
    type: str  # 골목상권, 발달상권, 전통시장, 관광특구
    coordinates: tuple[float, float]
    region_code: str
    industry_count: int


@dataclass
class BusinessStore:
    id: str
    name: str
    category_large: str
    category_medium: str
    category_small: str
    address: str
    road_address: str
    coordinates: tuple[float, float]
    commercial_area_id: str | None


class SemasCollector(BaseCollector):
    BASE_URL = "https://apis.data.go.kr/B553077/api/open/sdsc2"

    def __init__(self, api_key: str):
        super().__init__(name="semas", base_url=self.BASE_URL)
        self.api_key = api_key
        self.rate_limiter = RateLimiter(requests_per_second=5)

    async def collect(self, **params: Any) -> CollectionResult[BusinessStore]:
        collect_type = params.get("type", "stores")

        if collect_type == "stores":
            return await self._collect_stores(params)
        elif collect_type == "areas":
            return await self._collect_commercial_areas(params)
        else:
            raise ValueError(f"Unknown collection type: {collect_type}")

    async def _collect_stores(self, params: dict[str, Any]) -> CollectionResult[BusinessStore]:
        region_code = params.get("region_code", "11")  # Default: Seoul
        page_size = params.get("page_size", 1000)
        # sdsc2: storeListInDong(행정동코드 기반), storeListInArea(상권번호 기반)
        # region_code가 행정동코드이면 storeListInDong, 상권번호이면 storeListInArea
        query_type = params.get("query_type", "dong")  # "dong" or "area"
        endpoint = "storeListInDong" if query_type == "dong" else "storeListInArea"

        stores: list[BusinessStore] = []
        errors: list[str] = []
        page = 1

        while True:
            async with self.rate_limiter:
                try:
                    api_params: dict[str, Any] = {
                        "serviceKey": self.api_key,
                        "key": region_code,
                        "pageNo": page,
                        "numOfRows": page_size,
                        "type": "json",
                    }
                    # storeListInDong uses divId; storeListInArea does not
                    if query_type == "dong":
                        api_params["divId"] = "adongCd"

                    response = await self.fetch_json(
                        f"{self.BASE_URL}/{endpoint}",
                        params=api_params,
                    )

                    items = response.get("body", {}).get("items", [])
                    if not items:
                        break

                    for item in items:
                        store = self._parse_store(item)
                        if store:
                            stores.append(store)

                    total_count = response.get("body", {}).get("totalCount", 0)
                    if page * page_size >= total_count:
                        break

                    page += 1

                except Exception as e:
                    errors.append(f"Page {page}: {str(e)}")
                    break

        return CollectionResult(
            data=stores,
            source="semas_stores",
            collected_at=datetime.now(),
            total_count=len(stores) + len(errors),
            success_count=len(stores),
            error_count=len(errors),
            errors=errors,
        )

    async def _collect_commercial_areas(
        self, params: dict[str, Any]
    ) -> CollectionResult[CommercialArea]:
        # 상권 영역 데이터 수집 구현
        areas: list[CommercialArea] = []
        return CollectionResult(
            data=areas,
            source="semas_areas",
            collected_at=datetime.now(),
            total_count=0,
            success_count=0,
            error_count=0,
            errors=[],
        )

    def _parse_store(self, item: dict[str, Any]) -> BusinessStore | None:
        try:
            return BusinessStore(
                id=str(item.get("bizesId", "")),
                name=item.get("bizesNm", ""),
                category_large=item.get("indsLclsNm", ""),
                category_medium=item.get("indsMclsNm", ""),
                category_small=item.get("indsSclsNm", ""),
                address=item.get("lnoAdr", ""),
                road_address=item.get("rdnmAdr", ""),
                coordinates=(
                    float(item.get("lat", 0)),
                    float(item.get("lon", 0)),
                ),
                commercial_area_id=item.get("trdarCd"),
            )
        except (ValueError, TypeError):
            return None

    async def validate(self, data: Any) -> bool:
        if isinstance(data, BusinessStore):
            return bool(data.id and data.name and data.coordinates[0] != 0)
        return False
