"""
Transparent Scorecard Engine — percentile-based scoring across 5 categories.

Replaces _calculate_success_probability() (rule-based) and MLService (opaque ML).
Every score is explainable: raw_value → percentile → weighted contribution.
"""
from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "processed"

# Default category weights when no ML-derived weights file exists
DEFAULT_WEIGHTS: dict[str, dict[str, Any]] = {
    "매출력": {
        "weight": 0.25,
        "features": ["sales_per_store", "monthly_transactions", "avg_ticket", "monthly_sales"],
    },
    "성장성": {
        "weight": 0.20,
        "features": ["sales_growth_rate", "new_stores_ratio", "new_stores", "change_indicator_score"],
    },
    "경쟁환경": {
        "weight": 0.20,
        "features": ["store_count", "closed_ratio", "franchise_ratio", "closed_stores"],
    },
    "입지여건": {
        "weight": 0.20,
        "features": ["foot_traffic_total", "worker_total", "transit_raw", "facility_score", "facility_subway", "resident_total"],
    },
    "안정성": {
        "weight": 0.15,
        "features": ["survival_rate", "avg_operation_months", "weekday_ratio"],
    },
}

CHANGE_CODE_SCORE = {"HH": 1.0, "HL": 0.75, "LH": 0.25, "LL": 0.0}

# Features where lower is better (inverted percentile)
LOWER_IS_BETTER = {"store_count", "closed_ratio", "franchise_ratio", "closed_stores"}

# Feature labels (Korean)
FEATURE_LABELS: dict[str, str] = {
    "sales_per_store": "점포당 월매출",
    "monthly_transactions": "월 거래수",
    "avg_ticket": "평균 객단가",
    "monthly_sales": "월 매출총액",
    "sales_growth_rate": "매출 성장률",
    "new_stores_ratio": "신규 점포 비율",
    "new_stores": "신규 점포수",
    "change_indicator_score": "상권변화 지표",
    "store_count": "점포수(경쟁)",
    "closed_ratio": "폐업률",
    "franchise_ratio": "프랜차이즈 비율",
    "closed_stores": "폐업 점포수",
    "foot_traffic_total": "유동인구",
    "worker_total": "직장인구",
    "transit_raw": "대중교통 접근성",
    "facility_score": "시설 점수",
    "facility_subway": "지하철역 수",
    "resident_total": "상주인구",
    "survival_rate": "생존율",
    "avg_operation_months": "평균 운영개월",
    "weekday_ratio": "주중 매출비율",
}


def _load_weights(industry_code: str) -> dict[str, dict[str, Any]]:
    """Load ML-derived weights or fall back to defaults."""
    weights_path = DATA_DIR / f"{industry_code}_scorecard_weights.json"
    if weights_path.exists():
        try:
            with open(weights_path, encoding="utf-8") as f:
                data = json.load(f)
            return data.get("categories", DEFAULT_WEIGHTS)
        except Exception:
            pass
    return DEFAULT_WEIGHTS


def _extract_feature_value(d: dict[str, Any], feature: str) -> float:
    """Extract a single feature value from a district record."""
    sc = max(1, d.get("store_count", 1))
    ms = d.get("monthly_sales", 0)
    tx = d.get("monthly_transactions", 0)

    if feature == "sales_per_store":
        return ms / sc
    elif feature == "avg_ticket":
        tx_ps = tx / sc
        return (ms / sc) / max(1, tx_ps) if tx_ps > 0 else 0
    elif feature == "sales_growth_rate":
        trends = d.get("yearly_trends", [])
        if isinstance(trends, list) and len(trends) >= 4:
            try:
                recent = sum(t.get("sales", 0) for t in trends[-2:])
                earlier = sum(t.get("sales", 0) for t in trends[-4:-2])
                if earlier > 0:
                    return (recent - earlier) / earlier
            except Exception:
                pass
        return 0.0
    elif feature == "new_stores_ratio":
        return d.get("new_stores", 0) / sc if sc > 0 else 0
    elif feature == "closed_ratio":
        return d.get("closed_stores", 0) / sc if sc > 0 else 0
    elif feature == "franchise_ratio":
        return d.get("franchise_stores", 0) / sc if sc > 0 else 0
    elif feature == "change_indicator_score":
        return CHANGE_CODE_SCORE.get(d.get("change_indicator_code", ""), 0.5)
    else:
        return float(d.get(feature, 0))


class ScorecardService:
    """Transparent, percentile-based scoring for districts."""

    def __init__(self, industry_code: str = "CS100010", districts: list[dict[str, Any]] | None = None):
        self.industry_code = industry_code
        self.weights = _load_weights(industry_code)
        self._districts = districts or []
        self._percentile_arrays: dict[str, list[float]] = {}
        if self._districts:
            self._precompute_percentiles()

    def set_districts(self, districts: list[dict[str, Any]]) -> None:
        """Set districts and recompute percentiles."""
        self._districts = districts
        self._precompute_percentiles()

    def _precompute_percentiles(self) -> None:
        """Pre-compute sorted arrays for percentile lookup."""
        all_features: set[str] = set()
        for cat in self.weights.values():
            for f in cat.get("features", []):
                all_features.add(f)

        for feature in all_features:
            values = sorted(_extract_feature_value(d, feature) for d in self._districts)
            self._percentile_arrays[feature] = values

    def _percentile_of(self, feature: str, value: float) -> float:
        """Compute percentile rank (0-1) of a value within the distribution."""
        arr = self._percentile_arrays.get(feature, [])
        if not arr:
            return 0.5
        n = len(arr)
        rank = sum(1 for v in arr if v <= value)
        pctile = rank / max(1, n)
        # Invert for "lower is better" features
        if feature in LOWER_IS_BETTER:
            pctile = 1.0 - pctile
        return round(pctile, 4)

    def score_district(self, district: dict[str, Any]) -> dict[str, Any]:
        """Score a single district and return full breakdown."""
        categories = []
        total_score = 0.0

        for cat_name, cat_info in self.weights.items():
            cat_weight = cat_info.get("weight", 0.2)
            features = cat_info.get("features", [])
            items = []
            cat_raw_score = 0.0

            for feature in features:
                raw_value = _extract_feature_value(district, feature)
                pctile = self._percentile_of(feature, raw_value)
                feat_weight = 1.0 / max(1, len(features))  # equal weight within category
                weighted = pctile * feat_weight
                cat_raw_score += weighted

                items.append({
                    "feature": feature,
                    "label": FEATURE_LABELS.get(feature, feature),
                    "raw_value": round(raw_value, 2) if isinstance(raw_value, float) else raw_value,
                    "percentile": pctile,
                    "weight": round(feat_weight, 4),
                    "weighted_score": round(weighted * 100, 1),
                })

            cat_score = cat_raw_score * 100  # 0-100 scale
            categories.append({
                "name": cat_name,
                "weight": cat_weight,
                "score": round(cat_score, 1),
                "items": items,
            })
            total_score += cat_weight * cat_score

        total_score = round(max(0, min(100, total_score)), 1)

        # Compute rank and percentile among all districts
        rank = 1
        n = len(self._districts)
        for d in self._districts:
            other_score = self._quick_score(d)
            if other_score > total_score:
                rank += 1

        percentile = round((1.0 - (rank - 1) / max(1, n)) * 100, 1)

        return {
            "district_code": district.get("district_code", ""),
            "district_name": district.get("district_name", ""),
            "total_score": total_score,
            "rank": rank,
            "percentile": percentile,
            "categories": categories,
        }

    def _quick_score(self, district: dict[str, Any]) -> float:
        """Fast total score (no breakdown) for ranking."""
        total = 0.0
        for cat_name, cat_info in self.weights.items():
            cat_weight = cat_info.get("weight", 0.2)
            features = cat_info.get("features", [])
            cat_score = 0.0
            n_feats = max(1, len(features))
            for feature in features:
                raw = _extract_feature_value(district, feature)
                pctile = self._percentile_of(feature, raw)
                cat_score += pctile / n_feats
            total += cat_weight * cat_score * 100
        return round(total, 1)

    def rank_all(self, limit: int = 0, offset: int = 0) -> list[dict[str, Any]]:
        """Rank all districts by total score."""
        scored = []
        for d in self._districts:
            score = self._quick_score(d)
            scored.append((score, d))
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        n = len(scored)
        start = offset
        end = (offset + limit) if limit > 0 else n

        for rank_idx, (score, d) in enumerate(scored[start:end], start + 1):
            percentile = round((1.0 - (rank_idx - 1) / max(1, n)) * 100, 1)
            results.append({
                "district_code": d.get("district_code", ""),
                "district_name": d.get("district_name", ""),
                "district_type": d.get("district_type", ""),
                "total_score": score,
                "rank": rank_idx,
                "percentile": percentile,
                "survival_rate": d.get("survival_rate", 0),
                "monthly_sales": d.get("monthly_sales", 0),
                "store_count": d.get("store_count", 0),
            })
        return results


# ─── Registry ──────────────────────────────────────────────────────────────
_registry: dict[str, ScorecardService] = {}


def get_scorecard_service(industry_code: str = "CS100010") -> ScorecardService:
    """Get or create a ScorecardService for an industry."""
    if industry_code not in _registry:
        _registry[industry_code] = ScorecardService(industry_code)
    return _registry[industry_code]
