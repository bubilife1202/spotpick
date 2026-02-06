from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SuccessFactors:
    survival_score: float
    review_score: float
    growth_score: float
    stability_score: float

    weights: dict[str, float]

    @property
    def total_score(self) -> float:
        return (
            self.survival_score * self.weights.get("survival", 0.4)
            + self.review_score * self.weights.get("review", 0.3)
            + self.growth_score * self.weights.get("growth", 0.2)
            + self.stability_score * self.weights.get("stability", 0.1)
        )


@dataclass
class StoreData:
    store_id: str
    open_date: Optional[datetime]
    close_date: Optional[datetime]
    review_count: int
    avg_review_score: float
    review_history: list[tuple[datetime, int, float]]


class SuccessScorer:
    DEFAULT_WEIGHTS = {
        "survival": 0.4,
        "review": 0.3,
        "growth": 0.2,
        "stability": 0.1,
    }

    def __init__(self, weights: Optional[dict[str, float]] = None):
        self.weights = weights or self.DEFAULT_WEIGHTS

    def calculate_score(
        self, store: StoreData, reference_date: Optional[datetime] = None
    ) -> SuccessFactors:
        if reference_date is None:
            reference_date = datetime.now()

        survival = self._calculate_survival_score(store, reference_date)
        review = self._calculate_review_score(store)
        growth = self._calculate_growth_score(store)
        stability = self._calculate_stability_score(store)

        return SuccessFactors(
            survival_score=survival,
            review_score=review,
            growth_score=growth,
            stability_score=stability,
            weights=self.weights,
        )

    def _calculate_survival_score(self, store: StoreData, reference_date: datetime) -> float:
        if store.open_date is None:
            return 0.5

        if store.close_date:
            months = (store.close_date - store.open_date).days / 30
        else:
            months = (reference_date - store.open_date).days / 30

        if months >= 36:
            return 1.0
        elif months >= 24:
            return 0.8
        elif months >= 12:
            return 0.6
        elif months >= 6:
            return 0.4
        else:
            return 0.2

    def _calculate_review_score(self, store: StoreData) -> float:
        if store.review_count == 0:
            return 0.3

        score_component = min(store.avg_review_score / 5.0, 1.0)

        count_component = min(store.review_count / 500, 1.0)

        return score_component * 0.7 + count_component * 0.3

    def _calculate_growth_score(self, store: StoreData) -> float:
        if len(store.review_history) < 2:
            return 0.5

        sorted_history = sorted(store.review_history, key=lambda x: x[0])

        first_half = sorted_history[: len(sorted_history) // 2]
        second_half = sorted_history[len(sorted_history) // 2 :]

        first_avg = sum(h[1] for h in first_half) / len(first_half) if first_half else 0
        second_avg = sum(h[1] for h in second_half) / len(second_half) if second_half else 0

        if first_avg == 0:
            return 0.5

        growth_rate = (second_avg - first_avg) / first_avg

        if growth_rate > 0.5:
            return 1.0
        elif growth_rate > 0.2:
            return 0.8
        elif growth_rate > 0:
            return 0.6
        elif growth_rate > -0.2:
            return 0.4
        else:
            return 0.2

    def _calculate_stability_score(self, store: StoreData) -> float:
        if len(store.review_history) < 3:
            return 0.5

        scores = [h[2] for h in store.review_history if h[2] > 0]
        if not scores:
            return 0.5

        avg = sum(scores) / len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / len(scores)
        std_dev = variance**0.5

        if std_dev < 0.3:
            return 1.0
        elif std_dev < 0.5:
            return 0.8
        elif std_dev < 0.7:
            return 0.6
        elif std_dev < 1.0:
            return 0.4
        else:
            return 0.2
