"""
통계청 KOSIS API - 인구/가구/소득 통계
https://kosis.kr/openapi/
"""

from datetime import datetime
from typing import Any
from dataclasses import dataclass

from collectors.common.base import BaseCollector, CollectionResult
from collectors.common.rate_limiter import RateLimiter


@dataclass
class PopulationStats:
    region_code: str
    region_name: str
    year: int
    total_population: int
    male_population: int
    female_population: int
    households: int
    avg_household_size: float


@dataclass
class IncomeStats:
    region_code: str
    region_name: str
    year: int
    avg_income: int
    median_income: int


class KosisCollector(BaseCollector):
    BASE_URL = "https://kosis.kr/openapi/Param/statisticsParameterData.do"

    def __init__(self, api_key: str):
        super().__init__(name="kosis", base_url=self.BASE_URL)
        self.api_key = api_key
        self.rate_limiter = RateLimiter(requests_per_second=2)

    async def collect(self, **params: Any) -> CollectionResult[PopulationStats]:
        stat_type = params.get("type", "population")
        year = params.get("year", datetime.now().year - 1)

        if stat_type == "population":
            return await self._collect_population(year)
        elif stat_type == "income":
            return await self._collect_income(year)
        else:
            raise ValueError(f"Unknown stat type: {stat_type}")

    async def _collect_population(self, year: int) -> CollectionResult[PopulationStats]:
        stats: list[PopulationStats] = []
        errors: list[str] = []

        async with self.rate_limiter:
            try:
                response = await self.fetch_json(
                    self.BASE_URL,
                    params={
                        "method": "getList",
                        "apiKey": self.api_key,
                        "format": "json",
                        "jsonVD": "Y",
                        "orgId": "101",
                        "tblId": "DT_1B040A3",  # 주민등록인구현황
                        "prdSe": "Y",
                        "startPrdDe": str(year),
                        "endPrdDe": str(year),
                    },
                )

                for item in response:
                    stat = self._parse_population(item, year)
                    if stat:
                        stats.append(stat)

            except Exception as e:
                errors.append(str(e))

        return CollectionResult(
            data=stats,
            source="kosis_population",
            collected_at=datetime.now(),
            total_count=len(stats),
            success_count=len(stats),
            error_count=len(errors),
            errors=errors,
        )

    async def _collect_income(self, year: int) -> CollectionResult[IncomeStats]:
        # 소득 통계 수집 구현
        return CollectionResult(
            data=[],
            source="kosis_income",
            collected_at=datetime.now(),
            total_count=0,
            success_count=0,
            error_count=0,
            errors=[],
        )

    def _parse_population(self, item: dict[str, Any], year: int) -> PopulationStats | None:
        try:
            return PopulationStats(
                region_code=item.get("C1", ""),
                region_name=item.get("C1_NM", ""),
                year=year,
                total_population=int(item.get("DT", 0)),
                male_population=0,
                female_population=0,
                households=0,
                avg_household_size=0.0,
            )
        except (ValueError, TypeError):
            return None

    async def validate(self, data: Any) -> bool:
        if isinstance(data, PopulationStats):
            return data.total_population > 0
        return False
