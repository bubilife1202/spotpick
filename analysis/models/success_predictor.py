from dataclasses import dataclass
from typing import Any, Optional
import pickle
from pathlib import Path

from analysis.features.extractor import LocationFeatures, StoreFeatures


@dataclass
class Prediction:
    success_probability: float
    confidence: float
    risk_factors: list[str]
    recommendations: list[str]
    similar_successful_stores: list[str]


class SuccessPredictor:
    MODEL_PATH = Path("models/success_predictor.pkl")

    def __init__(self):
        self.model: Any = None
        self.feature_importance: dict[str, float] = {}

    def load_model(self, path: Optional[Path] = None) -> bool:
        model_path = path or self.MODEL_PATH
        if not model_path.exists():
            return False

        with open(model_path, "rb") as f:
            data = pickle.load(f)
            self.model = data["model"]
            self.feature_importance = data.get("feature_importance", {})
        return True

    def save_model(self, path: Optional[Path] = None) -> None:
        model_path = path or self.MODEL_PATH
        model_path.parent.mkdir(parents=True, exist_ok=True)

        with open(model_path, "wb") as f:
            pickle.dump(
                {
                    "model": self.model,
                    "feature_importance": self.feature_importance,
                },
                f,
            )

    def predict(
        self,
        location_features: LocationFeatures,
        store_features: Optional[StoreFeatures] = None,
    ) -> Prediction:
        if self.model is None:
            return self._rule_based_prediction(location_features, store_features)

        features = self._prepare_features(location_features, store_features)
        probability = self.model.predict_proba([features])[0][1]

        risk_factors = self._identify_risks(location_features, store_features)
        recommendations = self._generate_recommendations(
            location_features, store_features, risk_factors
        )

        return Prediction(
            success_probability=probability,
            confidence=0.7,
            risk_factors=risk_factors,
            recommendations=recommendations,
            similar_successful_stores=[],
        )

    def _rule_based_prediction(
        self,
        location: LocationFeatures,
        store: Optional[StoreFeatures],
    ) -> Prediction:
        score = 0.5
        risk_factors = []
        recommendations = []

        if location.competitor_density > 10:
            score -= 0.1
            risk_factors.append("높은 경쟁 밀도 (반경 500m 내 경쟁업체 과다)")

        if location.floating_population > 10000:
            score += 0.1
        elif location.floating_population < 3000:
            score -= 0.1
            risk_factors.append("낮은 유동인구")

        if location.avg_rent_price > 5000000:
            score -= 0.05
            risk_factors.append("높은 임대료")
            recommendations.append("인근 저렴한 위치 검토 권장")

        if location.nearby_subway:
            score += 0.05

        if store:
            if store.has_takeout:
                score += 0.05
                recommendations.append("테이크아웃 비중 확대 시 수익성 개선 가능")

            if store.operating_hours < 10:
                recommendations.append("영업시간 확대 검토")

        score = max(0.1, min(0.9, score))

        if not recommendations:
            if score > 0.6:
                recommendations.append("현재 조건 양호. 차별화 전략에 집중 권장")
            else:
                recommendations.append("위치 재검토 또는 운영 전략 수정 필요")

        return Prediction(
            success_probability=score,
            confidence=0.5,
            risk_factors=risk_factors,
            recommendations=recommendations,
            similar_successful_stores=[],
        )

    def _prepare_features(
        self,
        location: LocationFeatures,
        store: Optional[StoreFeatures],
    ) -> list[float]:
        features = [
            location.population_density,
            location.floating_population,
            location.competitor_count,
            location.competitor_density,
            location.avg_rent_price,
            float(location.nearby_subway),
            location.nearby_bus_stops,
            location.residential_ratio,
            location.commercial_ratio,
            location.office_ratio,
        ]

        if store:
            size_map = {"small": 0, "medium": 1, "large": 2, "unknown": 1}
            price_map = {"low": 0, "medium": 1, "high": 2, "unknown": 1}

            features.extend(
                [
                    size_map.get(store.size_category, 1),
                    price_map.get(store.price_range, 1),
                    float(store.has_delivery),
                    float(store.has_takeout),
                    store.menu_diversity,
                    store.avg_menu_price,
                    store.operating_hours,
                    float(store.weekend_operation),
                ]
            )

        return features

    def _identify_risks(
        self,
        location: LocationFeatures,
        store: Optional[StoreFeatures],
    ) -> list[str]:
        risks = []

        if location.competitor_density > 10:
            risks.append("높은 경쟁 밀도")
        if location.floating_population < 3000:
            risks.append("낮은 유동인구")
        if location.avg_rent_price > 5000000:
            risks.append("높은 임대료 부담")

        return risks

    def _generate_recommendations(
        self,
        location: LocationFeatures,
        store: Optional[StoreFeatures],
        risks: list[str],
    ) -> list[str]:
        recs = []

        if "높은 경쟁 밀도" in risks:
            recs.append("차별화된 메뉴/서비스로 경쟁력 확보 필요")
        if "낮은 유동인구" in risks:
            recs.append("배달/온라인 채널 강화 권장")
        if "높은 임대료 부담" in risks:
            recs.append("테이크아웃 특화로 좌석 수 최소화 검토")

        return recs
