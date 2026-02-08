"""상권 A vs B 비교 분석 + AI 판정."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/compare")


@router.get("")
async def compare_districts(
    a: str = Query(..., description="상권 A 코드"),
    b: str = Query(..., description="상권 B 코드"),
    industry_code: str = Query("CS100010", description="업종 코드"),
) -> dict[str, Any]:
    """두 상권을 나란히 비교 + AI 판정."""
    from api.services.data_service import get_data_service, estimate_rent
    from api.services.scorecard_service import get_scorecard_service

    svc = get_data_service(industry_code=industry_code)
    sc_svc = get_scorecard_service(industry_code)

    dist_a = svc.get_district(a)
    dist_b = svc.get_district(b)

    if not dist_a or not dist_b:
        raise HTTPException(404, "상권을 찾을 수 없습니다")

    score_a = sc_svc.score_district(dist_a)
    score_b = sc_svc.score_district(dist_b)

    metrics = _build_metrics(dist_a, dist_b, score_a, score_b)

    ai_verdict = await _generate_verdict(
        dist_a, dist_b, score_a, score_b, svc.display_name, svc, industry_code,
    )

    return {
        "district_a": _serialize(dist_a, score_a, svc),
        "district_b": _serialize(dist_b, score_b, svc),
        "comparison": metrics,
        "ai_verdict": ai_verdict,
    }


def _serialize(d: dict, score: dict, svc: Any) -> dict:
    monthly_sales = d.get("monthly_sales", 0)
    store_count = max(d.get("store_count", 1), 1)
    sps = monthly_sales // store_count

    from api.services.data_service import estimate_rent

    est_rent = estimate_rent(
        d.get("district_type", "골목상권"),
        sps,
        score.get("percentile", 50) / 100,
        industry_code=svc.industry_code,
    )

    return {
        "district_code": d.get("district_code", ""),
        "district_name": d.get("district_name", ""),
        "district_type": d.get("district_type", ""),
        "scorecard_total": score.get("total_score", 0),
        "rank": score.get("rank", 0),
        "percentile": score.get("percentile", 0),
        "monthly_sales_per_store": sps,
        "monthly_sales": monthly_sales,
        "store_count": d.get("store_count", 0),
        "survival_rate": d.get("survival_rate", 0),
        "foot_traffic": d.get("foot_traffic_total", 0),
        "estimated_rent": est_rent,
        "peak_time": d.get("peak_time", ""),
        "main_age_group": d.get("main_age_group", ""),
        "new_stores": d.get("new_stores", 0),
        "closed_stores": d.get("closed_stores", 0),
        "categories": score.get("categories", []),
    }


def _build_metrics(a: dict, b: dict, sa: dict, sb: dict) -> dict:
    def _w(va: float, vb: float, lower_better: bool = False) -> str:
        if lower_better:
            return "A" if va < vb else ("B" if vb < va else "TIE")
        return "A" if va > vb else ("B" if vb > va else "TIE")

    sc_a = sa.get("total_score", 0)
    sc_b = sb.get("total_score", 0)
    sca = max(a.get("store_count", 1), 1)
    scb = max(b.get("store_count", 1), 1)
    ms_a = (a.get("monthly_sales", 0)) // sca
    ms_b = (b.get("monthly_sales", 0)) // scb

    return {
        "scorecard": {"a": sc_a, "b": sc_b, "winner": _w(sc_a, sc_b)},
        "monthly_sales": {"a": ms_a, "b": ms_b, "winner": _w(ms_a, ms_b)},
        "survival_rate": {
            "a": a.get("survival_rate", 0),
            "b": b.get("survival_rate", 0),
            "winner": _w(a.get("survival_rate", 0), b.get("survival_rate", 0)),
        },
        "store_count": {
            "a": a.get("store_count", 0),
            "b": b.get("store_count", 0),
            "winner": _w(a.get("store_count", 0), b.get("store_count", 0), lower_better=True),
        },
        "foot_traffic": {
            "a": a.get("foot_traffic_total", 0),
            "b": b.get("foot_traffic_total", 0),
            "winner": _w(a.get("foot_traffic_total", 0), b.get("foot_traffic_total", 0)),
        },
    }


async def _generate_verdict(
    a: dict, b: dict, sa: dict, sb: dict,
    industry_name: str, svc: Any, industry_code: str,
) -> str:
    """Gemini 비교 판정 (실패 시 규칙 기반 폴백)."""
    name_a = a.get("district_name", "A")
    name_b = b.get("district_name", "B")

    try:
        from google import genai

        sca = max(a.get("store_count", 1), 1)
        scb = max(b.get("store_count", 1), 1)

        client = genai.Client()
        prompt = f"""당신은 상권 분석 전문가입니다. 두 상권을 비교 판정해주세요.

[상권 A: {name_a} ({a.get('district_type', '')})]
종합점수: {sa.get('total_score', 0)}점, 점포당 월매출: {a.get('monthly_sales', 0) // sca:,}원
생존율: {a.get('survival_rate', 0):.0%}, 경쟁점포: {a.get('store_count', 0)}개, 유동인구: {a.get('foot_traffic_total', 0):,}명

[상권 B: {name_b} ({b.get('district_type', '')})]
종합점수: {sb.get('total_score', 0)}점, 점포당 월매출: {b.get('monthly_sales', 0) // scb:,}원
생존율: {b.get('survival_rate', 0):.0%}, 경쟁점포: {b.get('store_count', 0)}개, 유동인구: {b.get('foot_traffic_total', 0):,}명

업종: {industry_name}

3~4문장으로 어느 상권이 더 유리한지 판정하고 핵심 근거를 제시하세요. 마크다운 없이 일반 텍스트로."""

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
        )
        if response.text and response.text.strip():
            return response.text.strip()
    except Exception:
        pass

    # 폴백
    score_a = sa.get("total_score", 0)
    score_b = sb.get("total_score", 0)
    if score_a > score_b:
        return f"{name_a} 상권이 종합점수 {score_a}점으로 {name_b}({score_b}점) 대비 유리합니다. 세부 지표를 확인하여 최종 판단하세요."
    if score_b > score_a:
        return f"{name_b} 상권이 종합점수 {score_b}점으로 {name_a}({score_a}점) 대비 유리합니다. 세부 지표를 확인하여 최종 판단하세요."
    return f"두 상권의 종합점수가 {score_a}점으로 동일합니다. 생존율, 경쟁 밀도 등 세부 지표를 비교하여 판단하세요."
