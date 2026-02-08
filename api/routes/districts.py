from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/districts")


@router.get("/search")
def search_districts(
    q: str = Query("", min_length=0, max_length=100, description="검색어 (상권명, 구, 역 등)"),
    limit: int = Query(20, ge=1, le=50),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    from ..services.data_service import get_data_service

    svc = get_data_service(industry_code=industry_code)
    q_clean = (q or "").strip()
    q_lower = q_clean.lower()

    if not q_lower:
        return {"results": [], "total": 0}

    # Use DataService ranking to avoid "강남" -> only "강남구청..." results due to input order + early break.
    raw = svc.search_districts(q_clean, limit=limit)

    def clamp_rate(v: object) -> float | None:
        try:
            if isinstance(v, (int, float)):
                return float(max(0.0, min(1.0, float(v))))
        except Exception:
            return None
        return None

    results: list[dict[str, object]] = []
    for d in raw:
        name = d.get("district_name", "")
        dtype = d.get("district_type", "")
        results.append(
            {
                "code": d["district_code"],
                "name": name,
                "type": dtype,
                "monthly_sales": d.get("monthly_sales"),
                "store_count": d.get("store_count"),
                "survival_rate": clamp_rate(d.get("survival_rate")),
            }
        )

    return {"results": results, "total": len(results)}


@router.get("/list")
def list_districts(
    district_type: str | None = Query(None, description="상권유형 필터 (골목상권, 발달상권, 전통시장, 관광특구)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    from ..services.data_service import get_data_service

    svc = get_data_service(industry_code=industry_code)
    filtered = svc.districts

    if district_type:
        filtered = [d for d in filtered if d.get("district_type") == district_type]

    total = len(filtered)
    page = filtered[offset : offset + limit]

    return {
        "results": [
            {
                "code": d["district_code"],
                "name": d["district_name"],
                "type": d.get("district_type", ""),
            }
            for d in page
        ],
        "total": total,
    }


@router.get("/{district_code}/risk")
def get_risk_analysis(
    district_code: str,
    industry_code: str = Query("CS100010", description="업종 코드"),
) -> dict[str, Any]:
    """폐업 위험도 분석."""
    from ..services.data_service import get_data_service, estimate_rent
    from ..services.risk_service import analyze_risk
    from ..services.scorecard_service import get_scorecard_service

    svc = get_data_service(industry_code=industry_code)
    district = svc.get_district(district_code)
    if not district:
        raise HTTPException(404, "상권을 찾을 수 없습니다")

    sc_svc = get_scorecard_service(industry_code)
    score = sc_svc.score_district(district)

    monthly_sales = district.get("monthly_sales", 0)
    store_count = max(district.get("store_count", 1), 1)
    est_rent = estimate_rent(
        district.get("district_type", "골목상권"),
        monthly_sales // store_count,
        score.get("percentile", 50) / 100,
        industry_code=industry_code,
    )

    return analyze_risk(district, est_rent)


@router.get("/{district_code}/briefing")
async def get_ai_briefing(
    district_code: str,
    industry_code: str = Query("CS100010", description="업종 코드"),
) -> dict[str, Any]:
    """AI 실시간 상권 브리핑 — 종합 데이터 기반 4~6문장 해석."""
    from ..services.data_service import get_data_service, estimate_rent
    from ..services.risk_service import analyze_risk
    from ..services.scorecard_service import get_scorecard_service

    svc = get_data_service(industry_code=industry_code)
    district = svc.get_district(district_code)
    if not district:
        raise HTTPException(404, "상권을 찾을 수 없습니다")

    sc_svc = get_scorecard_service(industry_code)
    score = sc_svc.score_district(district)

    monthly_sales = district.get("monthly_sales", 0)
    store_count = max(district.get("store_count", 1), 1)
    sps = monthly_sales // store_count
    est_rent = estimate_rent(
        district.get("district_type", "골목상권"),
        sps,
        score.get("percentile", 50) / 100,
        industry_code=industry_code,
    )

    risk = analyze_risk(district, est_rent)

    # Gemini 브리핑
    briefing_text = ""
    try:
        from google import genai

        client = genai.Client()
        prompt = f"""당신은 상권 분석 전문 컨설턴트입니다.
아래 데이터를 바탕으로 {svc.display_name} 업종 예비 창업자에게 이 상권에 대한 핵심 브리핑을 해주세요.

상권: {district.get('district_name', '')} ({district.get('district_type', '')})
종합점수: {score.get('total_score', 0)}점 (상위 {score.get('percentile', 50):.0f}%)
점포당 월매출: {sps:,}원
추정 임대료: {est_rent:,}원
생존율: {district.get('survival_rate', 0):.0%}
경쟁 점포: {store_count}개
유동인구: {district.get('foot_traffic_total', 0):,}명/분기
주요 고객층: {district.get('main_age_group', '')}
피크 시간대: {district.get('peak_time', '')}
위험도: {risk['risk_score']}점 ({risk['risk_level']})

4~6문장으로 다음을 포함하여 브리핑하세요:
1) 이 상권의 한 줄 평가
2) 가장 큰 강점 1개
3) 가장 큰 약점 또는 주의점 1개
4) 구체적 추천 전략 1개

마크다운 없이 자연스러운 구어체로 작성하세요."""

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
        )
        if response.text:
            briefing_text = response.text.strip()
    except Exception:
        pass

    # 폴백
    if not briefing_text:
        total = score.get("total_score", 0)
        grade = "우수" if total >= 75 else "보통" if total >= 50 else "취약"
        briefing_text = (
            f"{district.get('district_name', '')} 상권은 종합 {total}점으로 {grade} 등급입니다. "
            f"점포당 월매출 {sps // 10000:,}만원, 생존율 {district.get('survival_rate', 0):.0%}입니다. "
            f"{'주의가 필요한 상권입니다. 대안 상권 비교를 권장합니다.' if risk['risk_level'] == 'high' else '세부 분석을 확인하세요.'}"
        )

    return {
        "briefing": briefing_text,
        "summary": {
            "total_score": score.get("total_score", 0),
            "risk_score": risk["risk_score"],
            "risk_level": risk["risk_level"],
            "sales_per_store": sps,
            "estimated_rent": est_rent,
            "survival_rate": district.get("survival_rate", 0),
        },
    }
