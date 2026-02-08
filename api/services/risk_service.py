"""폐업 위험 신호 탐지 — DataService 데이터 기반 순수 계산 (AI 호출 없음)."""
from __future__ import annotations

from typing import Any


# 임계값 상수
THRESHOLDS = {
    "survival_rate_danger": 0.55,
    "survival_rate_warning": 0.65,
    "competition_danger": 100,
    "competition_warning": 60,
    "rent_ratio_danger": 0.30,
    "rent_ratio_warning": 0.20,
    "closed_ratio_danger": 0.15,
    "closed_ratio_warning": 0.10,
    "new_store_surge": 0.25,
}


def analyze_risk(
    district: dict[str, Any],
    estimated_rent: int = 0,
) -> dict[str, Any]:
    """상권의 폐업 위험도를 분석합니다.

    Args:
        district: DataService에서 가져온 상권 dict (64개 필드)
        estimated_rent: estimate_rent()로 계산된 추정 임대료 (원)

    Returns:
        {risk_score, risk_level, signals[], danger_count, warning_count}
    """
    signals: list[dict[str, str]] = []
    score = 0

    # 1) 생존율
    survival = district.get("survival_rate")
    if isinstance(survival, (int, float)):
        survival = float(survival)
        if survival < THRESHOLDS["survival_rate_danger"]:
            signals.append({
                "level": "danger",
                "title": "높은 폐업률",
                "detail": f"생존율 {survival:.0%} — 서울 평균(약 65%) 대비 매우 낮음",
                "advice": "이 상권에서 동종 업종의 절반 가까이가 2년 내 폐업합니다",
            })
            score += 30
        elif survival < THRESHOLDS["survival_rate_warning"]:
            signals.append({
                "level": "warning",
                "title": "평균 이하 생존율",
                "detail": f"생존율 {survival:.0%}",
                "advice": "생존율이 평균보다 낮습니다. 차별화 전략이 필요합니다",
            })
            score += 15

    # 2) 경쟁 밀도
    store_count = district.get("store_count", 0) or 0
    if store_count >= THRESHOLDS["competition_danger"]:
        signals.append({
            "level": "danger",
            "title": "경쟁 과밀",
            "detail": f"동종 점포 {store_count}개 — 포화 상태",
            "advice": "이미 과밀 상권입니다. 명확한 차별화 없이는 생존이 어렵습니다",
        })
        score += 25
    elif store_count >= THRESHOLDS["competition_warning"]:
        signals.append({
            "level": "warning",
            "title": "경쟁 다수",
            "detail": f"동종 점포 {store_count}개",
            "advice": "경쟁이 치열합니다. 틈새 전략을 고려하세요",
        })
        score += 10

    # 3) 임대료 대비 매출
    monthly_sales = district.get("monthly_sales", 0) or 0
    sc = max(store_count, 1)
    sales_per_store = monthly_sales // sc
    if estimated_rent > 0 and sales_per_store > 0:
        rent_ratio = estimated_rent / sales_per_store
        if rent_ratio > THRESHOLDS["rent_ratio_danger"]:
            signals.append({
                "level": "danger",
                "title": "과도한 임대 부담",
                "detail": f"임대료/매출 비율 {rent_ratio:.0%} (권장: 15% 이하)",
                "advice": "고정비가 과도합니다. 더 낮은 임대료의 인근 상권을 검토하세요",
            })
            score += 20
        elif rent_ratio > THRESHOLDS["rent_ratio_warning"]:
            signals.append({
                "level": "warning",
                "title": "임대 부담 주의",
                "detail": f"임대료/매출 비율 {rent_ratio:.0%}",
                "advice": "임대료 비중이 다소 높습니다",
            })
            score += 10

    # 4) 폐업 비율
    closed = district.get("closed_stores", 0) or 0
    total_stores = store_count + closed
    if total_stores > 0:
        closed_ratio = closed / total_stores
        if closed_ratio > THRESHOLDS["closed_ratio_danger"]:
            signals.append({
                "level": "danger",
                "title": "최근 폐업 급증",
                "detail": f"폐업률 {closed_ratio:.0%} ({closed}개 폐업)",
                "advice": "최근 폐업이 급증한 상권입니다",
            })
            score += 15
        elif closed_ratio > THRESHOLDS["closed_ratio_warning"]:
            signals.append({
                "level": "warning",
                "title": "폐업 증가 추세",
                "detail": f"폐업률 {closed_ratio:.0%}",
                "advice": "폐업 추세를 주시하세요",
            })
            score += 8

    # 5) 신규 점포 급증 (과열 신호)
    new_stores = district.get("new_stores", 0) or 0
    if store_count > 0 and new_stores / store_count > THRESHOLDS["new_store_surge"]:
        signals.append({
            "level": "warning",
            "title": "신규 점포 급증",
            "detail": f"신규 {new_stores}개 (기존 대비 {new_stores / store_count:.0%})",
            "advice": "시장이 과열 상태일 수 있습니다. 6개월 후 경쟁 심화에 대비하세요",
        })
        score += 10

    risk_score = min(score, 100)
    if risk_score >= 50:
        risk_level = "high"
    elif risk_score >= 25:
        risk_level = "medium"
    else:
        risk_level = "low"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "signals": signals,
        "signal_count": len(signals),
        "danger_count": sum(1 for s in signals if s["level"] == "danger"),
        "warning_count": sum(1 for s in signals if s["level"] == "warning"),
    }
