"""Cafe type recommendation engine — data-driven positioning for cafe startups.

This service takes a single district record (from DataService) and returns a ranked
list of cafe "business models" (e.g. express takeout vs specialty) with scores,
constraints (budget/experience), and explainable reasons.

Important:
- Seoul commercial API does NOT provide cafe sub-category codes.
- This engine infers the best cafe type from real district-level signals.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Literal, TypedDict, cast


CafeTypeCode = Literal[
    "EXPRESS",
    "SPECIALTY",
    "DESSERT",
    "NEIGHBORHOOD",
    "STUDY",
    "STANDARD",
]

ExperienceLevel = Literal["beginner", "experienced", "expert"]


TYPE_NAMES_KR: dict[CafeTypeCode, str] = {
    "EXPRESS": "익스프레스 테이크아웃",
    "SPECIALTY": "스페셜티 카페",
    "DESSERT": "디저트 카페",
    "NEIGHBORHOOD": "동네 생활 카페",
    "STUDY": "스터디·작업 카페",
    "STANDARD": "표준형 카페",
}


MIN_BUDGET_MAN: dict[CafeTypeCode, int] = {
    "EXPRESS": 4000,
    "SPECIALTY": 8000,
    "DESSERT": 7000,
    "NEIGHBORHOOD": 5000,
    "STUDY": 6500,
    "STANDARD": 7000,
}

IDEAL_BUDGET_MAN: dict[CafeTypeCode, int] = {
    "EXPRESS": 5500,
    "SPECIALTY": 11000,
    "DESSERT": 9500,
    "NEIGHBORHOOD": 7000,
    "STUDY": 8500,
    "STANDARD": 9000,
}


DIFFICULTY: dict[CafeTypeCode, int] = {
    "STANDARD": 1,
    "EXPRESS": 2,
    "NEIGHBORHOOD": 2,
    "STUDY": 2,
    "DESSERT": 3,
    "SPECIALTY": 4,
}


DISTRICT_TYPE_BONUS: dict[CafeTypeCode, dict[str, float]] = {
    "EXPRESS": {"발달상권": 10, "관광특구": 6, "골목상권": 2, "전통시장": 1},
    "SPECIALTY": {"골목상권": 10, "관광특구": 7, "발달상권": 4, "전통시장": 3},
    "DESSERT": {"관광특구": 10, "골목상권": 8, "발달상권": 5, "전통시장": 1},
    "NEIGHBORHOOD": {"골목상권": 10, "전통시장": 8, "발달상권": 1, "관광특구": 1},
    "STUDY": {"골목상권": 10, "발달상권": 5, "전통시장": 2, "관광특구": 0},
    "STANDARD": {"발달상권": 8, "골목상권": 6, "관광특구": 6, "전통시장": 5},
}


class CafeTypeComponent(TypedDict):
    key: str
    label: str
    points: float
    detail: str


class CafeTypeRanking(TypedDict):
    rank: int
    type: CafeTypeCode
    name_kr: str
    score: float
    difficulty: int
    budget_min_man: int
    budget_ideal_man: int
    eliminated: bool
    elimination_reason: str
    reasons: list[str]


class CafeTypeWarning(TypedDict):
    code: str
    message: str
    severity: Literal["low", "medium", "high"]


class CafeTypeResult(TypedDict):
    district_code: str
    district_name: str
    industry_code: str
    confidence: float
    confidence_label: str
    rankings: list[CafeTypeRanking]
    warnings: list[CafeTypeWarning]


def _safe_int(v: object) -> int:
    if isinstance(v, bool):
        return 0
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str):
        try:
            return int(float(v))
        except Exception:
            return 0
    return 0


def _safe_float(v: object, default: float = 0.0) -> float:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    if isinstance(v, str):
        try:
            return float(v)
        except Exception:
            return default
    return default


def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    return (a / b) if b > 0 else default


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _S(value: float, lo: float, hi: float) -> float:
    if hi == lo:
        return 1.0 if value >= hi else 0.0
    return _clamp((value - lo) / (hi - lo))


def _S_inv(value: float, lo: float, hi: float) -> float:
    return 1.0 - _S(value, lo, hi)


def _S_bell(value: float, center: float, half_width: float) -> float:
    if half_width <= 0:
        return 1.0
    return _clamp(1.0 - abs(value - center) / half_width)


def _fmt_pct(x: float, digits: int = 0) -> str:
    return f"{x * 100:.{digits}f}%"


def _fmt_int(x: int) -> str:
    return f"{int(x):,}"


def _district_type_bonus(code: CafeTypeCode, district_type: str) -> float:
    return float(DISTRICT_TYPE_BONUS.get(code, {}).get(district_type, 3))


def _experience_level(raw: str | None) -> ExperienceLevel | None:
    if raw in ("beginner", "experienced", "expert"):
        return cast(ExperienceLevel, raw)
    return None


@dataclass(frozen=True)
class _Norm:
    """Percentile normalizer for derived metrics (industry-specific)."""

    arrays: dict[str, list[float]]

    def pct(self, metric: str, value: float) -> float:
        arr = self.arrays.get(metric)
        if not arr or len(arr) < 2:
            return 0.5
        if not math.isfinite(value):
            return 0.5
        idx = bisect_left(arr, value)
        return _clamp(idx / float(len(arr) - 1), 0.0, 1.0)


_NORM_METRICS: tuple[str, ...] = (
    "worker_dominance",
    "lunch_ratio",
    "morning_ratio",
    "weekday_ratio",
    "weekend_ratio",
    "afternoon_ratio",
    "evening_ratio",
    "young_ratio",
    "age_20_ratio",
    "older_ratio",
    "female_ratio",
    "indie_ratio",
    "franchise_ratio_adj",
    "log_foot_traffic",
    "log_resident",
    "log_households",
    "store_count",
    "avg_operation_months",
    "facility_score",
    "closed_ratio",
    "time_spread",
)


@lru_cache(maxsize=32)
def _get_norm(industry_code: str) -> _Norm:
    """Compute percentile arrays for the given industry.

    Cached per industry_code to avoid re-sorting on every request.
    """
    from api.services.data_service import get_data_service

    svc = get_data_service(industry_code)
    arrays: dict[str, list[float]] = {k: [] for k in _NORM_METRICS}

    for row in getattr(svc, "districts", []) or []:
        if not isinstance(row, dict):
            continue
        d = _derive(cast(dict[str, Any], row))
        closed_ratio = _safe_div(
            float(d.closed_stores), float(max(1, d.store_count + d.closed_stores))
        )

        arrays["worker_dominance"].append(float(d.worker_dominance))
        arrays["lunch_ratio"].append(float(d.lunch_ratio))
        arrays["morning_ratio"].append(float(d.morning_ratio))
        arrays["weekday_ratio"].append(float(d.weekday_ratio))
        arrays["weekend_ratio"].append(float(d.weekend_ratio))
        arrays["afternoon_ratio"].append(float(d.afternoon_ratio))
        arrays["evening_ratio"].append(float(d.evening_ratio))
        arrays["young_ratio"].append(float(d.young_ratio))
        arrays["age_20_ratio"].append(float(d.age_20_ratio))
        arrays["older_ratio"].append(float(d.older_ratio))
        arrays["female_ratio"].append(float(d.female_ratio))
        arrays["indie_ratio"].append(float(d.indie_ratio))
        arrays["franchise_ratio_adj"].append(float(d.franchise_ratio_adj))
        arrays["log_foot_traffic"].append(float(d.log_foot_traffic))
        arrays["log_resident"].append(math.log10(max(1.0, float(d.resident_total))))
        arrays["log_households"].append(math.log10(max(1.0, float(d.total_households))))
        arrays["store_count"].append(float(d.store_count))
        arrays["avg_operation_months"].append(float(d.avg_operation_months))
        arrays["facility_score"].append(float(d.facility_score))
        arrays["closed_ratio"].append(float(closed_ratio))
        arrays["time_spread"].append(float(d.time_spread))

    for k in list(arrays.keys()):
        arrays[k].sort()

    return _Norm(arrays=arrays)


def _pct_scaled(
    norm: _Norm | None, metric: str, raw: float, fallback: float, *, invert: bool = False
) -> float:
    if norm is None:
        return fallback
    p = norm.pct(metric, raw)
    return 1.0 - p if invert else p


@dataclass(frozen=True)
class Derived:
    district_type: str
    store_count: int
    survival_rate: (
        float  # 0..1 (clamped). NOTE: in our pipeline this is a 2-year store-count ratio.
    )

    new_stores: int
    closed_stores: int
    avg_operation_months: float

    worker_total: int
    resident_total: int
    foot_traffic_total: int

    worker_dominance: float
    log_foot_traffic: float

    weekday_ratio: float
    weekend_ratio: float
    male_ratio: float
    female_ratio: float

    morning_ratio: float
    lunch_ratio: float
    afternoon_ratio: float
    evening_ratio: float

    age_20_ratio: float
    age_30_ratio: float
    age_40_ratio: float
    age_50_ratio: float
    age_60_ratio: float
    young_ratio: float
    older_ratio: float

    indie_ratio: float
    franchise_ratio_adj: float

    facility_score: int
    facility_university: int
    total_households: int

    time_spread: float
    change_code: str
    change_label: str


def _derive(d: dict[str, Any]) -> Derived:
    district_type = str(d.get("district_type") or "골목상권")
    store_count = max(0, _safe_int(d.get("store_count")))

    new_stores = max(0, _safe_int(d.get("new_stores")))
    closed_stores = max(0, _safe_int(d.get("closed_stores")))
    avg_operation_months = max(0.0, _safe_float(d.get("avg_operation_months"), default=0.0))

    # survival_rate is stored as 0..1 in processed data (may exceed 1.0 if market grew)
    survival_rate_raw = _safe_float(d.get("survival_rate"), default=0.0)
    survival_rate = _clamp(survival_rate_raw, 0.0, 1.0)

    worker_total = max(0, _safe_int(d.get("worker_total")))
    resident_total = max(0, _safe_int(d.get("resident_total")))
    foot_traffic_total = max(0, _safe_int(d.get("foot_traffic_total")))
    worker_dominance = _safe_div(
        float(worker_total), float(worker_total + resident_total), default=0.5
    )

    log_foot_traffic = math.log10(max(1.0, float(foot_traffic_total)))

    weekday_ratio = _clamp(_safe_float(d.get("weekday_ratio"), default=0.0))
    weekend_ratio = _clamp(_safe_float(d.get("weekend_ratio"), default=0.0))
    male_ratio = _clamp(_safe_float(d.get("male_ratio"), default=0.0))
    female_ratio = _clamp(_safe_float(d.get("female_ratio"), default=0.0))

    # Time ratios from time_* sales
    time_sales = {
        "morning": float(_safe_int(d.get("time_06_11_sales"))),
        "lunch": float(_safe_int(d.get("time_11_14_sales"))),
        "afternoon": float(_safe_int(d.get("time_14_17_sales"))),
        "evening": float(_safe_int(d.get("time_17_21_sales"))),
    }
    total_time_sales = sum(time_sales.values())
    if total_time_sales <= 0:
        # fallback: approximate from monthly_sales split
        ms = float(_safe_int(d.get("monthly_sales")))
        total_time_sales = ms if ms > 0 else 1.0
        time_sales = {
            "morning": total_time_sales * 0.2,
            "lunch": total_time_sales * 0.3,
            "afternoon": total_time_sales * 0.3,
            "evening": total_time_sales * 0.2,
        }

    morning_ratio = _safe_div(time_sales["morning"], total_time_sales)
    lunch_ratio = _safe_div(time_sales["lunch"], total_time_sales)
    afternoon_ratio = _safe_div(time_sales["afternoon"], total_time_sales)
    evening_ratio = _safe_div(time_sales["evening"], total_time_sales)

    # Age ratios from age_* sales
    age_sales = {
        "20": float(_safe_int(d.get("age_20_sales"))),
        "30": float(_safe_int(d.get("age_30_sales"))),
        "40": float(_safe_int(d.get("age_40_sales"))),
        "50": float(_safe_int(d.get("age_50_sales"))),
        "60": float(_safe_int(d.get("age_60_sales"))),
    }
    total_age_sales = sum(age_sales.values())
    if total_age_sales <= 0:
        total_age_sales = 1.0

    age_20_ratio = _safe_div(age_sales["20"], total_age_sales)
    age_30_ratio = _safe_div(age_sales["30"], total_age_sales)
    age_40_ratio = _safe_div(age_sales["40"], total_age_sales)
    age_50_ratio = _safe_div(age_sales["50"], total_age_sales)
    age_60_ratio = _safe_div(age_sales["60"], total_age_sales)
    young_ratio = _clamp(age_20_ratio + age_30_ratio)
    older_ratio = _clamp(age_40_ratio + age_50_ratio + age_60_ratio)

    franchise = max(0, _safe_int(d.get("franchise_stores")))
    if store_count >= 5:
        franchise_ratio_adj = _safe_div(float(franchise), float(max(1, store_count)))
    else:
        franchise_ratio_adj = _safe_div(float(franchise + 2), float(store_count + 4))
    franchise_ratio_adj = _clamp(franchise_ratio_adj)
    indie_ratio = _clamp(1.0 - franchise_ratio_adj)

    facility_score = max(0, _safe_int(d.get("facility_score")))
    facility_university = max(0, _safe_int(d.get("facility_university")))
    total_households = max(0, _safe_int(d.get("total_households")))

    # Rough spread: higher when demand is distributed (not single peak)
    ratios = [morning_ratio, lunch_ratio, afternoon_ratio, evening_ratio]
    time_spread = _clamp(1.0 - max(ratios) + min(ratios), 0.0, 1.0)

    change_code = str(d.get("change_indicator_code") or "")
    change_label = str(d.get("change_indicator") or "")

    return Derived(
        district_type=district_type,
        store_count=store_count,
        survival_rate=survival_rate,
        new_stores=new_stores,
        closed_stores=closed_stores,
        avg_operation_months=avg_operation_months,
        worker_total=worker_total,
        resident_total=resident_total,
        foot_traffic_total=foot_traffic_total,
        worker_dominance=_clamp(worker_dominance),
        log_foot_traffic=log_foot_traffic,
        weekday_ratio=weekday_ratio,
        weekend_ratio=weekend_ratio,
        male_ratio=male_ratio,
        female_ratio=female_ratio,
        morning_ratio=_clamp(morning_ratio),
        lunch_ratio=_clamp(lunch_ratio),
        afternoon_ratio=_clamp(afternoon_ratio),
        evening_ratio=_clamp(evening_ratio),
        age_20_ratio=_clamp(age_20_ratio),
        age_30_ratio=_clamp(age_30_ratio),
        age_40_ratio=_clamp(age_40_ratio),
        age_50_ratio=_clamp(age_50_ratio),
        age_60_ratio=_clamp(age_60_ratio),
        young_ratio=young_ratio,
        older_ratio=older_ratio,
        indie_ratio=indie_ratio,
        franchise_ratio_adj=franchise_ratio_adj,
        facility_score=facility_score,
        facility_university=facility_university,
        total_households=total_households,
        time_spread=time_spread,
        change_code=change_code,
        change_label=change_label,
    )


def _pick_reasons(components: list[CafeTypeComponent], limit: int = 4) -> list[str]:
    # Highest contributing components; filter out tiny contributions.
    sorted_comps = sorted(components, key=lambda c: c.get("points", 0.0), reverse=True)
    out: list[str] = []
    for c in sorted_comps:
        if len(out) >= limit:
            break
        pts = float(c.get("points", 0.0))
        if pts < 4.0:
            continue
        detail = str(c.get("detail", "")).strip()
        if not detail:
            continue
        out.append(detail)
    return out


def _budget_gate(
    score: float, type_code: CafeTypeCode, budget_max_man: int | None
) -> tuple[float, bool, str]:
    if budget_max_man is None or budget_max_man <= 0:
        return score, False, ""

    min_b = MIN_BUDGET_MAN[type_code]
    if budget_max_man < min_b:
        return 0.0, True, f"예산 {budget_max_man:,}만원 < 최소 {min_b:,}만원"

    # Soft budget signal should not override location fit. Keep score unchanged.
    return score, False, ""


def _experience_gate(
    score: float, type_code: CafeTypeCode, exp: ExperienceLevel | None
) -> tuple[float, bool, str]:
    # Do NOT down-rank location fit by experience.
    # Experience is surfaced as a warning and execution guidance in the UI.
    return score, False, ""


def _confidence_label(conf: float) -> str:
    if conf >= 80:
        return "매우 높음"
    if conf >= 60:
        return "높음"
    if conf >= 40:
        return "보통"
    if conf >= 20:
        return "낮음"
    return "매우 낮음"


def _compute_confidence(d: Derived, final_scores: dict[CafeTypeCode, float]) -> float:
    scores = sorted(final_scores.values(), reverse=True)
    top = scores[0] if scores else 0.0
    second = scores[1] if len(scores) > 1 else 0.0

    # C1: data completeness (0-30)
    key_nonzero = 0
    key_total = 10
    key_nonzero += 1 if d.worker_total > 0 else 0
    key_nonzero += 1 if d.resident_total > 0 else 0
    key_nonzero += 1 if d.foot_traffic_total > 0 else 0
    key_nonzero += 1 if d.store_count > 0 else 0
    key_nonzero += 1 if d.avg_operation_months > 0 else 0
    key_nonzero += 1 if d.weekday_ratio > 0 else 0
    key_nonzero += 1 if d.female_ratio > 0 else 0
    key_nonzero += 1 if d.total_households > 0 else 0
    key_nonzero += 1 if d.facility_score > 0 else 0
    key_nonzero += 1 if d.change_code != "" else 0
    c1 = (key_nonzero / max(1, key_total)) * 30.0

    # C2: sample size (0-25)
    c2 = _S(float(d.store_count), 3.0, 30.0) * 25.0

    # C3: margin (0-25)
    margin = top - second
    c3 = _S(float(margin), 3.0, 20.0) * 25.0

    # C4: absolute strength (0-20)
    c4 = _S(float(top), 40.0, 75.0) * 20.0

    return round(_clamp(c1 + c2 + c3 + c4, 0.0, 100.0), 1)


def _score_express(d: Derived, norm: _Norm | None) -> tuple[float, list[CafeTypeComponent]]:
    comps: list[CafeTypeComponent] = []

    def add(key: str, label: str, scaled: float, weight: float, detail: str) -> None:
        comps.append(
            {
                "key": key,
                "label": label,
                "points": round(float(scaled) * float(weight), 2),
                "detail": detail,
            }
        )

    add(
        "worker_dominance",
        "직장인 비중",
        _pct_scaled(
            norm, "worker_dominance", d.worker_dominance, _S(d.worker_dominance, 0.55, 0.85)
        ),
        25,
        f"직장인 비중 {_fmt_pct(d.worker_dominance)}",
    )
    add(
        "lunch_ratio",
        "점심 피크",
        _pct_scaled(norm, "lunch_ratio", d.lunch_ratio, _S(d.lunch_ratio, 0.22, 0.36)),
        15,
        f"점심(11-14) 매출 {_fmt_pct(d.lunch_ratio)}",
    )
    add(
        "morning_ratio",
        "아침 수요",
        _pct_scaled(norm, "morning_ratio", d.morning_ratio, _S(d.morning_ratio, 0.10, 0.22)),
        10,
        f"아침(06-11) 매출 {_fmt_pct(d.morning_ratio)}",
    )
    add(
        "weekday_ratio",
        "주중 집중",
        _pct_scaled(norm, "weekday_ratio", d.weekday_ratio, _S(d.weekday_ratio, 0.62, 0.78)),
        10,
        f"주중 매출비율 {_fmt_pct(d.weekday_ratio)}",
    )
    add(
        "foot_traffic",
        "유동인구",
        _pct_scaled(norm, "log_foot_traffic", d.log_foot_traffic, _S(d.log_foot_traffic, 5.5, 6.9)),
        15,
        f"유동인구 {_fmt_int(d.foot_traffic_total)}",
    )
    add(
        "young_ratio",
        "2030 비중",
        _pct_scaled(norm, "young_ratio", d.young_ratio, _S(d.young_ratio, 0.40, 0.60)),
        10,
        f"2030 매출비중 {_fmt_pct(d.young_ratio)}",
    )
    add(
        "afternoon_penalty",
        "오후 편중",
        _pct_scaled(
            norm,
            "afternoon_ratio",
            d.afternoon_ratio,
            _S_inv(d.afternoon_ratio, 0.22, 0.33),
            invert=True,
        ),
        5,
        f"오후(14-17) 편중 {_fmt_pct(d.afternoon_ratio)}",
    )

    bonus = _district_type_bonus("EXPRESS", d.district_type)
    comps.append(
        {
            "key": "district_type",
            "label": "상권유형",
            "points": round(float(bonus), 2),
            "detail": f"상권유형 {d.district_type}",
        }
    )

    score = sum(c["points"] for c in comps)
    return round(score, 1), comps


def _score_specialty(d: Derived, norm: _Norm | None) -> tuple[float, list[CafeTypeComponent]]:
    comps: list[CafeTypeComponent] = []

    def add(key: str, label: str, scaled: float, weight: float, detail: str) -> None:
        comps.append(
            {
                "key": key,
                "label": label,
                "points": round(float(scaled) * float(weight), 2),
                "detail": detail,
            }
        )

    add(
        "indie_ratio",
        "개인카페 환경",
        _pct_scaled(norm, "indie_ratio", d.indie_ratio, _S(d.indie_ratio, 0.50, 0.80)),
        25,
        f"개인카페 비중 {_fmt_pct(d.indie_ratio)}",
    )
    add(
        "afternoon_ratio",
        "오후 목적지 수요",
        _pct_scaled(norm, "afternoon_ratio", d.afternoon_ratio, _S(d.afternoon_ratio, 0.22, 0.34)),
        15,
        f"오후(14-17) 매출 {_fmt_pct(d.afternoon_ratio)}",
    )
    add(
        "young_ratio",
        "2030 수요",
        _pct_scaled(norm, "young_ratio", d.young_ratio, _S(d.young_ratio, 0.42, 0.62)),
        15,
        f"2030 매출비중 {_fmt_pct(d.young_ratio)}",
    )
    add(
        "avg_operation_months",
        "운영 지속성",
        _pct_scaled(
            norm,
            "avg_operation_months",
            d.avg_operation_months,
            _S(d.avg_operation_months, 24.0, 120.0),
        ),
        10,
        f"평균 운영 {d.avg_operation_months:.0f}개월",
    )
    add(
        "competition_bell",
        "적정 경쟁",
        _S_bell(
            _pct_scaled(
                norm, "store_count", float(d.store_count), _S_bell(float(d.store_count), 30.0, 40.0)
            ),
            0.60,
            0.35,
        ),
        10,
        f"카페 점포수 {d.store_count}개",
    )
    add(
        "foot_traffic",
        "유동인구",
        _pct_scaled(norm, "log_foot_traffic", d.log_foot_traffic, _S(d.log_foot_traffic, 5.0, 6.5)),
        10,
        f"유동인구 {_fmt_int(d.foot_traffic_total)}",
    )
    add(
        "weekend_ratio",
        "주말 수요",
        _pct_scaled(norm, "weekend_ratio", d.weekend_ratio, _S(d.weekend_ratio, 0.28, 0.45)),
        5,
        f"주말 매출비율 {_fmt_pct(d.weekend_ratio)}",
    )

    bonus = _district_type_bonus("SPECIALTY", d.district_type)
    comps.append(
        {
            "key": "district_type",
            "label": "상권유형",
            "points": round(float(bonus), 2),
            "detail": f"상권유형 {d.district_type}",
        }
    )

    score = sum(c["points"] for c in comps)
    return round(score, 1), comps


def _score_dessert(d: Derived, norm: _Norm | None) -> tuple[float, list[CafeTypeComponent]]:
    comps: list[CafeTypeComponent] = []

    def add(key: str, label: str, scaled: float, weight: float, detail: str) -> None:
        comps.append(
            {
                "key": key,
                "label": label,
                "points": round(float(scaled) * float(weight), 2),
                "detail": detail,
            }
        )

    add(
        "female_ratio",
        "여성 수요",
        _pct_scaled(norm, "female_ratio", d.female_ratio, _S(d.female_ratio, 0.50, 0.62)),
        20,
        f"여성 매출비중 {_fmt_pct(d.female_ratio)}",
    )
    add(
        "afternoon_ratio",
        "오후 디저트 시간",
        _pct_scaled(norm, "afternoon_ratio", d.afternoon_ratio, _S(d.afternoon_ratio, 0.22, 0.34)),
        15,
        f"오후(14-17) 매출 {_fmt_pct(d.afternoon_ratio)}",
    )
    add(
        "weekend_ratio",
        "주말 레저",
        _pct_scaled(norm, "weekend_ratio", d.weekend_ratio, _S(d.weekend_ratio, 0.30, 0.48)),
        20,
        f"주말 매출비율 {_fmt_pct(d.weekend_ratio)}",
    )
    add(
        "young_ratio",
        "2030 수요",
        _pct_scaled(norm, "young_ratio", d.young_ratio, _S(d.young_ratio, 0.42, 0.62)),
        15,
        f"2030 매출비중 {_fmt_pct(d.young_ratio)}",
    )
    add(
        "foot_traffic",
        "유동인구",
        _pct_scaled(norm, "log_foot_traffic", d.log_foot_traffic, _S(d.log_foot_traffic, 5.0, 6.5)),
        10,
        f"유동인구 {_fmt_int(d.foot_traffic_total)}",
    )
    add(
        "avg_operation_months",
        "운영 지속성",
        _pct_scaled(
            norm,
            "avg_operation_months",
            d.avg_operation_months,
            _S(d.avg_operation_months, 24.0, 120.0),
        ),
        10,
        f"평균 운영 {d.avg_operation_months:.0f}개월",
    )

    bonus = _district_type_bonus("DESSERT", d.district_type)
    comps.append(
        {
            "key": "district_type",
            "label": "상권유형",
            "points": round(float(bonus), 2),
            "detail": f"상권유형 {d.district_type}",
        }
    )

    score = sum(c["points"] for c in comps)
    return round(score, 1), comps


def _score_neighborhood(d: Derived, norm: _Norm | None) -> tuple[float, list[CafeTypeComponent]]:
    comps: list[CafeTypeComponent] = []

    def add(key: str, label: str, scaled: float, weight: float, detail: str) -> None:
        comps.append(
            {
                "key": key,
                "label": label,
                "points": round(float(scaled) * float(weight), 2),
                "detail": detail,
            }
        )

    add(
        "not_office",
        "비오피스",
        _pct_scaled(
            norm,
            "worker_dominance",
            d.worker_dominance,
            _S_inv(d.worker_dominance, 0.45, 0.80),
            invert=True,
        ),
        20,
        f"직장인 비중 {_fmt_pct(d.worker_dominance)}",
    )
    add(
        "older_ratio",
        "중장년 수요",
        _pct_scaled(norm, "older_ratio", d.older_ratio, _S(d.older_ratio, 0.30, 0.55)),
        15,
        f"40+ 매출비중 {_fmt_pct(d.older_ratio)}",
    )
    # APT ratio is currently unreliable (API returns 0 for all); use households as proxy.
    add(
        "households",
        "거주 기반",
        _pct_scaled(
            norm,
            "log_households",
            math.log10(max(1.0, float(d.total_households))),
            _S(float(d.total_households), 800.0, 8000.0),
        ),
        15,
        f"총 가구수 {_fmt_int(d.total_households)}",
    )
    add(
        "underserved",
        "공급 과잉 아님",
        _pct_scaled(
            norm,
            "store_count",
            float(d.store_count),
            _S_inv(float(d.store_count), 3.0, 40.0),
            invert=True,
        ),
        15,
        f"카페 점포수 {d.store_count}개",
    )
    add(
        "avg_operation_months",
        "운영 지속성",
        _pct_scaled(
            norm,
            "avg_operation_months",
            d.avg_operation_months,
            _S(d.avg_operation_months, 24.0, 120.0),
        ),
        10,
        f"평균 운영 {d.avg_operation_months:.0f}개월",
    )
    add(
        "time_spread",
        "꾸준함",
        _pct_scaled(norm, "time_spread", d.time_spread, _S(d.time_spread, 0.15, 0.45)),
        5,
        "시간대 수요가 비교적 고르게 분포",
    )

    bonus = _district_type_bonus("NEIGHBORHOOD", d.district_type)
    comps.append(
        {
            "key": "district_type",
            "label": "상권유형",
            "points": round(float(bonus), 2),
            "detail": f"상권유형 {d.district_type}",
        }
    )

    score = sum(c["points"] for c in comps)
    return round(score, 1), comps


def _score_study(d: Derived, norm: _Norm | None) -> tuple[float, list[CafeTypeComponent]]:
    comps: list[CafeTypeComponent] = []

    def add(key: str, label: str, scaled: float, weight: float, detail: str) -> None:
        comps.append(
            {
                "key": key,
                "label": label,
                "points": round(float(scaled) * float(weight), 2),
                "detail": detail,
            }
        )

    add(
        "university",
        "대학교",
        _S(float(d.facility_university), 0.0, 1.0),
        20,
        f"대학교 시설 {d.facility_university}개",
    )
    add(
        "age20",
        "20대 수요",
        _pct_scaled(norm, "age_20_ratio", d.age_20_ratio, _S(d.age_20_ratio, 0.20, 0.38)),
        20,
        f"20대 매출비중 {_fmt_pct(d.age_20_ratio)}",
    )
    add(
        "evening",
        "저녁 체류",
        _pct_scaled(norm, "evening_ratio", d.evening_ratio, _S(d.evening_ratio, 0.18, 0.30)),
        15,
        f"저녁(17-21) 매출 {_fmt_pct(d.evening_ratio)}",
    )
    add(
        "not_office",
        "비오피스",
        _pct_scaled(
            norm,
            "worker_dominance",
            d.worker_dominance,
            _S_inv(d.worker_dominance, 0.45, 0.80),
            invert=True,
        ),
        10,
        f"직장인 비중 {_fmt_pct(d.worker_dominance)}",
    )
    add(
        "foot_traffic",
        "유동인구",
        _S_bell(
            _pct_scaled(
                norm, "log_foot_traffic", d.log_foot_traffic, _S_bell(d.log_foot_traffic, 5.8, 1.2)
            ),
            0.60,
            0.50,
        ),
        10,
        f"유동인구 {_fmt_int(d.foot_traffic_total)}",
    )
    add(
        "resident",
        "거주 기반",
        _pct_scaled(
            norm,
            "log_resident",
            math.log10(max(1.0, float(d.resident_total))),
            _S(float(d.resident_total), 1000.0, 8000.0),
        ),
        10,
        f"상주인구 {_fmt_int(d.resident_total)}",
    )
    add(
        "indie",
        "체류형 차별화",
        _pct_scaled(
            norm,
            "franchise_ratio_adj",
            d.franchise_ratio_adj,
            _S_inv(d.franchise_ratio_adj, 0.30, 0.65),
            invert=True,
        ),
        5,
        f"프랜차이즈 비중 {_fmt_pct(d.franchise_ratio_adj)}",
    )

    bonus = _district_type_bonus("STUDY", d.district_type)
    comps.append(
        {
            "key": "district_type",
            "label": "상권유형",
            "points": round(float(bonus), 2),
            "detail": f"상권유형 {d.district_type}",
        }
    )

    score = sum(c["points"] for c in comps)
    return round(score, 1), comps


def _score_standard(d: Derived, norm: _Norm | None) -> tuple[float, list[CafeTypeComponent]]:
    comps: list[CafeTypeComponent] = []

    def add(key: str, label: str, scaled: float, weight: float, detail: str) -> None:
        comps.append(
            {
                "key": key,
                "label": label,
                "points": round(float(scaled) * float(weight), 2),
                "detail": detail,
            }
        )

    add(
        "avg_operation_months",
        "운영 지속성",
        _pct_scaled(
            norm,
            "avg_operation_months",
            d.avg_operation_months,
            _S(d.avg_operation_months, 24.0, 120.0),
        ),
        20,
        f"평균 운영 {d.avg_operation_months:.0f}개월",
    )
    closed_ratio = _safe_div(float(d.closed_stores), float(max(1, d.store_count + d.closed_stores)))
    add(
        "closed_ratio",
        "폐업 압력",
        _pct_scaled(
            norm, "closed_ratio", closed_ratio, _S_inv(closed_ratio, 0.05, 0.20), invert=True
        ),
        10,
        f"폐업 비율 {_fmt_pct(closed_ratio)}",
    )
    add(
        "foot_traffic",
        "유동인구",
        _pct_scaled(norm, "log_foot_traffic", d.log_foot_traffic, _S(d.log_foot_traffic, 5.0, 6.5)),
        20,
        f"유동인구 {_fmt_int(d.foot_traffic_total)}",
    )
    add(
        "competition_bell",
        "적정 경쟁",
        _S_bell(
            _pct_scaled(
                norm, "store_count", float(d.store_count), _S_bell(float(d.store_count), 25.0, 35.0)
            ),
            0.60,
            0.40,
        ),
        15,
        f"카페 점포수 {d.store_count}개",
    )
    add(
        "time_spread",
        "수요 분산",
        _pct_scaled(norm, "time_spread", d.time_spread, _S(d.time_spread, 0.15, 0.40)),
        10,
        "시간대 수요가 한쪽에 치우치지 않음",
    )
    add(
        "households",
        "거주 기반",
        _pct_scaled(
            norm,
            "log_households",
            math.log10(max(1.0, float(d.total_households))),
            _S(float(d.total_households), 500.0, 5000.0),
        ),
        10,
        f"총 가구수 {_fmt_int(d.total_households)}",
    )
    add(
        "facility",
        "입지 편의",
        _pct_scaled(
            norm, "facility_score", float(d.facility_score), _S(float(d.facility_score), 30.0, 70.0)
        ),
        10,
        f"시설 점수 {d.facility_score}",
    )

    bonus = _district_type_bonus("STANDARD", d.district_type)
    comps.append(
        {
            "key": "district_type",
            "label": "상권유형",
            "points": round(float(bonus), 2),
            "detail": f"상권유형 {d.district_type}",
        }
    )

    score = sum(c["points"] for c in comps)
    return round(score, 1), comps


def compute_cafe_type_recommendation(
    *,
    industry_code: str,
    district: dict[str, Any],
    budget_max_man: int | None = None,
    experience_level: str | None = None,
) -> CafeTypeResult:
    d = _derive(district)
    exp = _experience_level(experience_level)

    norm: _Norm | None = None
    try:
        norm = _get_norm(industry_code)
    except Exception:
        norm = None

    raw: dict[CafeTypeCode, tuple[float, list[CafeTypeComponent]]] = {
        "EXPRESS": _score_express(d, norm),
        "SPECIALTY": _score_specialty(d, norm),
        "DESSERT": _score_dessert(d, norm),
        "NEIGHBORHOOD": _score_neighborhood(d, norm),
        "STUDY": _score_study(d, norm),
        "STANDARD": _score_standard(d, norm),
    }

    # Standard boost: if no niche dominates, standard becomes more attractive.
    max_niche = max(v[0] for k, v in raw.items() if k != "STANDARD")
    if max_niche < 60.0:
        boost = min(12.0, (60.0 - max_niche) * 0.4)
        s, comps = raw["STANDARD"]
        raw["STANDARD"] = (round(s + boost, 1), comps)

    # Apply gates
    final_scores: dict[CafeTypeCode, float] = {}
    eliminated: dict[CafeTypeCode, tuple[bool, str]] = {}
    reasons_map: dict[CafeTypeCode, list[str]] = {}

    for code, (score, comps) in raw.items():
        gated, elim_budget, reason_budget = _budget_gate(score, code, budget_max_man)
        final_scores[code] = round(float(gated), 1)
        eliminated[code] = (bool(elim_budget), reason_budget)
        reasons_map[code] = _pick_reasons(comps)

    ranked = sorted(final_scores.items(), key=lambda kv: kv[1], reverse=True)
    conf = _compute_confidence(d, final_scores)

    warnings: list[CafeTypeWarning] = []
    top_score = ranked[0][1] if ranked else 0.0
    if top_score < 40.0:
        warnings.append(
            {
                "code": "MARGINAL_LOCATION",
                "message": "모든 카페 타입 적합도가 낮습니다. 높은 리스크 가능성이 있습니다.",
                "severity": "high",
            }
        )

    if d.change_label:
        # 서울 상권변화지표(TRDAR_CHNGE_IX_NM)는 4개 라벨로 제공된다.
        # - 상권축소: 명확한 리스크
        # - 다이나믹: 변동성이 큰 편 (기회/리스크 공존)
        # - 정체: 큰 변화 없음
        # - 상권확장: 확장 국면 (경쟁 증가/기회 공존)
        if d.change_label == "상권축소":
            warnings.append(
                {
                    "code": "SHRINKING_DISTRICT",
                    "message": f"상권변화지표가 {d.change_code}({d.change_label})입니다. 보수적으로 접근하세요.",
                    "severity": "high",
                }
            )
        elif d.change_label == "다이나믹":
            warnings.append(
                {
                    "code": "DYNAMIC_DISTRICT",
                    "message": f"상권변화지표가 {d.change_code}({d.change_label})입니다. 변동성이 큰 상권일 수 있습니다.",
                    "severity": "medium",
                }
            )
        elif d.change_label == "정체":
            warnings.append(
                {
                    "code": "STAGNANT_DISTRICT",
                    "message": f"상권변화지표가 {d.change_code}({d.change_label})입니다.",
                    "severity": "low",
                }
            )

    if d.avg_operation_months > 0 and d.avg_operation_months < 36:
        warnings.append(
            {
                "code": "SHORT_OPERATION",
                "message": f"평균 운영기간이 {d.avg_operation_months:.0f}개월로 짧은 편입니다.",
                "severity": "medium",
            }
        )

    if d.closed_stores > d.new_stores:
        warnings.append(
            {
                "code": "NET_CLOSURE",
                "message": "폐업이 개업보다 많아 보입니다. 현장 확인이 필요합니다.",
                "severity": "medium",
            }
        )

    if d.store_count > 80:
        warnings.append(
            {
                "code": "HIGH_COMPETITION",
                "message": f"경쟁 매장이 {d.store_count}개로 매우 많습니다. 강한 차별화가 필요합니다.",
                "severity": "medium",
            }
        )

    if len(ranked) >= 2 and (ranked[0][1] - ranked[1][1]) < 5.0:
        warnings.append(
            {
                "code": "CLOSE_CALL",
                "message": "1위와 2위 점수 차이가 작습니다. 두 타입 모두 검토를 권장합니다.",
                "severity": "low",
            }
        )

    if budget_max_man is not None and budget_max_man > 0 and ranked:
        top_type = ranked[0][0]
        ideal = IDEAL_BUDGET_MAN[top_type]
        if budget_max_man < ideal:
            warnings.append(
                {
                    "code": "TIGHT_BUDGET",
                    "message": f"1위 타입({TYPE_NAMES_KR[top_type]}) 기준 예산이 타이트합니다 (이상치 {ideal:,}만원).",
                    "severity": "medium",
                }
            )

    if exp == "beginner" and ranked:
        top_type = ranked[0][0]
        if DIFFICULTY[top_type] >= 3:
            warnings.append(
                {
                    "code": "HARD_FOR_BEGINNER",
                    "message": f"1위 타입({TYPE_NAMES_KR[top_type]})은 난이도가 높습니다. 트레이닝/인력 보강을 권장합니다.",
                    "severity": "medium",
                }
            )

    rankings: list[CafeTypeRanking] = []
    for idx, (code, score) in enumerate(ranked):
        elim, elim_reason = eliminated[code]
        rankings.append(
            {
                "rank": idx + 1,
                "type": code,
                "name_kr": TYPE_NAMES_KR[code],
                "score": float(score),
                "difficulty": int(DIFFICULTY[code]),
                "budget_min_man": int(MIN_BUDGET_MAN[code]),
                "budget_ideal_man": int(IDEAL_BUDGET_MAN[code]),
                "eliminated": bool(elim and score <= 0.0),
                "elimination_reason": str(elim_reason if elim and score <= 0.0 else ""),
                "reasons": reasons_map.get(code, []),
            }
        )

    district_code = str(district.get("district_code") or "")
    district_name = str(district.get("district_name") or district_code)

    return {
        "district_code": district_code,
        "district_name": district_name,
        "industry_code": industry_code,
        "confidence": float(conf),
        "confidence_label": _confidence_label(conf),
        "rankings": rankings,
        "warnings": warnings,
    }
