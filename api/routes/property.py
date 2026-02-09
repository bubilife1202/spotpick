"""상가 매물 탐색 + 비용 비교 API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/property")


@router.get("/listings")
async def get_property_listings(
    district_code: str = Query(..., description="상권 코드"),
    industry_code: str = Query("CS100010", description="업종 코드"),
) -> dict[str, Any]:
    """추천 상권 근처 상가 매물 + 부동산 중개소 검색."""
    from ..services.data_service import get_data_service, estimate_rent
    from ..services.scorecard_service import get_scorecard_service
    from ..services.property_service import search_naver_properties, search_kakao_realtors

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

    district_name = district.get("district_name", "")
    gu_name = district.get("gu_name", "")
    search_query = f"{gu_name} {district_name}" if gu_name else district_name

    # 네이버 매물 검색
    naver_results = await search_naver_properties(search_query, display=10)

    # 카카오 부동산 중개소 검색 (좌표 기반)
    lat = district.get("latitude", district.get("lat", 0))
    lng = district.get("longitude", district.get("lng", 0))
    realtors = []
    if lat and lng:
        realtors = await search_kakao_realtors(lat, lng, radius=1000)

    return {
        "district_name": district_name,
        "district_type": district.get("district_type", ""),
        "estimated_rent": est_rent,
        "listings": naver_results,
        "realtors": realtors,
        "search_query": search_query,
        "listing_count": len(naver_results),
        "realtor_count": len(realtors),
    }


@router.get("/cost-compare")
async def cost_compare(
    industry_code: str = Query("CS100010", description="업종 코드"),
    monthly_rent: int = Query(0, description="월 임대료 (원)"),
    deposit: int = Query(0, description="보증금 (원)"),
    area_pyeong: int = Query(15, ge=5, le=100, description="면적 (평)"),
) -> dict[str, Any]:
    """프랜차이즈 vs 독립창업 비용 비교 + AI 추천."""
    from ..services.startup_cost_service import calc_independent_cost, calc_franchise_cost

    # 독립창업 비용
    independent = calc_independent_cost(
        industry_code, area_pyeong, deposit, monthly_rent,
    )

    # 프랜차이즈 비용 (공정위 API)
    franchise_data: dict[str, Any] = {}
    try:
        from ..services.franchise_data_service import get_franchise_benchmark
        benchmark = await get_franchise_benchmark(industry_code)
        costs = benchmark.get("startup_costs", {})
        if isinstance(costs, list) and len(costs) > 0:
            franchise_data = costs[0]
        elif isinstance(costs, dict):
            franchise_data = costs
    except Exception:
        pass

    franchise = calc_franchise_cost(
        franchise_data,
        area_pyeong,
        deposit,
        monthly_rent,
        interior_per_pyeong=independent["breakdown"]["interior"] // max(area_pyeong, 1),
    )

    difference = franchise["total_initial_cost"] - independent["total_initial_cost"]

    # AI 추천 생성
    verdict = await _generate_cost_verdict(
        industry_code, independent, franchise, difference,
    )

    return {
        "independent": independent,
        "franchise": franchise,
        "difference": difference,
        "cheaper": "independent" if difference > 0 else "franchise",
        "verdict": verdict,
        "params": {
            "industry_code": industry_code,
            "area_pyeong": area_pyeong,
            "monthly_rent": monthly_rent,
            "deposit": deposit,
        },
    }


async def _generate_cost_verdict(
    industry_code: str,
    independent: dict,
    franchise: dict,
    difference: int,
) -> str:
    """Gemini로 비용 비교 AI 판정 생성."""
    try:
        from google import genai

        client = genai.Client()
        ind_total = independent["total_initial_cost"]
        fran_total = franchise["total_initial_cost"]
        cheaper = "독립창업" if difference > 0 else "프랜차이즈"

        prompt = f"""창업 비용 비교 전문가입니다. 아래 데이터를 보고 3~4문장으로 추천을 해주세요.

독립창업 총비용: {ind_total:,}원
프랜차이즈 총비용: {fran_total:,}원
차액: {abs(difference):,}원 ({cheaper}이 저렴)
업종: {independent.get('industry_name', '')}

고려사항:
- 프랜차이즈: 브랜드 인지도, 본사 지원, 마케팅 포함
- 독립창업: 자유로운 운영, 로열티 없음, 브랜딩 직접

마크다운 없이 자연스러운 구어체로 작성하세요."""

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
        )
        if response.text:
            return response.text.strip()
    except Exception:
        pass

    # 폴백
    cheaper = "독립창업" if difference > 0 else "프랜차이즈"
    return (
        f"초기 투자금 기준으로 {cheaper}이 {abs(difference) // 10000:,}만원 저렴합니다. "
        f"프랜차이즈는 브랜드 인지도와 운영 노하우가 포함되어 있고, "
        f"독립창업은 자유로운 운영과 로열티 부담이 없다는 장점이 있습니다. "
        f"예산과 운영 경험을 고려하여 선택하세요."
    )
