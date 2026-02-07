#!/usr/bin/env python3
"""
Offline scorecard weight discovery script.

Reads {industry_code}_districts.json, computes a Composite Success Index,
trains GradientBoosting to discover feature importances, and groups them
into 5 scoring categories.

Usage:
    python scripts/build_scorecard_weights.py --industry CS100010
    python scripts/build_scorecard_weights.py --all
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "processed"
INDUSTRIES_DIR = ROOT / "data" / "industries"


# ─── Feature → Category mapping ───────────────────────────────────────────
CATEGORY_FEATURES: dict[str, list[str]] = {
    "매출력": [
        "sales_per_store",
        "monthly_transactions",
        "avg_ticket",
        "monthly_sales",
    ],
    "성장성": [
        "sales_growth_rate",
        "new_stores_ratio",
        "new_stores",
        "change_indicator_score",
    ],
    "경쟁환경": [
        "store_count",
        "closed_ratio",
        "franchise_ratio",
        "closed_stores",
    ],
    "입지여건": [
        "foot_traffic_total",
        "worker_total",
        "transit_raw",
        "facility_score",
        "facility_subway",
        "resident_total",
    ],
    "안정성": [
        "survival_rate",
        "avg_operation_months",
        "weekday_ratio",
    ],
}

ALL_FEATURES = [f for feats in CATEGORY_FEATURES.values() for f in feats]

CHANGE_CODE_SCORE = {"HH": 1.0, "HL": 0.75, "LH": 0.25, "LL": 0.0}


def load_districts(industry_code: str) -> list[dict]:
    """Load districts JSON for a given industry code."""
    # Try industry-specific file first
    path = DATA_DIR / f"{industry_code}_districts.json"
    if not path.exists() and industry_code == "CS100010":
        path = DATA_DIR / "coffee_districts.json"
    if not path.exists():
        print(f"[SKIP] {path} not found")
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def extract_features(d: dict) -> dict[str, float]:
    """Extract numeric features from a district record."""
    sc = max(1, d.get("store_count", 1))
    ms = d.get("monthly_sales", 0)
    tx = d.get("monthly_transactions", 0)
    sps = ms / sc
    tx_ps = tx / sc
    avg_ticket = sps / max(1, tx_ps) if tx_ps > 0 else 0

    # Growth: use yearly_trends if available
    trends = d.get("yearly_trends", [])
    growth = 0.0
    if isinstance(trends, list) and len(trends) >= 4:
        try:
            recent = sum(t.get("sales", 0) for t in trends[-2:])
            earlier = sum(t.get("sales", 0) for t in trends[-4:-2])
            if earlier > 0:
                growth = (recent - earlier) / earlier
        except Exception:
            growth = 0.0

    new_stores = d.get("new_stores", 0)
    closed_stores = d.get("closed_stores", 0)
    change_code = d.get("change_indicator_code", "")

    return {
        "sales_per_store": sps,
        "monthly_transactions": tx,
        "avg_ticket": avg_ticket,
        "monthly_sales": ms,
        "sales_growth_rate": growth,
        "new_stores_ratio": new_stores / sc if sc > 0 else 0,
        "new_stores": new_stores,
        "change_indicator_score": CHANGE_CODE_SCORE.get(change_code, 0.5),
        "store_count": d.get("store_count", 0),
        "closed_ratio": closed_stores / sc if sc > 0 else 0,
        "franchise_ratio": d.get("franchise_stores", 0) / sc if sc > 0 else 0,
        "closed_stores": closed_stores,
        "foot_traffic_total": d.get("foot_traffic_total", 0),
        "worker_total": d.get("worker_total", 0),
        "transit_raw": d.get("transit_raw", 0),
        "facility_score": d.get("facility_score", 0),
        "facility_subway": d.get("facility_subway", 0),
        "resident_total": d.get("resident_total", 0),
        "survival_rate": d.get("survival_rate", 0),
        "avg_operation_months": d.get("avg_operation_months", 0),
        "weekday_ratio": d.get("weekday_ratio", 0),
    }


def compute_composite_index(districts: list[dict]) -> list[float]:
    """
    Composite Success Index =
      sales_per_store_pctile × 0.40
    + survival_rate_pctile × 0.25
    + sales_growth_pctile × 0.20
    + competition_stability_pctile × 0.15
    """
    n = len(districts)
    if n == 0:
        return []

    # Extract raw values
    sps_vals = []
    surv_vals = []
    growth_vals = []
    stability_vals = []

    for d in districts:
        sc = max(1, d.get("store_count", 1))
        sps = d.get("monthly_sales", 0) / sc
        sps_vals.append(sps)
        surv_vals.append(d.get("survival_rate", 0))

        trends = d.get("yearly_trends", [])
        growth = 0.0
        if isinstance(trends, list) and len(trends) >= 4:
            try:
                recent = sum(t.get("sales", 0) for t in trends[-2:])
                earlier = sum(t.get("sales", 0) for t in trends[-4:-2])
                if earlier > 0:
                    growth = (recent - earlier) / earlier
            except Exception:
                pass
        growth_vals.append(growth)

        closed = d.get("closed_stores", 0)
        stability = 1.0 - (closed / max(1, sc))
        change_code = d.get("change_indicator_code", "")
        stability += CHANGE_CODE_SCORE.get(change_code, 0.5) * 0.2
        stability_vals.append(stability)

    def to_percentile(vals: list[float]) -> list[float]:
        sorted_vals = sorted(vals)
        result = []
        for v in vals:
            rank = sum(1 for sv in sorted_vals if sv <= v)
            result.append(rank / max(1, len(sorted_vals)))
        return result

    sps_pctile = to_percentile(sps_vals)
    surv_pctile = to_percentile(surv_vals)
    growth_pctile = to_percentile(growth_vals)
    stab_pctile = to_percentile(stability_vals)

    composite = []
    for i in range(n):
        score = (
            sps_pctile[i] * 0.40
            + surv_pctile[i] * 0.25
            + growth_pctile[i] * 0.20
            + stab_pctile[i] * 0.15
        )
        composite.append(score)

    return composite


def build_weights(industry_code: str) -> dict | None:
    """Build scorecard weights for a single industry."""
    districts = load_districts(industry_code)
    if not districts:
        return None

    print(f"[{industry_code}] Loaded {len(districts)} districts")

    # Compute target
    composite = compute_composite_index(districts)

    # Extract features
    feature_matrix = []
    valid_indices = []
    for i, d in enumerate(districts):
        feats = extract_features(d)
        row = [feats.get(f, 0.0) for f in ALL_FEATURES]
        # Skip rows with all zeros
        if any(v != 0 for v in row):
            feature_matrix.append(row)
            valid_indices.append(i)

    if len(feature_matrix) < 20:
        print(f"[{industry_code}] Too few valid records ({len(feature_matrix)}), skipping")
        return None

    X = np.array(feature_matrix)
    y = np.array([composite[i] for i in valid_indices])

    # Train GradientBoosting
    from sklearn.ensemble import GradientBoostingRegressor

    model = GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=4,
        min_samples_split=5,
        min_samples_leaf=3,
        random_state=42,
    )
    model.fit(X, y)

    importances = dict(zip(ALL_FEATURES, model.feature_importances_))

    # Group by category
    categories = {}
    total_weight = 0.0
    for cat_name, cat_features in CATEGORY_FEATURES.items():
        cat_imp = sum(importances.get(f, 0) for f in cat_features)
        categories[cat_name] = {
            "weight": round(cat_imp, 4),
            "features": cat_features,
            "feature_importances": {
                f: round(importances.get(f, 0), 4) for f in cat_features
            },
        }
        total_weight += cat_imp

    # Normalize weights to sum to 1.0
    if total_weight > 0:
        for cat in categories.values():
            cat["weight"] = round(cat["weight"] / total_weight, 4)

    result = {
        "industry_code": industry_code,
        "n_districts": len(valid_indices),
        "model_type": "GradientBoostingRegressor",
        "composite_index_weights": {
            "sales_per_store_pctile": 0.40,
            "survival_rate_pctile": 0.25,
            "sales_growth_pctile": 0.20,
            "competition_stability_pctile": 0.15,
        },
        "categories": categories,
    }

    # Save
    out_path = DATA_DIR / f"{industry_code}_scorecard_weights.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"[{industry_code}] Saved weights to {out_path}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Build scorecard weights from district data")
    parser.add_argument("--industry", type=str, help="Industry code (e.g., CS100010)")
    parser.add_argument("--all", action="store_true", help="Build for all available industries")
    args = parser.parse_args()

    if args.all:
        for p in sorted(INDUSTRIES_DIR.glob("CS*.json")):
            code = p.stem
            build_weights(code)
    elif args.industry:
        result = build_weights(args.industry)
        if result is None:
            sys.exit(1)
    else:
        # Default: CS100010
        build_weights("CS100010")


if __name__ == "__main__":
    main()
