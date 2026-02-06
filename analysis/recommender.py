from dataclasses import dataclass
from typing import Optional

from .features.extractor import FeatureExtractor, LocationFeatures
from .models.success_predictor import SuccessPredictor, Prediction


@dataclass
class LocationRecommendation:
    rank: int
    lat: float
    lng: float
    address: str
    prediction: Prediction
    estimated_monthly_rent: int
    nearby_successful_stores: list[dict]
    key_success_factors: list[str]


@dataclass
class RecommendationRequest:
    category: str
    budget_min: int
    budget_max: int
    preferred_region: Optional[str] = None
    store_size: Optional[str] = None
    has_delivery: bool = False
    has_takeout: bool = True


class LocationRecommender:
    def __init__(self):
        self.feature_extractor = FeatureExtractor()
        self.predictor = SuccessPredictor()

    async def get_recommendations(
        self,
        request: RecommendationRequest,
        candidate_locations: list[dict],
        area_data_map: dict[str, dict],
        competitor_map: dict[str, list[dict]],
        top_n: int = 10,
    ) -> list[LocationRecommendation]:
        scored_locations: list[tuple[dict, Prediction, LocationFeatures]] = []

        for loc in candidate_locations:
            lat, lng = loc["lat"], loc["lng"]
            region_code = loc.get("region_code", "")

            area_data = area_data_map.get(region_code, {})
            competitors = competitor_map.get(region_code, [])

            rent = area_data.get("avg_rent_price", 0)
            if rent < request.budget_min or rent > request.budget_max:
                continue

            location_features = self.feature_extractor.extract_location_features(
                lat=lat,
                lng=lng,
                area_data=area_data,
                competitors=competitors,
            )

            prediction = self.predictor.predict(location_features)
            scored_locations.append((loc, prediction, location_features))

        scored_locations.sort(key=lambda x: x[1].success_probability, reverse=True)

        recommendations = []
        for rank, (loc, prediction, features) in enumerate(scored_locations[:top_n], 1):
            key_factors = self._extract_key_factors(features, prediction)

            recommendations.append(
                LocationRecommendation(
                    rank=rank,
                    lat=loc["lat"],
                    lng=loc["lng"],
                    address=loc.get("address", ""),
                    prediction=prediction,
                    estimated_monthly_rent=int(loc.get("rent", 0)),
                    nearby_successful_stores=[],
                    key_success_factors=key_factors,
                )
            )

        return recommendations

    def _extract_key_factors(
        self,
        features: LocationFeatures,
        prediction: Prediction,
    ) -> list[str]:
        factors = []

        if features.floating_population > 10000:
            factors.append("높은 유동인구")
        if features.nearby_subway:
            factors.append("지하철역 인접")
        if features.competitor_density < 5:
            factors.append("낮은 경쟁 밀도")
        if features.office_ratio > 0.3:
            factors.append("오피스 밀집 지역")

        return factors[:5]
