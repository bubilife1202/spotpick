"""Go/No-Go 판정 엔진 — 데이터 기반 정직한 창업 진단."""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict, cast

logger = logging.getLogger(__name__)

VerdictLevel = Literal["GO", "CAUTION", "NO_GO"]


class VerdictReason(TypedDict):
    factor: str  # e.g. "생존율", "경쟁 밀도", "임대 부담"
    level: Literal["danger", "warning", "positive"]
    detail: str  # e.g. "생존율 45% — 하위 10% 상권"
    data_value: str  # e.g. "45%"
    threshold: str  # e.g. "하위 10% = 55%"


class VerdictResult(TypedDict):
    verdict: VerdictLevel
    confidence: int  # 0-100
    summary: str  # 1-line Korean summary
    reasons: list[VerdictReason]
    danger_count: int
    warning_count: int
    positive_count: int
    alternatives: list[dict[str, Any]]  # alternative districts if NO_GO
    data_source: str


_CHANGE_CODE_SCORE: dict[str, float] = {"HH": 1.0, "HL": 0.75, "LH": 0.25, "LL": 0.0}


def _clamp_int(value: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(value)))


def _fmt_pct(x: float) -> str:
    return f"{x * 100:.0f}%"


def _as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _change_indicator_code(district: dict[str, Any]) -> str:
    code = district.get("change_indicator_code")
    if isinstance(code, str):
        return code
    # Some payloads carry a user-facing label in `change_indicator`.
    # We only trust the explicit code for verdict rules.
    return ""


def _change_indicator_score(district: dict[str, Any]) -> float:
    raw = _as_float(district.get("change_indicator_score"))
    if raw is not None:
        return float(raw)
    return _CHANGE_CODE_SCORE.get(_change_indicator_code(district), 0.5)


def _risk_signals_to_reasons(
    district: dict[str, Any],
    thresholds: dict[str, float],
    estimated_rent: int,
) -> tuple[list[VerdictReason], str]:
    """Convert risk_service.analyze_risk signals to VerdictReason rows."""
    from api.services.risk_service import analyze_risk

    analysis = analyze_risk(district, estimated_rent=estimated_rent)
    signals = analysis.get("signals", [])
    thresholds_source = str(analysis.get("thresholds_source", ""))

    survival = _as_float(district.get("survival_rate"))
    store_count = int(district.get("store_count", 0) or 0)
    monthly_sales = int(district.get("monthly_sales", 0) or 0)
    sc = max(store_count, 1)
    sales_per_store = monthly_sales // sc

    rent_ratio = (
        (estimated_rent / sales_per_store) if (estimated_rent > 0 and sales_per_store > 0) else 0.0
    )
    closed = int(district.get("closed_stores", 0) or 0)
    total_stores = store_count + closed
    closed_ratio = (closed / total_stores) if total_stores > 0 else 0.0
    new_stores = int(district.get("new_stores", 0) or 0)
    new_store_ratio = (new_stores / store_count) if store_count > 0 else 0.0

    reasons: list[VerdictReason] = []
    if not isinstance(signals, list):
        return reasons, thresholds_source

    for s in signals:
        if not isinstance(s, dict):
            continue
        level = s.get("level")
        title = s.get("title")
        detail = s.get("detail")
        if level not in ("danger", "warning"):
            continue
        if not isinstance(title, str) or not isinstance(detail, str):
            continue

        factor = title
        data_value = ""
        threshold_str = ""

        if title in ("높은 폐업률", "평균 이하 생존율") and isinstance(survival, float):
            data_value = _fmt_pct(survival)
            if title == "높은 폐업률":
                threshold_str = (
                    f"하위 10% = {_fmt_pct(thresholds.get('survival_rate_danger', 0.55))}"
                )
            else:
                threshold_str = (
                    f"하위 25% = {_fmt_pct(thresholds.get('survival_rate_warning', 0.65))}"
                )
            factor = "생존율"
        elif title in ("경쟁 과밀", "경쟁 다수"):
            data_value = f"{store_count}개"
            if title == "경쟁 과밀":
                threshold_str = f"상위 5% = {int(thresholds.get('competition_danger', 100.0))}개"
            else:
                threshold_str = f"상위 15% = {int(thresholds.get('competition_warning', 60.0))}개"
            factor = "경쟁 밀도"
        elif title in ("과도한 임대 부담", "임대 부담 주의"):
            data_value = f"{rent_ratio:.0%}" if rent_ratio > 0 else "-"
            if title == "과도한 임대 부담":
                threshold_str = f"> {thresholds.get('rent_ratio_danger', 0.30):.0%}"
            else:
                threshold_str = f"> {thresholds.get('rent_ratio_warning', 0.20):.0%}"
            factor = "임대 부담(매출 대비)"
        elif title in ("최근 폐업 급증", "폐업 증가 추세"):
            data_value = f"{closed_ratio:.0%}" if closed_ratio > 0 else "-"
            if title == "최근 폐업 급증":
                threshold_str = f"> {thresholds.get('closed_ratio_danger', 0.15):.0%}"
            else:
                threshold_str = f"> {thresholds.get('closed_ratio_warning', 0.10):.0%}"
            factor = "폐업 비율"
        elif title == "신규 점포 급증":
            data_value = f"{new_store_ratio:.0%}" if new_store_ratio > 0 else "-"
            threshold_str = f"> {thresholds.get('new_store_surge', 0.25):.0%}"
            factor = "신규 진입 과열"
        else:
            data_value = "-"
            threshold_str = "(risk_service)"

        reasons.append(
            {
                "factor": factor,
                "level": cast(Literal["danger", "warning"], level),
                "detail": detail,
                "data_value": data_value,
                "threshold": threshold_str,
            }
        )

    return reasons, thresholds_source


def _find_alternatives(
    district: dict[str, Any],
    data_service: Any,
    industry_code: str,
    budget_max: int | None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """Find alternative districts that pass GO criteria."""
    from api.services.data_service import estimate_rent

    thresholds = _safe_thresholds()
    target_type = (
        district.get("district_type") if isinstance(district.get("district_type"), str) else None
    )
    adjacent: dict[str, set[str]] = {
        "골목상권": {"발달상권", "전통시장"},
        "발달상권": {"골목상권", "관광특구"},
        "전통시장": {"골목상권"},
        "관광특구": {"발달상권"},
    }
    allowed_types: set[str] = set()
    if target_type:
        allowed_types.add(target_type)
        allowed_types |= adjacent.get(target_type, set())
    survival_warn = thresholds.get("survival_rate_warning", 0.65)

    candidates: list[dict[str, Any]] = []
    for d in getattr(data_service, "districts", []) or []:
        if not isinstance(d, dict):
            continue

        # 1) Same district_type or adjacent types (fallback: accept all when missing)
        dt = d.get("district_type")
        if allowed_types and isinstance(dt, str) and dt and dt not in allowed_types:
            continue

        survival = _as_float(d.get("survival_rate"))
        if survival is None or survival <= survival_warn:
            continue

        store_count = int(d.get("store_count", 0) or 0)
        if store_count >= thresholds.get("competition_danger", 100.0):
            continue

        # Estimated rent for budget filter
        sc = max(1, int(d.get("store_count", 1) or 1))
        monthly_sales_per_store = int(d.get("monthly_sales", 0) or 0) // sc
        code = d.get("district_code")
        sales_pct = 0.5
        if isinstance(code, str):
            sales_pct = float(getattr(data_service, "_sales_percentile", {}).get(code, 0.5))

        est_rent = estimate_rent(
            str(dt or "골목상권"),
            monthly_sales_per_store,
            float(sales_pct),
            getattr(data_service, "_rent_ranges", None),
            industry_code=industry_code,
        )
        if budget_max is not None and budget_max > 0 and est_rent > int(budget_max * 0.4):
            continue

        v = _compute_verdict_core(
            district=d,
            industry_code=industry_code,
            budget_max=budget_max,
            experience_level=None,
            estimated_rent=est_rent,
            compute_alternatives=False,
            data_service=data_service,
            thresholds=thresholds,
        )
        if v["verdict"] != "GO":
            continue

        scorecard = d.get("scorecard")
        scorecard_score = None
        if isinstance(scorecard, dict):
            ts = scorecard.get("total_score")
            if isinstance(ts, (int, float)):
                scorecard_score = float(ts)

        monthly_sales_total = int(d.get("monthly_sales", 0) or 0)
        monthly_sales_per_store_out = monthly_sales_total // max(1, store_count)

        candidates.append(
            {
                "district_code": d.get("district_code"),
                "district_name": d.get("district_name"),
                "district_type": dt,
                "survival_rate": survival,
                "estimated_rent": est_rent,
                "monthly_sales_per_store": monthly_sales_per_store_out,
                "verdict": "GO",
                "reason": v.get("summary", "GO 기준 충족"),
                "_score": scorecard_score,
            }
        )

    def _sort_key(x: dict[str, Any]) -> tuple[float, float]:
        sc = x.get("_score")
        if isinstance(sc, (int, float)):
            return (float(sc), float(x.get("survival_rate", 0.0)))
        return (
            float(x.get("survival_rate", 0.0)) * 100.0,
            float(x.get("monthly_sales_per_store", 0)),
        )

    candidates.sort(key=_sort_key, reverse=True)
    out: list[dict[str, Any]] = []
    for c in candidates[: max(0, limit)]:
        c.pop("_score", None)
        out.append(c)
    return out


def _safe_thresholds() -> dict[str, float]:
    from api.services.risk_service import _compute_thresholds_from_data

    try:
        return _compute_thresholds_from_data()
    except Exception:
        logger.exception("Failed to compute thresholds; using fallback defaults")
        return {
            "survival_rate_danger": 0.55,
            "survival_rate_warning": 0.65,
            "competition_danger": 100.0,
            "competition_warning": 60.0,
            "rent_ratio_danger": 0.30,
            "rent_ratio_warning": 0.20,
            "closed_ratio_danger": 0.15,
            "closed_ratio_warning": 0.10,
            "new_store_surge": 0.25,
        }


def _compute_verdict_core(
    district: dict[str, Any],
    industry_code: str,
    budget_max: int | None,
    experience_level: str | None,
    estimated_rent: int,
    compute_alternatives: bool,
    data_service: Any | None,
    thresholds: dict[str, float] | None,
) -> VerdictResult:
    thresholds = thresholds or _safe_thresholds()

    # Use existing risk engine for "risk signals" aggregation
    risk_reasons, thresholds_source = _risk_signals_to_reasons(
        district=district, thresholds=thresholds, estimated_rent=estimated_rent
    )

    survival = _as_float(district.get("survival_rate"))
    store_count = int(district.get("store_count", 0) or 0)
    new_stores = int(district.get("new_stores", 0) or 0)
    closed_stores = int(district.get("closed_stores", 0) or 0)
    name = (
        district.get("district_name")
        if isinstance(district.get("district_name"), str)
        else "해당 상권"
    )

    change_code = _change_indicator_code(district)
    change_score = _change_indicator_score(district)
    ll_decline = (change_code == "LL") or (abs(change_score - 0.0) < 1e-9)

    # Extra reasons beyond risk_service
    reasons: list[VerdictReason] = list(risk_reasons)

    if ll_decline:
        reasons.append(
            {
                "factor": "상권변화 지표",
                "level": "danger",
                "detail": "매출↓ 점포↓ 쇠퇴 상권 (LL)",
                "data_value": change_code or f"score={change_score:.2f}",
                "threshold": "LL",
            }
        )
    elif change_score >= 0.75:
        reasons.append(
            {
                "factor": "상권변화 지표",
                "level": "positive",
                "detail": "성장 상권 (HH) 구간",
                "data_value": change_code or f"score={change_score:.2f}",
                "threshold": ">= 0.75",
            }
        )

    # Budget-based rent burden rules (explicit in verdict spec)
    if budget_max is not None and budget_max > 0 and estimated_rent > 0:
        # budget_max is in 만원, estimated_rent is in 원 — normalize to same unit
        budget_won = budget_max * 10_000  # convert 만원 → 원
        ratio = estimated_rent / budget_won
        if ratio > 0.4:
            reasons.append(
                {
                    "factor": "임대 부담",
                    "level": "danger",
                    "detail": "임대료가 예산의 40% 초과",
                    "data_value": f"{ratio:.0%}",
                    "threshold": "40%",
                }
            )
        elif ratio > 0.3:
            reasons.append(
                {
                    "factor": "임대 부담",
                    "level": "warning",
                    "detail": "임대료가 예산의 30% 초과",
                    "data_value": f"{ratio:.0%}",
                    "threshold": "30%",
                }
            )

    # Net negative store dynamics (CAUTION condition)
    if closed_stores > new_stores:
        reasons.append(
            {
                "factor": "개폐업 동향",
                "level": "warning",
                "detail": "폐업이 개업보다 많음 (순감)",
                "data_value": f"폐업 {closed_stores} > 개업 {new_stores}",
                "threshold": "폐업 > 개업",
            }
        )
    elif closed_stores > 0 and new_stores > int(closed_stores * 1.5):
        reasons.append(
            {
                "factor": "신규 진입",
                "level": "positive",
                "detail": "활발한 신규 진입",
                "data_value": f"개업 {new_stores} vs 폐업 {closed_stores}",
                "threshold": "개업 > 폐업×1.5",
            }
        )

    # High survival is a strong positive
    if isinstance(survival, float) and survival > 0.8:
        reasons.append(
            {
                "factor": "생존율",
                "level": "positive",
                "detail": "높은 생존율",
                "data_value": _fmt_pct(survival),
                "threshold": "> 80%",
            }
        )

    # Low competition + high foot traffic (positive)
    if data_service is not None:
        ft = int(district.get("foot_traffic_total", 0) or 0)
        avg_ft = float(getattr(data_service, "_avg_foot_traffic", 0.0) or 0.0)
        comp_warn = thresholds.get("competition_warning", 60.0)
        if (
            store_count > 0
            and avg_ft > 0
            and ft > avg_ft * 1.5
            and store_count < int(comp_warn * 0.7)
        ):
            reasons.append(
                {
                    "factor": "유동인구/경쟁",
                    "level": "positive",
                    "detail": "유동인구는 높고 경쟁은 낮음",
                    "data_value": f"유동 {ft:,}, 경쟁 {store_count}개",
                    "threshold": f"유동 > 평균×1.5, 경쟁 < {int(comp_warn * 0.7)}개",
                }
            )

    danger_count = sum(1 for r in reasons if r["level"] == "danger")
    warning_count = sum(1 for r in reasons if r["level"] == "warning")
    positive_count = sum(1 for r in reasons if r["level"] == "positive")

    # Confidence calculation
    confidence = 50
    confidence += positive_count * 10
    confidence -= danger_count * 15
    confidence -= warning_count * 8
    confidence = _clamp_int(confidence, 0, 100)

    # Verdict rules
    survival_danger = thresholds.get("survival_rate_danger", 0.55)
    survival_warn = thresholds.get("survival_rate_warning", 0.65)
    comp_danger = thresholds.get("competition_danger", 100.0)
    comp_warn = thresholds.get("competition_warning", 60.0)

    # risk_service danger_count (required for NO_GO condition #4)
    from api.services.risk_service import analyze_risk

    risk_analysis = analyze_risk(district, estimated_rent=estimated_rent)
    risk_danger_count = int(risk_analysis.get("danger_count", 0) or 0)

    no_go_conditions: list[str] = []
    if isinstance(survival, float) and survival < survival_danger:
        no_go_conditions.append("survival")
    if store_count > comp_danger:
        no_go_conditions.append("competition")
    if ll_decline:
        no_go_conditions.append("decline")
    if risk_danger_count >= 3:
        no_go_conditions.append("multi_risk")
    if (
        budget_max is not None
        and budget_max > 0
        and estimated_rent > int(budget_max * 10_000 * 0.4)
    ):
        no_go_conditions.append("rent_budget")
    if (
        experience_level == "beginner"
        and store_count > comp_warn
        and isinstance(survival, float)
        and survival < survival_warn
    ):
        no_go_conditions.append("beginner_combo")

    caution_conditions: list[str] = []
    if isinstance(survival, float) and survival < survival_warn:
        caution_conditions.append("survival")
    if store_count > comp_warn:
        caution_conditions.append("competition")
    if closed_stores > new_stores:
        caution_conditions.append("net_negative")
    if (
        budget_max is not None
        and budget_max > 0
        and estimated_rent > int(budget_max * 10_000 * 0.3)
    ):
        caution_conditions.append("rent_budget")

    if no_go_conditions:
        verdict: VerdictLevel = "NO_GO"
    elif caution_conditions:
        verdict = "CAUTION"
    else:
        verdict = "GO"

    # 1-line summary
    if verdict == "NO_GO":
        # pick one prominent danger factor
        top_danger = next((r for r in reasons if r["level"] == "danger"), None)
        why = top_danger["factor"] if top_danger else "리스크"
        summary = f"NO_GO — {name}: {why}가 위험 구간입니다."
    elif verdict == "CAUTION":
        top_warn = next((r for r in reasons if r["level"] == "warning"), None)
        why = top_warn["factor"] if top_warn else "리스크"
        summary = f"CAUTION — {name}: {why} 때문에 신중 접근이 필요합니다."
    else:
        summary = f"GO — {name}: 데이터상 리스크가 낮은 편입니다."

    alternatives: list[dict[str, Any]] = []
    if verdict == "NO_GO" and compute_alternatives:
        try:
            if data_service is None:
                from api.services.data_service import get_data_service

                data_service = get_data_service(industry_code)
            alternatives = _find_alternatives(
                district=district,
                data_service=data_service,
                industry_code=industry_code,
                budget_max=budget_max,
                limit=3,
            )
        except Exception:
            logger.exception("Failed to compute alternatives")
            alternatives = []

    return {
        "verdict": verdict,
        "confidence": confidence,
        "summary": summary,
        "reasons": reasons,
        "danger_count": danger_count,
        "warning_count": warning_count,
        "positive_count": positive_count,
        "alternatives": alternatives,
        "data_source": thresholds_source or "risk_service thresholds",
    }


def compute_verdict(
    district: dict[str, Any],
    industry_code: str,
    budget_max: int | None = None,
    experience_level: str | None = None,  # "beginner", "experienced", "expert"
    estimated_rent: int = 0,
) -> VerdictResult:
    """Compute Go/No-Go verdict for a district."""
    from api.services.data_service import get_data_service

    thresholds = _safe_thresholds()
    ds = None
    try:
        ds = get_data_service(industry_code)
    except Exception:
        ds = None

    try:
        return _compute_verdict_core(
            district=district,
            industry_code=industry_code,
            budget_max=budget_max,
            experience_level=experience_level,
            estimated_rent=estimated_rent,
            compute_alternatives=True,
            data_service=ds,
            thresholds=thresholds,
        )
    except Exception:
        logger.exception("Verdict computation failed")
        name = (
            district.get("district_name")
            if isinstance(district.get("district_name"), str)
            else "해당 상권"
        )
        return {
            "verdict": "CAUTION",
            "confidence": 30,
            "summary": f"CAUTION — {name}: 판정 계산 중 오류가 발생했습니다.",
            "reasons": [
                {
                    "factor": "시스템",
                    "level": "warning",
                    "detail": "판정 엔진이 일부 데이터를 읽지 못했습니다.",
                    "data_value": "-",
                    "threshold": "-",
                }
            ],
            "danger_count": 0,
            "warning_count": 1,
            "positive_count": 0,
            "alternatives": [],
            "data_source": "verdict_service fallback",
        }
