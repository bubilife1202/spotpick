"""창업 타임라인 + 인허가 체크리스트 생성."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/timeline")

PERMITS_PATH = Path(__file__).resolve().parent.parent / "data" / "industry_permits.json"

_permits_cache: dict[str, Any] | None = None


def _load_permits() -> dict[str, Any]:
    global _permits_cache
    if _permits_cache is not None:
        return _permits_cache
    try:
        with open(PERMITS_PATH, encoding="utf-8") as f:
            _permits_cache = json.load(f)
            return _permits_cache
    except Exception:
        return {}


@router.get("/permits")
def get_permits(
    industry_code: str = Query("CS100010", description="업종 코드"),
) -> dict[str, Any]:
    """업종별 인허가 체크리스트 반환 (정적 데이터)."""
    permits = _load_permits()
    data = permits.get(industry_code)
    if not data:
        data = permits.get("CS100010", {"name": "", "permits": [], "notes": []})
    return data


@router.get("/generate")
async def generate_timeline(
    district_code: str = Query(..., description="상권 코드"),
    industry_code: str = Query("CS100010", description="업종 코드"),
    budget: int = Query(5000, description="총 예산 (만원)"),
) -> dict[str, Any]:
    """AI 기반 맞춤 창업 타임라인 생성."""
    from api.services.data_service import get_data_service, estimate_rent
    from api.services.scorecard_service import get_scorecard_service

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

    permits_data = _load_permits().get(industry_code, {})
    permits_list = permits_data.get("permits", [])
    notes = permits_data.get("notes", [])

    # Gemini 타임라인 생성
    timeline = await _generate_with_gemini(
        svc.display_name, district, est_rent, budget, permits_list,
    )
    if not timeline:
        timeline = _fallback_timeline(permits_list, est_rent, budget)

    return {
        "timeline": timeline,
        "permits": permits_list,
        "notes": notes,
        "summary": {
            "estimated_rent": est_rent,
            "budget_man": budget,
            "district_name": district.get("district_name", ""),
            "industry_name": svc.display_name,
        },
    }


async def _generate_with_gemini(
    industry_name: str, district: dict, est_rent: int,
    budget: int, permits_list: list,
) -> list[dict] | None:
    try:
        from google import genai

        client = genai.Client()
        permit_names = [p["name"] for p in permits_list]

        prompt = f"""창업 실행 타임라인을 JSON 배열로 생성하세요.

조건:
- 업종: {industry_name}
- 상권: {district.get('district_name', '')} ({district.get('district_type', '')})
- 예산: {budget}만원
- 추정 임대료: {est_rent:,}원/월
- 필요 인허가: {json.dumps(permit_names, ensure_ascii=False)}

D-90(오픈 90일 전)부터 D+90(오픈 후 90일)까지 12~15개 마일스톤을 생성하세요.
각 항목 형식: {{"day": -90, "title": "제목", "detail": "1줄 설명", "cost_man": 0, "duration": "3일", "category": "인허가|자금|시설|운영|마케팅"}}

JSON 배열만 반환하세요. 다른 텍스트 없이."""

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
        )
        text = (response.text or "").strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
        if isinstance(result, list) and len(result) > 0:
            return result
    except Exception:
        pass
    return None


def _fallback_timeline(permits: list, est_rent: int, budget: int) -> list[dict]:
    """Gemini 실패 시 규칙 기반 타임라인."""
    items: list[dict] = [
        {"day": -90, "title": "사업 구상 확정", "detail": "메뉴, 콘셉트, 타겟 고객 확정", "cost_man": 0, "duration": "7일", "category": "운영"},
        {"day": -80, "title": "자금 확보", "detail": "대출 상담, 정부 지원금 신청", "cost_man": 0, "duration": "14일", "category": "자금"},
        {"day": -75, "title": "점포 물색 및 계약", "detail": "임대차 계약 체결, 보증금 납부", "cost_man": int(est_rent / 10000 * 10), "duration": "14일", "category": "시설"},
        {"day": -60, "title": "인테리어 설계·시공", "detail": "도면 작성, 시공업체 선정, 착공", "cost_man": int(budget * 0.3), "duration": "30일", "category": "시설"},
    ]

    for p in permits:
        items.append({
            "day": -45 + (p.get("order", 1) - 1) * 5,
            "title": p["name"],
            "detail": f"{p.get('agency', '')} | 소요: {p.get('duration', '')}",
            "cost_man": (p.get("cost", 0) + 9999) // 10000,
            "duration": p.get("duration", "7일"),
            "category": "인허가",
        })

    items.extend([
        {"day": -14, "title": "장비 입고 및 설치", "detail": "주방 장비, 가구, 인테리어 마무리", "cost_man": int(budget * 0.15), "duration": "7일", "category": "시설"},
        {"day": -7, "title": "시범 운영 (소프트 오픈)", "detail": "지인 초대, 메뉴 최종 점검, 운영 리허설", "cost_man": 50, "duration": "7일", "category": "운영"},
        {"day": 0, "title": "정식 오픈", "detail": "그랜드 오픈 + 오픈 이벤트", "cost_man": 100, "duration": "1일", "category": "마케팅"},
        {"day": 30, "title": "1개월 운영 점검", "detail": "매출 분석, 메뉴 조정, 고객 피드백 반영", "cost_man": 0, "duration": "지속", "category": "운영"},
        {"day": 90, "title": "3개월 성과 평가", "detail": "손익분기 도달 여부 확인, 전략 수정", "cost_man": 0, "duration": "지속", "category": "운영"},
    ])

    return sorted(items, key=lambda x: x["day"])
