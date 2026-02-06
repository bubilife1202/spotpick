from dataclasses import dataclass
from typing import Any
import math


@dataclass
class LocationFeatures:
    population_density: float
    floating_population: float
    competitor_count: int
    competitor_density: float
    avg_rent_price: float

    nearby_subway: bool
    nearby_bus_stops: int

    residential_ratio: float
    commercial_ratio: float
    office_ratio: float


@dataclass
class StoreFeatures:
    size_category: str
    price_range: str
    has_delivery: bool
    has_takeout: bool

    menu_diversity: float
    avg_menu_price: float

    operating_hours: float
    weekend_operation: bool


class FeatureExtractor:
    EARTH_RADIUS_KM = 6371.0

    def __init__(self, category: str = "coffee"):
        self.category = category

    def extract_location_features(
        self,
        lat: float,
        lng: float,
        area_data: dict[str, Any],
        competitors: list[dict[str, Any]],
    ) -> LocationFeatures:
        nearby_competitors = self._count_nearby(lat, lng, competitors, radius_km=0.5)
        density = nearby_competitors / (math.pi * 0.5**2)

        return LocationFeatures(
            population_density=area_data.get("population_density", 0),
            floating_population=area_data.get("floating_population", 0),
            competitor_count=nearby_competitors,
            competitor_density=density,
            avg_rent_price=area_data.get("avg_rent_price", 0),
            nearby_subway=area_data.get("nearby_subway", False),
            nearby_bus_stops=area_data.get("nearby_bus_stops", 0),
            residential_ratio=area_data.get("residential_ratio", 0),
            commercial_ratio=area_data.get("commercial_ratio", 0),
            office_ratio=area_data.get("office_ratio", 0),
        )

    def extract_store_features(self, store_data: dict[str, Any]) -> StoreFeatures:
        menu_items = store_data.get("menu_items", [])
        prices = [m.get("price", 0) for m in menu_items if m.get("price")]

        return StoreFeatures(
            size_category=self._categorize_size(store_data.get("size_sqm")),
            price_range=self._categorize_price(prices),
            has_delivery=store_data.get("has_delivery", False),
            has_takeout=store_data.get("has_takeout", False),
            menu_diversity=len(set(m.get("category") for m in menu_items if m.get("category"))),
            avg_menu_price=sum(prices) / len(prices) if prices else 0,
            operating_hours=self._calculate_operating_hours(store_data.get("business_hours", {})),
            weekend_operation=self._has_weekend_operation(store_data.get("business_hours", {})),
        )

    def _count_nearby(
        self,
        lat: float,
        lng: float,
        locations: list[dict[str, Any]],
        radius_km: float,
    ) -> int:
        count = 0
        for loc in locations:
            loc_lat = loc.get("lat", 0)
            loc_lng = loc.get("lng", 0)
            if self._haversine_distance(lat, lng, loc_lat, loc_lng) <= radius_km:
                count += 1
        return count

    def _haversine_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return self.EARTH_RADIUS_KM * c

    def _categorize_size(self, size_sqm: float | None) -> str:
        if size_sqm is None:
            return "unknown"
        if size_sqm < 33:
            return "small"
        elif size_sqm < 66:
            return "medium"
        else:
            return "large"

    def _categorize_price(self, prices: list[float]) -> str:
        if not prices:
            return "unknown"
        avg = sum(prices) / len(prices)
        if avg < 4000:
            return "low"
        elif avg < 6000:
            return "medium"
        else:
            return "high"

    def _calculate_operating_hours(self, hours: dict[str, str]) -> float:
        total = 0
        for day, time_range in hours.items():
            if "-" in time_range:
                try:
                    start, end = time_range.split("-")
                    start_h = int(start.split(":")[0])
                    end_h = int(end.split(":")[0])
                    total += (end_h - start_h) if end_h > start_h else (24 - start_h + end_h)
                except (ValueError, IndexError):
                    pass
        return total / 7 if hours else 0

    def _has_weekend_operation(self, hours: dict[str, str]) -> bool:
        weekend_keys = ["토", "일", "sat", "sun", "saturday", "sunday"]
        return any(k.lower() in [wk.lower() for wk in weekend_keys] for k in hours.keys())
