"""
AI 사업계획서 자동 생성 API — Gemini 2.5 Flash v3

9개 섹션: 사업개요, 상권시장분석, 경쟁환경, 메뉴가격전략, 마케팅전략, 재무계획, 리스크분석, 실행로드맵, 프랜차이즈vs독립창업
모든 섹션 Gemini Flash 연동 (실패 시 룰 기반 fallback).
asyncio.gather로 섹션 2-9 병렬 생성.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv  # type: ignore[import-not-found]
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.services.data_service import get_data_service, estimate_rent
from api.services.simulation_service import get_simulation_service
from api.services.scorecard_service import get_scorecard_service
from api.services.competitive_analysis_service import get_competitive_analysis_service
from config.industry_config import load_industry_config, DEFAULT_INDUSTRY

# .env 로드
_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

logger = logging.getLogger(__name__)

try:
    from google import genai  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    genai = None  # type: ignore[assignment]

router = APIRouter(prefix="/business-plan")

# ---------------------------------------------------------------------------
# Gemini client singleton
# ---------------------------------------------------------------------------

_gemini_client: object | None = None


def _get_gemini_client() -> object | None:
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client
    if GEMINI_API_KEY and genai is not None:
        try:
            _gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception:
            logger.exception("Gemini client 초기화 실패")
    return _gemini_client


GEMINI_MODEL = "gemini-2.5-flash"

# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------


class BusinessPlanRequest(BaseModel):
    industry_code: str = Field(default="CS100010", description="업종 코드")
    district_code: str = Field(..., description="상권 코드")
    budget: int = Field(..., ge=1000, le=100000, description="총 예산 (만원)")
    area_pyeong: int = Field(default=15, ge=5, le=100, description="매장 면적(평)")
    business_name: Optional[str] = Field(default=None, description="상호명")
    target_customers: Optional[str] = Field(default=None, description="타겟 고객")


class SectionResponse(BaseModel):
    id: str
    title: str
    content: str
    data: Optional[dict[str, Any]] = None


class BusinessPlanResponse(BaseModel):
    business_name: str
    district_name: str
    industry_name: str
    sections: list[SectionResponse]
    generated_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fmt(v: int | float) -> str:
    """Format number with commas."""
    return f"{int(v):,}"


def _fmt_man(v: int | float) -> str:
    """Format won to 만원."""
    m = int(v) // 10_000
    return f"{m:,}만원"


def _fmt_man_raw(v: int | float) -> str:
    """Format 만원 value (already in 만원 unit)."""
    return f"{int(v):,}만원"


def _pct(v: float) -> str:
    return f"{v:.1f}%"


def _change_indicator_text(code: str) -> str:
    mapping = {
        "HH": "성장 상권 (매출 증가, 점포 증가)",
        "HL": "안정 상권 (매출 증가, 점포 감소 — 점포당 수익 개선)",
        "LH": "과포화 위험 상권 (매출 감소, 점포 증가)",
        "LL": "쇠퇴 상권 (매출 감소, 점포 감소)",
    }
    return mapping.get(code, "데이터 없음")


# ---------------------------------------------------------------------------
# Gemini helper — async wrapper for sync SDK call
# ---------------------------------------------------------------------------


async def _gemini_generate(prompt: str) -> str | None:
    """Call Gemini Flash and return text. Returns None on failure."""
    client = _get_gemini_client()
    if client is None:
        return None
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(  # type: ignore[union-attr]
                model=GEMINI_MODEL,
                contents=prompt,
            ),
        )
        return response.text or None  # type: ignore[union-attr]
    except Exception as exc:
        logger.warning("Gemini 호출 실패: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Data extraction helpers for prompts
# ---------------------------------------------------------------------------


def _extract_time_pcts(district: dict[str, Any]) -> dict[str, float]:
    """Extract time-slot sales percentages."""
    monthly_sales = max(1, district.get("monthly_sales", 1))
    time_fields = [
        ("새벽(0-6시)", "time_00_06_sales"),
        ("아침(6-11시)", "time_06_11_sales"),
        ("점심(11-14시)", "time_11_14_sales"),
        ("오후(14-17시)", "time_14_17_sales"),
        ("저녁(17-21시)", "time_17_21_sales"),
        ("밤(21-24시)", "time_21_24_sales"),
    ]
    result: dict[str, float] = {}
    for label, field in time_fields:
        val = district.get(field, 0)
        result[label] = round(val / monthly_sales * 100, 1) if isinstance(val, (int, float)) else 0.0
    return result


def _extract_age_pcts(district: dict[str, Any]) -> dict[str, float]:
    """Extract age-group sales percentages."""
    monthly_sales = max(1, district.get("monthly_sales", 1))
    age_fields = [
        ("10대", "age_10_sales"), ("20대", "age_20_sales"), ("30대", "age_30_sales"),
        ("40대", "age_40_sales"), ("50대", "age_50_sales"), ("60대+", "age_60_sales"),
    ]
    result: dict[str, float] = {}
    for label, field in age_fields:
        val = district.get(field, 0)
        result[label] = round(val / monthly_sales * 100, 1) if isinstance(val, (int, float)) else 0.0
    return result


def _extract_menu_analysis(config: dict[str, Any]) -> dict[str, Any]:
    """Extract and analyze menu cost data by category."""
    menu_costs = config.get("MENU_COSTS", {})
    if not menu_costs:
        return {}

    categories: dict[str, list[dict[str, Any]]] = {}
    all_items: list[dict[str, Any]] = []
    for name, data in menu_costs.items():
        cat = data.get("category", "기타")
        sp = data.get("selling_price", 0)
        tc = data.get("total_cost", 0)
        margin = sp - tc
        mr = margin / max(1, sp) * 100
        item = {"name": name, "category": cat, "selling_price": sp, "total_cost": tc,
                "margin": margin, "margin_rate": mr}
        categories.setdefault(cat, []).append(item)
        all_items.append(item)

    cat_analysis: dict[str, dict[str, Any]] = {}
    for cat, items in categories.items():
        avg_mr = sum(i["margin_rate"] for i in items) / len(items)
        avg_sp = sum(i["selling_price"] for i in items) / len(items)
        avg_tc = sum(i["total_cost"] for i in items) / len(items)
        cat_analysis[cat] = {
            "count": len(items), "avg_margin_rate": round(avg_mr, 1),
            "avg_selling_price": round(avg_sp), "avg_total_cost": round(avg_tc),
            "items": items,
        }

    sorted_items = sorted(all_items, key=lambda x: x["margin_rate"], reverse=True)
    return {
        "all_items": all_items, "categories": cat_analysis,
        "best_margin": sorted_items[0] if sorted_items else None,
        "worst_margin": sorted_items[-1] if sorted_items else None,
        "avg_margin_rate": round(sum(i["margin_rate"] for i in all_items) / max(1, len(all_items)), 1),
    }


# ---------------------------------------------------------------------------
# Section 1: 사업 개요 (룰 기반 — 정형 테이블)
# ---------------------------------------------------------------------------


def _section_overview(
    district: dict[str, Any],
    config: dict[str, Any],
    business_name: str,
    industry_name: str,
    area_pyeong: int,
    budget: int,
    target_customers: str | None,
) -> SectionResponse:
    """Section 1: 사업 개요"""
    district_name = district["district_name"]
    district_type = district["district_type"]

    target = target_customers or f"{district.get('main_age_group', '30대')} 중심"

    content = f"""## 사업 개요

| 항목 | 내용 |
|------|------|
| **상호명** | {business_name} |
| **업종** | {industry_name} |
| **입지** | 서울특별시 {district_name} ({district_type}) |
| **매장 면적** | {area_pyeong}평 (약 {int(area_pyeong * 3.3)}㎡) |
| **총 예산** | {_fmt_man_raw(budget)}  |
| **타겟 고객** | {target} |

### 사업 컨셉

{district_type} 입지의 {district_name}에 위치한 **{business_name}**은(는) \
{target}을 대상으로 하는 {industry_name} 매장입니다. \
{area_pyeong}평 규모로 총 예산 {_fmt_man_raw(budget)} 내에서 운영을 목표로 합니다.
"""

    return SectionResponse(
        id="overview",
        title="1. 사업 개요",
        content=content,
        data={
            "business_name": business_name,
            "industry": industry_name,
            "district_name": district_name,
            "district_type": district_type,
            "area_pyeong": area_pyeong,
            "budget_man": budget,
        },
    )


# ---------------------------------------------------------------------------
# Section 2: 상권·시장 분석 (Gemini + fallback)
# ---------------------------------------------------------------------------


def _section_market_analysis_fallback(district: dict[str, Any]) -> str:
    """Fallback rule-based market analysis."""
    name = district["district_name"]
    dtype = district["district_type"]
    ft = district.get("foot_traffic_total", 0)
    resident = district.get("resident_total", 0)
    worker = district.get("worker_total", 0)
    peak_time = district.get("peak_time", "11-14")
    peak_day = district.get("peak_day", "금")
    main_age = district.get("main_age_group", "30대")
    male_r = district.get("male_ratio", 0.5) * 100
    female_r = district.get("female_ratio", 0.5) * 100
    change_code = district.get("change_indicator_code", "")
    monthly_sales = district.get("monthly_sales", 0)

    time_labels = [
        ("새벽 (0-6시)", "time_00_06_sales"),
        ("아침 (6-11시)", "time_06_11_sales"),
        ("점심 (11-14시)", "time_11_14_sales"),
        ("오후 (14-17시)", "time_14_17_sales"),
        ("저녁 (17-21시)", "time_17_21_sales"),
        ("밤 (21-24시)", "time_21_24_sales"),
    ]
    time_rows = ""
    for label, key in time_labels:
        val = district.get(key, 0)
        pct = val / max(1, monthly_sales) * 100
        time_rows += f"| {label} | {_pct(pct)} |\n"

    age_labels = [
        ("10대", "age_10_sales"), ("20대", "age_20_sales"), ("30대", "age_30_sales"),
        ("40대", "age_40_sales"), ("50대", "age_50_sales"), ("60대+", "age_60_sales"),
    ]
    age_rows = ""
    for label, key in age_labels:
        val = district.get(key, 0)
        pct = val / max(1, monthly_sales) * 100
        age_rows += f"| {label} | {_pct(pct)} |\n"

    return f"""## 상권·시장 분석

### 상권 기본 정보

{name}은(는) **{dtype}** 유형의 상권으로, 다음과 같은 특성을 보입니다.

| 지표 | 수치 |
|------|------|
| **유동인구** | {_fmt(ft)}명/분기 |
| **거주인구** | {_fmt(resident)}명 |
| **직장인구** | {_fmt(worker)}명 |
| **피크 시간대** | {peak_time}시 |
| **피크 요일** | {peak_day}요일 |
| **상권변화지표** | {_change_indicator_text(change_code)} |

### 시간대별 매출 비중

| 시간대 | 비중 |
|--------|------|
{time_rows}
### 고객 분석

- **주요 연령대**: {main_age}
- **성별 비율**: 남성 {_pct(male_r)} / 여성 {_pct(female_r)}

| 연령대 | 매출 비중 |
|--------|----------|
{age_rows}"""


async def _section_market_analysis(
    district: dict[str, Any],
    industry_name: str,
) -> SectionResponse:
    """Section 2: 상권·시장 분석 — Gemini enhanced."""
    name = district["district_name"]
    dtype = district["district_type"]
    ft = district.get("foot_traffic_total", 0)
    resident = district.get("resident_total", 0)
    worker = district.get("worker_total", 0)
    peak_time = district.get("peak_time", "11-14")
    peak_day = district.get("peak_day", "금")
    main_age = district.get("main_age_group", "30대")
    change_code = district.get("change_indicator_code", "")
    monthly_sales = district.get("monthly_sales", 0)
    sc = max(1, district.get("store_count", 1))
    weekday_r = district.get("weekday_ratio", 0.7) * 100
    weekend_r = district.get("weekend_ratio", 0.3) * 100

    time_pcts = _extract_time_pcts(district)
    age_pcts = _extract_age_pcts(district)

    time_str = ", ".join(f"{k} {v}%" for k, v in time_pcts.items())
    age_str = ", ".join(f"{k} {v}%" for k, v in age_pcts.items())

    prompt = f"""당신은 맥킨지 수준의 창업 컨설턴트입니다. 아래 데이터를 분석해서 상권·시장 분석 섹션을 작성하세요.

업종: {industry_name}
상권: {name} ({dtype})
유동인구: {_fmt(ft)}명/분기
거주인구: {_fmt(resident)}명, 직장인구: {_fmt(worker)}명
피크 시간대: {peak_time}시, 피크 요일: {peak_day}요일
주요 연령대: {main_age}
시간대별 매출비중: {time_str}
연령대별 매출비중: {age_str}
상권변화지표: {_change_indicator_text(change_code)} ({change_code})
월매출 총액: {_fmt(monthly_sales)}원, 점포수: {sc}개, 점포당 월매출: {_fmt(monthly_sales // sc)}원
평일/주말 매출비중: 평일 {_pct(weekday_r)} / 주말 {_pct(weekend_r)}

분석 요구사항:
1. 핵심 고객층을 데이터 기반으로 규명하고 그 이유를 구체적으로 설명하세요.
2. 시간대별 매출 패턴에서 기회와 위험 요인을 도출하세요.
3. 유동인구, 거주인구, 직장인구 비율에서 상권 특성과 고객 동선을 분석하세요.
4. 상권 성장성/안정성을 상권변화지표 기반으로 평가하세요.
5. 구체적인 영업 전략 시사점을 3가지 이상 제시하세요 (예: "점심 피크에 테이크아웃 세트 메뉴로 직장인 공략").
6. 마크다운 형식으로 작성하세요. 제목(##)은 쓰지 마세요 — 본문만 작성하세요.
7. 최소 500자 이상 작성하세요.
8. 데이터 수치를 적극 인용하며 분석 근거를 명확히 하세요."""

    ai_text = await _gemini_generate(prompt)

    if ai_text:
        fallback = _section_market_analysis_fallback(district)
        content = fallback + "\n\n### AI 전문 분석\n\n" + ai_text.strip()
    else:
        content = _section_market_analysis_fallback(district)

    return SectionResponse(
        id="market",
        title="2. 상권·시장 분석",
        content=content,
        data={
            "foot_traffic": ft,
            "resident_total": resident,
            "worker_total": worker,
            "peak_time": peak_time,
            "peak_day": peak_day,
            "main_age_group": main_age,
            "change_indicator": change_code,
        },
    )


# ---------------------------------------------------------------------------
# Section 3: 경쟁 환경 (Gemini + fallback)
# ---------------------------------------------------------------------------


def _section_competition_fallback(
    district: dict[str, Any],
    industry_name: str,
) -> str:
    """Fallback rule-based competition analysis."""
    sc = district.get("store_count", 0)
    new_s = district.get("new_stores", 0)
    closed_s = district.get("closed_stores", 0)
    franchise_s = district.get("franchise_stores", 0)
    franchise_r = franchise_s / max(1, sc) * 100
    survival = min(district.get("survival_rate", 0), 1.0) * 100
    closed_r = closed_s / max(1, sc) * 100
    monthly_sales = district.get("monthly_sales", 0)
    per_store = monthly_sales // max(1, sc)

    net_change = new_s - closed_s
    trend = "증가 추세" if net_change > 0 else ("감소 추세" if net_change < 0 else "유지")

    if sc <= 5:
        comp_level = "낮음 (블루오션)"
    elif sc <= 15:
        comp_level = "보통"
    elif sc <= 25:
        comp_level = "높음"
    else:
        comp_level = "매우 높음 (레드오션)"

    content = f"""## 경쟁 환경 분석

### 경쟁 현황

| 지표 | 수치 | 해석 |
|------|------|------|
| **{industry_name} 점포수** | {sc}개 | 경쟁 강도: {comp_level} |
| **프랜차이즈 비율** | {_pct(franchise_r)} ({franchise_s}개) | {'프랜차이즈 밀집' if franchise_r > 50 else '개인 매장 다수'} |
| **신규 개업** | {new_s}개 | - |
| **폐업** | {closed_s}개 | - |
| **순 증감** | {'+' if net_change > 0 else ''}{net_change}개 | {trend} |
| **생존율 (2년)** | {_pct(survival)} | {'양호' if survival >= 70 else '주의 필요'} |
| **폐업률** | {_pct(closed_r)} | {'안정적' if closed_r < 10 else '높음'} |
| **점포당 월매출** | {_fmt(per_store)}원 | - |
"""
    hints = []
    if franchise_r > 50:
        hints.append(f"- 프랜차이즈 비율이 {_pct(franchise_r)}로 높아, **차별화된 컨셉과 메뉴**로 승부해야 합니다.")
    if sc > 20:
        hints.append(f"- 점포 밀집도가 높아({sc}개) **가격 경쟁력** 또는 **특화 전략**이 필수적입니다.")
    if closed_s > new_s:
        hints.append("- 폐업이 개업보다 많은 상권입니다. **철저한 리스크 관리**가 필요합니다.")
    if survival >= 80:
        hints.append("- 생존율이 높아 안정적인 상권입니다. **기본에 충실한 운영**이 중요합니다.")
    if net_change > 0:
        hints.append("- 점포가 증가 추세여서 **초기 고객 확보 속도**가 관건입니다.")
    if hints:
        content += "\n### 경쟁 전략 시사점\n\n" + "\n".join(hints) + "\n"

    return content


async def _section_competition(
    district: dict[str, Any],
    industry_name: str,
) -> SectionResponse:
    """Section 3: 경쟁 환경 — Gemini enhanced."""
    sc = district.get("store_count", 0)
    new_s = district.get("new_stores", 0)
    closed_s = district.get("closed_stores", 0)
    franchise_s = district.get("franchise_stores", 0)
    franchise_r = franchise_s / max(1, sc) * 100
    survival = min(district.get("survival_rate", 0), 1.0) * 100
    monthly_sales = district.get("monthly_sales", 0)
    per_store = monthly_sales // max(1, sc)

    name = district["district_name"]
    dtype = district["district_type"]
    main_age = district.get("main_age_group", "30대")
    peak_time = district.get("peak_time", "11-14")
    worker = district.get("worker_total", 0)
    resident = district.get("resident_total", 0)

    prompt = f"""당신은 맥킨지 수준의 창업 컨설턴트입니다. 아래 데이터를 분석해서 경쟁 환경 분석과 구체적 차별화 전략을 작성하세요.

업종: {industry_name}
상권: {name} ({dtype})
동종 업종 점포수: {sc}개
프랜차이즈: {franchise_s}개 ({_pct(franchise_r)})
신규 개업: {new_s}개, 폐업: {closed_s}개 (순증감: {new_s - closed_s}개)
2년 생존율: {_pct(survival)}
점포당 월매출: {_fmt(per_store)}원
주요 고객 연령대: {main_age}
피크 시간대: {peak_time}시
직장인구: {_fmt(worker)}명, 거주인구: {_fmt(resident)}명

분석 요구사항:
1. 경쟁 강도를 구체적으로 평가하세요 (점포 밀집도, 프랜차이즈 vs 개인 비율, 신규/폐업 추세).
2. 프랜차이즈 대비 개인 매장의 강점/약점을 분석하세요.
3. **반드시 구체적인 차별화 전략 5가지 이상**을 제안하세요. 각 전략은 실행 가능한 수준으로 상세하게:
   - 메뉴 차별화: 어떤 메뉴를 어떻게 (예: 스페셜티 원두, 시그니처 음료, 로컬 식재료 활용)
   - 시간대 차별화: 경쟁사가 약한 시간대를 구체적으로 공략 (예: 아침 7시 오픈으로 출근길 수요 선점)
   - 공간/경험 차별화: 구체적 컨셉 (예: 작업 친화적 카페 — 콘센트 전석 배치+화이트보드, 반려동물 동반 카페)
   - 타겟 차별화: 해당 상권의 인구 특성을 반영한 타겟 전략 (예: 직장인 테이크아웃 특화, 주부 디저트 카페)
   - 서비스 차별화: 구독/멤버십, 클래스, 커뮤니티 등
4. 각 차별화 전략별 예상 효과(매출 증가율, 고객 확보 등)를 언급하세요.
5. 마크다운 형식으로 작성하세요. 제목(##)은 쓰지 마세요 — 본문과 ###소제목만 사용하세요.
6. 최소 600자 이상 작성하세요."""

    ai_text = await _gemini_generate(prompt)

    if ai_text:
        fallback = _section_competition_fallback(district, industry_name)
        content = fallback + "\n### AI 경쟁 분석 및 차별화 전략\n\n" + ai_text.strip()
    else:
        content = _section_competition_fallback(district, industry_name)

    return SectionResponse(
        id="competition",
        title="3. 경쟁 환경",
        content=content,
        data={
            "store_count": sc,
            "franchise_ratio": round(franchise_r, 1),
            "new_stores": new_s,
            "closed_stores": closed_s,
            "survival_rate": round(survival, 1),
        },
    )


# ---------------------------------------------------------------------------
# Section 4: 메뉴·가격 전략 (Gemini + fallback — 카테고리별 마진 분석)
# ---------------------------------------------------------------------------


async def _section_menu_pricing(
    config: dict[str, Any],
    industry_name: str,
    district: dict[str, Any],
) -> SectionResponse:
    """Section 4: 메뉴·가격 전략 — Gemini enhanced + 카테고리별 분석."""
    menu_data = _extract_menu_analysis(config)
    menu_costs = config.get("MENU_COSTS", {})
    main_age = district.get("main_age_group", "30대")
    peak_time = district.get("peak_time", "11-14")
    worker = district.get("worker_total", 0)

    if not menu_data:
        content = f"""## 메뉴·가격 전략

{industry_name} 업종의 메뉴 원가 데이터가 준비 중입니다. 일반적으로 식재료 원가율 30~35%를 목표로 가격을 책정하시기 바랍니다.
"""
        return SectionResponse(id="menu", title="4. 메뉴·가격 전략", content=content)

    all_items = menu_data["all_items"]
    categories = menu_data["categories"]
    best = menu_data["best_margin"]
    worst = menu_data["worst_margin"]
    avg_mr = menu_data["avg_margin_rate"]

    # Build tables
    rows = ""
    for item in all_items:
        rows += f"| {item['name']} | {item['category']} | {_fmt(item['selling_price'])}원 | {_fmt(item['total_cost'])}원 | {_fmt(item['margin'])}원 | {_pct(item['margin_rate'])} |\n"

    cat_rows = ""
    for cat, info in categories.items():
        cat_rows += f"| **{cat}** | {info['count']}종 | {_fmt(info['avg_selling_price'])}원 | {_fmt(info['avg_total_cost'])}원 | {_pct(info['avg_margin_rate'])} |\n"

    base_table = f"""## 메뉴·가격 전략

### 메뉴별 원가 분석

| 메뉴 | 카테고리 | 판매가 | 원가 | 마진 | 마진율 |
|------|----------|--------|------|------|--------|
{rows}
### 카테고리별 분석

| 카테고리 | 메뉴 수 | 평균 판매가 | 평균 원가 | 평균 마진율 |
|----------|---------|-------------|-----------|-------------|
{cat_rows}
- **전체 평균 마진율**: {_pct(avg_mr)}
- **최고 마진 메뉴**: {best['name']} ({_pct(best['margin_rate'])})
- **최저 마진 메뉴**: {worst['name']} ({_pct(worst['margin_rate'])})
"""

    # Build category summary for Gemini
    cat_lines = []
    for cat, info in categories.items():
        items_list = ", ".join(f"{i['name']}({_pct(i['margin_rate'])})" for i in info["items"])
        cat_lines.append(f"- {cat}: 평균 마진율 {_pct(info['avg_margin_rate'])}, 평균 판매가 {_fmt(info['avg_selling_price'])}원, {info['count']}종 ({items_list})")
    cat_text = "\n".join(cat_lines)

    prompt = f"""당신은 {industry_name} 메뉴 전략 컨설턴트입니다. 아래 원가 데이터를 바탕으로 메뉴·가격 전략을 제안해주세요.

[원가 데이터]
- 전체 평균 마진율: {_pct(avg_mr)}
- 최고 마진 메뉴: {best['name']} (마진율 {_pct(best['margin_rate'])}, 판매가 {_fmt(best['selling_price'])}원, 원가 {_fmt(best['total_cost'])}원)
- 최저 마진 메뉴: {worst['name']} (마진율 {_pct(worst['margin_rate'])}, 판매가 {_fmt(worst['selling_price'])}원, 원가 {_fmt(worst['total_cost'])}원)

[카테고리별 분석]
{cat_text}

[상권 특성]
- 주요 고객: {main_age}
- 피크 시간대: {peak_time}시
- 직장인구: {_fmt(worker)}명

[작성 지침]
1. **카테고리별 마진 분석**: 각 카테고리(커피/음료/디저트 등)의 수익성을 비교 분석하세요.
2. **원가율 최적화 전략**: 식재료 원가율 30% 이하로 관리하기 위한 구체적 방안을 제시하세요.
3. **추천 메뉴 믹스**: 고마진 메뉴와 저마진 미끼 메뉴의 최적 조합을 제안하세요.
4. **세트 메뉴 전략**: 객단가 상승을 위한 구체적인 세트 구성안을 제시하세요 (이 메뉴와 저 메뉴를 묶어서 가격은 이렇게).
5. **계절별/시간대별 메뉴 운영 전략**을 제시하세요.
6. 마크다운 형식, 최소 500자 이상, 제목(##)은 쓰지 마세요."""

    ai_text = await _gemini_generate(prompt)

    if ai_text:
        content = base_table + "\n### AI 메뉴 전략 분석\n\n" + ai_text.strip()
    else:
        # Enhanced fallback
        content = base_table + f"""
### 메뉴 전략 제언

**1. 주력 메뉴 배치**: 마진율이 가장 높은 **{best['name']}**({_pct(best['margin_rate'])})을 POP 광고와 메뉴판 상단에 배치하여 주문 유도율을 높이세요. 마진 {_fmt(best['margin'])}원은 일 100잔 기준 월 {_fmt(best['margin'] * 100 * 30)}원의 수익 차이를 만듭니다.

**2. 세트 구성 전략**: 마진이 낮은 **{worst['name']}**은(는) 단독 판매보다 고마진 음료와 세트로 묶어 평균 객단가를 상승시키세요. 예를 들어 '{best['name']} + {worst['name']}' 세트를 개별 합계보다 500~1,000원 할인하면 세트 주문율이 올라가고 전체 마진은 개선됩니다.

**3. 원가율 관리**: 전체 평균 마진율 {_pct(avg_mr)}{'는 업계 평균(65~70%) 수준입니다.' if avg_mr >= 65 else '는 업계 평균(65~70%)보다 낮아 개선이 필요합니다. 대량구매 계약, 시즌 식재료 활용, 레시피 원가 최적화를 추진하세요.'}

**4. 시간대별 메뉴**: 피크 시간({peak_time}시)에는 빠른 서비스가 가능한 메뉴 위주로, 비피크 시간에는 고마진 디저트+음료 세트를 프로모션하세요.

**5. 시즌 메뉴**: 분기별 한정 메뉴(봄: 딸기 라떼, 여름: 에이드류, 가을: 단호박 라떼, 겨울: 핫초코)를 운영하여 재방문율을 높이고 SNS 바이럴을 유도하세요. 시즌 메뉴는 원가율 25% 이하로 설계하여 수익성 확보가 가능합니다."""

    return SectionResponse(
        id="menu",
        title="4. 메뉴·가격 전략",
        content=content,
        data={
            "avg_margin_rate": avg_mr,
            "menu_count": len(all_items),
            "best_margin_menu": best["name"] if best else "-",
            "categories": {cat: info["avg_margin_rate"] for cat, info in categories.items()},
        },
    )


# ---------------------------------------------------------------------------
# Section 5: 마케팅 전략 (Gemini + fallback)
# ---------------------------------------------------------------------------


def _section_marketing_fallback(
    district: dict[str, Any],
    industry_name: str,
    target_customers: str | None,
) -> str:
    """Fallback rule-based marketing strategy."""
    peak_time = district.get("peak_time", "11-14")
    main_age = district.get("main_age_group", "30대")
    female_r = district.get("female_ratio", 0.5) * 100
    worker = district.get("worker_total", 0)
    resident = district.get("resident_total", 0)
    weekend_r = district.get("weekend_ratio", 0.3) * 100
    target = target_customers or main_age

    strategies = []
    if "20" in main_age or "30" in main_age:
        strategies.append("**SNS 마케팅**: 인스타그램 릴스/스토리 + 네이버 플레이스 리뷰 관리.")
    else:
        strategies.append("**지역 밀착 마케팅**: 네이버 플레이스 최적화 + 당근마켓 동네 홍보.")
    if peak_time in ("06-11", "11-14"):
        strategies.append(f"**모닝/런치 특화**: 피크 시간대({peak_time}시) 집중 프로모션.")
    if worker > 3000:
        strategies.append(f"**직장인 공략**: 직장인구 {_fmt(worker)}명 밀집 지역. 법인 주문 할인.")
    if resident > 1000:
        strategies.append(f"**단골 확보**: 거주인구 {_fmt(resident)}명 대상 멤버십 프로그램.")
    if female_r > 60:
        strategies.append("**여성 타겟**: 인테리어/포토존 투자와 SNS 바이럴.")
    if weekend_r > 35:
        strategies.append(f"**주말 프로모션**: 주말 매출 비중 {_pct(weekend_r)}로 높음.")

    strategy_text = "\n".join(f"{i+1}. {s}" for i, s in enumerate(strategies[:6]))

    return f"""## 마케팅 전략

### 타겟 고객
- **1차 타겟**: {target}
- **주요 연령대**: {main_age}
- **성별 비율**: 남성 {_pct(100 - female_r)} / 여성 {_pct(female_r)}

### 핵심 마케팅 전략
{strategy_text}

### 오픈 마케팅 (1개월)
1. **오픈 전**: 네이버 플레이스 등록 + 인스타그램 티저 콘텐츠 (D-14)
2. **오픈 당일**: 선착순 할인(50%) + SNS 인증샷 이벤트
3. **오픈 1주차**: 리뷰 이벤트 (리뷰 작성 시 음료 1잔 무료)
4. **오픈 1개월**: 스탬프 카드 도입 + 단골 확보 전략 전환
"""


async def _section_marketing(
    district: dict[str, Any],
    industry_name: str,
    target_customers: str | None,
) -> SectionResponse:
    """Section 5: 마케팅 전략 — Gemini enhanced."""
    name = district["district_name"]
    dtype = district["district_type"]
    peak_time = district.get("peak_time", "11-14")
    peak_day = district.get("peak_day", "금")
    main_age = district.get("main_age_group", "30대")
    male_r = district.get("male_ratio", 0.5) * 100
    female_r = district.get("female_ratio", 0.5) * 100
    worker = district.get("worker_total", 0)
    resident = district.get("resident_total", 0)
    weekday_r = district.get("weekday_ratio", 0.7) * 100
    weekend_r = district.get("weekend_ratio", 0.3) * 100
    target = target_customers or main_age
    sc = max(1, district.get("store_count", 1))
    monthly_sales = district.get("monthly_sales", 0)

    time_pcts = _extract_time_pcts(district)
    age_pcts = _extract_age_pcts(district)
    time_str = ", ".join(f"{k} {v}%" for k, v in time_pcts.items())
    age_str = ", ".join(f"{k} {v}%" for k, v in age_pcts.items())

    prompt = f"""당신은 맥킨지 수준의 마케팅 전략 컨설턴트입니다. 아래 데이터를 기반으로 {industry_name} 매장의 구체적인 마케팅 전략을 작성하세요.

업종: {industry_name}
상권: {name} ({dtype})
타겟 고객: {target}
주요 연령대: {main_age}
성별 비율: 남성 {_pct(male_r)} / 여성 {_pct(female_r)}
유동인구: {_fmt(district.get('foot_traffic_total', 0))}명/분기
직장인구: {_fmt(worker)}명, 거주인구: {_fmt(resident)}명
피크 시간대: {peak_time}시, 피크 요일: {peak_day}요일
시간대별 매출비중: {time_str}
연령대별 매출비중: {age_str}
평일/주말 비율: 평일 {_pct(weekday_r)} / 주말 {_pct(weekend_r)}
경쟁 점포: {sc}개, 점포당 월매출: {_fmt(monthly_sales // sc)}원

작성 요구사항:
1. "SNS 마케팅을 합니다" 같은 뻔한 내용 금지. 데이터에 근거한 구체적 전략만 작성하세요.
2. 타겟 연령대 + 시간대 + 지역 특성을 모두 반영한 전략을 작성하세요.
3. 아래 4가지 카테고리별로 각 2개 이상의 구체적 실행 방안을 제시하세요:
   - **오프라인 마케팅**: 상권 특성에 맞는 현장 마케팅 (예: 직장인 밀집 지역이면 "오전 8~9시 출근길 시음 이벤트 — 주 3회, 역 출구 앞")
   - **온라인/디지털 마케팅**: 타겟 연령에 맞는 채널과 콘텐츠 전략 (예: "20~30대 여성 타겟 → 인스타 릴스 주 3회: 음료 제조 과정 ASMR + 감성 인테리어 컷")
   - **프로모션/CRM**: 고객 확보와 리텐션 전략 (예: "런치타임 직장인 스탬프: 5잔 무료 1잔 → 월 평균 재방문 4.2회 목표")
   - **시간대별 전략**: 약한 시간대 매출 보강 방안 (데이터에서 비중 낮은 시간대를 공략)
4. 각 전략별 예상 비용과 ROI 추정치를 포함하세요.
5. 오픈 후 90일 마케팅 로드맵을 주차별로 구성하세요.
6. 마크다운 형식. 제목(##)은 쓰지 마세요 — ###소제목과 본문만 사용하세요.
7. 최소 600자 이상 작성하세요."""

    ai_text = await _gemini_generate(prompt)

    if ai_text:
        header = f"""## 마케팅 전략

### 타겟 고객
- **1차 타겟**: {target}
- **주요 연령대**: {main_age}
- **성별 비율**: 남성 {_pct(100 - female_r)} / 여성 {_pct(female_r)}

"""
        content = header + ai_text.strip()
    else:
        content = _section_marketing_fallback(district, industry_name, target_customers)

    return SectionResponse(
        id="marketing",
        title="5. 마케팅 전략",
        content=content,
        data={
            "target_customers": target,
            "peak_time": peak_time,
            "strategy_count": 4,
        },
    )


# ---------------------------------------------------------------------------
# Section 6: 재무 계획 (Gemini + fallback — 캐시플로우/상세분석 추가)
# ---------------------------------------------------------------------------


async def _section_financials(
    sim_result: dict[str, Any],
    budget: int,
    district: dict[str, Any],
    industry_name: str,
) -> SectionResponse:
    """Section 6: 재무 계획 — Gemini enhanced + 캐시플로우 + 리스크 시나리오."""
    revenue = sim_result["revenue"]
    startup = sim_result["startup_cost"]
    operating = sim_result["operating_cost"]
    be = sim_result["break_even"]

    monthly_rev = revenue["monthly_sales_per_store"]
    monthly_net = be["monthly_net_profit"]

    pessimistic_rev = revenue["pessimistic"]
    optimistic_rev = revenue["optimistic"]

    y1_monthly = int(monthly_rev * 0.8)
    y2_monthly = monthly_rev
    y3_monthly = int(monthly_rev * 1.05)

    y1_annual = y1_monthly * 12
    y2_annual = y2_monthly * 12
    y3_annual = y3_monthly * 12

    op_total = operating["total"]
    y1_net = (y1_monthly - op_total) * 12
    y2_net = (y2_monthly - op_total) * 12
    y3_net = (y3_monthly - int(op_total * 1.03)) * 12

    budget_diff = budget * 10000 - startup["total_min"]
    budget_ok = budget_diff >= 0

    # Monthly cashflow table
    ramp_rates = [0.4, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0, 1.0, 1.0]
    cashflow_rows = ""
    cumulative = -startup["total_min"]
    for i, rate in enumerate(ramp_rates):
        m_rev = int(monthly_rev * rate)
        m_cost = op_total
        m_net = m_rev - m_cost
        cumulative += m_net
        cashflow_rows += f"| {i+1}개월 | {_fmt_man(m_rev)} | {_fmt_man(m_cost)} | {_fmt_man(m_net)} | {_fmt_man(cumulative)} |\n"

    # Risk scenarios
    risk_70 = int(monthly_rev * 0.7) - op_total
    risk_50 = int(monthly_rev * 0.5) - op_total
    reserve = budget_diff if budget_ok else 0
    survive_70 = int(reserve / max(1, abs(risk_70))) if risk_70 < 0 else 99
    survive_50 = int(reserve / max(1, abs(risk_50))) if risk_50 < 0 else 99

    base_content = f"""## 재무 계획

### 초기 투자비용

| 항목 | 금액 | 비중 |
|------|------|------|
| **보증금** | {_fmt_man(startup['deposit'])} | {_pct(startup['deposit'] / max(1, startup['total_min']) * 100)} |
| **인테리어** | {_fmt_man(startup['interior'])} | {_pct(startup['interior'] / max(1, startup['total_min']) * 100)} |
| **장비/설비** | {_fmt_man(startup['equipment_min'])} ~ {_fmt_man(startup['equipment_max'])} | - |
| **초도물품** | {_fmt_man(startup['initial_inventory_min'])} ~ {_fmt_man(startup['initial_inventory_max'])} | - |
| **인허가/기타** | {_fmt_man(startup['permits_misc_min'])} ~ {_fmt_man(startup['permits_misc_max'])} | - |
| **합계** | **{_fmt_man(startup['total_min'])} ~ {_fmt_man(startup['total_max'])}** | 100% |

> 총 예산 {_fmt_man_raw(budget)} 대비 투자비용 {_fmt_man(startup['total_min'])} ~ {_fmt_man(startup['total_max'])} \
({'**예산 내 가능** — 여유 자금 ' + _fmt_man(budget_diff) + '은 운영자금으로 확보하세요.' if budget_ok else '**예산 초과** — ' + _fmt_man(abs(budget_diff)) + ' 추가 확보 또는 비용 절감이 필요합니다.'})

### 월간 운영비

| 항목 | 금액 | 비중 | 적정 범위 |
|------|------|------|-----------|
| **임대료** | {_fmt_man(operating['rent'])} | {_pct(operating['rent'] / max(1, op_total) * 100)} | 매출의 10~15% |
| **식재료/원재료** | {_fmt_man(operating['cogs'])} | {_pct(operating['cogs'] / max(1, op_total) * 100)} | 매출의 25~35% |
| **인건비** | {_fmt_man(operating['labor'])} | {_pct(operating['labor'] / max(1, op_total) * 100)} | 매출의 25~30% |
| **공과금** | {_fmt_man(operating['utilities'])} | {_pct(operating['utilities'] / max(1, op_total) * 100)} | 매출의 3~5% |
| **기타** | {_fmt_man(operating['other'])} | {_pct(operating['other'] / max(1, op_total) * 100)} | 매출의 5~10% |
| **합계** | **{_fmt_man(op_total)}** | 100% | - |

### 손익분기점

| 지표 | 수치 |
|------|------|
| **예상 월매출** | {_fmt_man(monthly_rev)} |
| **월 운영비** | {_fmt_man(op_total)} |
| **월 순이익** | {_fmt_man(monthly_net)} |
| **순이익률** | {_pct(be['net_profit_margin'] * 100)} |
| **투자 회수 기간** | {be['break_even_months_min']}~{be['break_even_months_max']}개월 |
| **일 손익분기 매출** | {_fmt_man(be['daily_break_even_sales'])} |

### 3개년 매출 전망

| 구분 | 1년차 | 2년차 | 3년차 |
|------|-------|-------|-------|
| **월매출(평균)** | {_fmt_man(y1_monthly)} | {_fmt_man(y2_monthly)} | {_fmt_man(y3_monthly)} |
| **연매출** | {_fmt_man(y1_annual)} | {_fmt_man(y2_annual)} | {_fmt_man(y3_annual)} |
| **연 순이익** | {_fmt_man(y1_net)} | {_fmt_man(y2_net)} | {_fmt_man(y3_net)} |

> 비관적 시나리오 월매출: {_fmt_man(pessimistic_rev)} / 낙관적: {_fmt_man(optimistic_rev)}

### 월별 캐시플로우 (1년차)

| 월 | 매출 | 운영비 | 순이익 | 누적 손익 |
|----|------|--------|--------|-----------|
{cashflow_rows}
### 리스크 시나리오

| 시나리오 | 월매출 | 월 순이익 | 비고 |
|----------|--------|-----------|------|
| **낙관적 (120%)** | {_fmt_man(int(monthly_rev * 1.2))} | {_fmt_man(int(monthly_rev * 1.2) - op_total)} | 안정적 수익 |
| **기본** | {_fmt_man(monthly_rev)} | {_fmt_man(monthly_net)} | 예상치 |
| **보수적 (70%)** | {_fmt_man(int(monthly_rev * 0.7))} | {_fmt_man(risk_70)} | {'적자 — 여유자금으로 약 ' + str(survive_70) + '개월 버틸 수 있음' if risk_70 < 0 else '흑자 유지'} |
| **위기 (50%)** | {_fmt_man(int(monthly_rev * 0.5))} | {_fmt_man(risk_50)} | {'적자 — 여유자금으로 약 ' + str(survive_50) + '개월 버틸 수 있음' if risk_50 < 0 else '흑자 유지'} |
"""

    # Gemini prompt
    rent_ratio = operating['rent'] / max(1, monthly_rev) * 100
    cogs_ratio = operating['cogs'] / max(1, monthly_rev) * 100
    labor_ratio = operating['labor'] / max(1, monthly_rev) * 100

    prompt = f"""당신은 {industry_name} 창업 재무 컨설턴트입니다. 아래 재무 데이터를 바탕으로 상세한 재무 분석과 조언을 작성해주세요.

[재무 데이터]
- 총 예산: {_fmt_man_raw(budget)}
- 초기 투자비: {_fmt_man(startup['total_min'])} ~ {_fmt_man(startup['total_max'])} (예산 대비 {_fmt_man(abs(budget_diff))} {'여유' if budget_ok else '부족'})
- 월 예상매출: {_fmt_man(monthly_rev)} / 월 운영비: {_fmt_man(op_total)} / 월 순이익: {_fmt_man(monthly_net)}
- 임대료 비율: {_pct(rent_ratio)} / 식재료 원가율: {_pct(cogs_ratio)} / 인건비 비율: {_pct(labor_ratio)}
- 순이익률: {_pct(be['net_profit_margin'] * 100)}
- 투자 회수: {be['break_even_months_min']}~{be['break_even_months_max']}개월
- 비관적 매출: {_fmt_man(pessimistic_rev)} / 낙관적: {_fmt_man(optimistic_rev)}
- 보수적(70%) 시나리오 월 순이익: {_fmt_man(risk_70)}

[작성 지침]
1. 각 **투자비 항목의 근거** (왜 이 금액인지, 업계 평균 대비 적정한지)를 설명하세요.
2. 각 **운영비 항목 상세 분석** (적정 비율인지, 구체적 절감 포인트 3가지 이상)을 제시하세요.
3. **예산 {'부족' if not budget_ok else '여유자금 활용'} 방안**을 구체적으로 제시하세요.
   {'- 중고 장비, 셀프 인테리어, 정부 지원금, 임대료 협상 등' if not budget_ok else '- 운영자금 확보, 마케팅 투자, 비상금 비율 등'}
4. **월별 캐시플로우 해석** (언제 흑자 전환하는지, 운전자금은 얼마나 필요한지)
5. **리스크 시나리오별 대응 전략** (매출 70%, 50% 시 구체적 대응)
6. 마크다운 형식, 최소 500자 이상, 제목(##)은 쓰지 마세요."""

    ai_text = await _gemini_generate(prompt)

    if ai_text:
        content = base_content + "\n### AI 재무 분석\n\n" + ai_text.strip()
    else:
        # Fallback
        budget_advice = ""
        if not budget_ok:
            budget_advice = f"""

### 예산 부족 대응 방안

예산이 약 {_fmt_man(abs(budget_diff))} 부족합니다. 다음 방안을 검토하세요:

1. **인테리어 절감**: 셀프 인테리어/부분 시공으로 30~40% 절감 가능 (약 {_fmt_man(int(startup['interior'] * 0.35))} 절약)
2. **중고 장비 활용**: 커피머신, 냉장고 등 중고 구입 시 40~50% 절감
3. **정부 지원금**: 소상공인진흥공단 정책자금(연 2~3%, 최대 1억원) 활용
4. **소규모 오픈**: 초기 메뉴를 핵심 5~10종으로 축소하여 초도물품비 절감
5. **임대료 협상**: 프리렌트(1~3개월 무상임대) 또는 보증금-월세 전환 협상"""

        content = base_content + f"""
### 운영비 상세 분석

- **임대료** {_fmt_man(operating['rent'])} (매출 대비 {_pct(rent_ratio)}) — {'적정 범위(10~15%)입니다.' if 10 <= rent_ratio <= 15 else '적정 범위(10~15%)를 벗어납니다. 임대료 협상 또는 입지 재검토를 고려하세요.'}
- **식재료 원가율** {_pct(cogs_ratio)} — {'양호합니다. 대량 구매 계약으로 추가 절감이 가능합니다.' if cogs_ratio <= 35 else '높은 편입니다. 대량구매 계약, 시즌 식재료 활용, 레시피 원가 최적화를 추진하세요.'}
- **인건비** {_fmt_man(operating['labor'])} (매출 대비 {_pct(labor_ratio)}) — {'적정합니다.' if labor_ratio <= 30 else '높은 편입니다. 피크 시간대 집중 배치, 셀프서비스 도입, POS 자동화를 검토하세요.'}
- **공과금** {_fmt_man(operating['utilities'])} — 절전 LED, 인버터 에어컨 등으로 월 10~15% 절감 가능합니다.

> **권장**: 보수적 시나리오(70%)에서도 최소 6개월은 버틸 수 있는 운영자금({_fmt_man(abs(risk_70) * 6) if risk_70 < 0 else '이미 흑자'})을 확보한 후 오픈하세요.{budget_advice}"""

    return SectionResponse(
        id="financials",
        title="6. 재무 계획",
        content=content,
        data={
            "startup_total_min": startup["total_min"],
            "startup_total_max": startup["total_max"],
            "monthly_revenue": monthly_rev,
            "monthly_operating_cost": op_total,
            "monthly_net_profit": monthly_net,
            "break_even_months_min": be["break_even_months_min"],
            "break_even_months_max": be["break_even_months_max"],
            "budget_man": budget,
            "budget_ok": budget_ok,
        },
    )


# ---------------------------------------------------------------------------
# Section 7: 리스크 분석 (Gemini + fallback)
# ---------------------------------------------------------------------------


def _section_risk_fallback(
    district: dict[str, Any],
    sim_result: dict[str, Any],
    scorecard: dict[str, Any] | None,
) -> str:
    """Fallback rule-based risk analysis."""
    risks = sim_result.get("risk_summary", [])
    survival = min(district.get("survival_rate", 0), 1.0) * 100
    sc = district.get("store_count", 0)
    closed = district.get("closed_stores", 0)
    new = district.get("new_stores", 0)
    change_code = district.get("change_indicator_code", "")

    risk_score = 0
    if survival < 60:
        risk_score += 3
    elif survival < 70:
        risk_score += 2
    elif survival < 80:
        risk_score += 1
    if sc > 25:
        risk_score += 2
    elif sc > 15:
        risk_score += 1
    if closed > new:
        risk_score += 2
    if change_code == "LL":
        risk_score += 2
    elif change_code == "LH":
        risk_score += 1

    if risk_score >= 6:
        risk_level = "높음"
    elif risk_score >= 3:
        risk_level = "보통"
    else:
        risk_level = "낮음"

    scorecard_text = ""
    if scorecard and scorecard.get("categories"):
        scorecard_text = "\n### 스코어카드 평가\n\n| 영역 | 점수 |\n|------|------|\n"
        for cat in scorecard["categories"]:
            scorecard_text += f"| {cat['name']} | {cat['score']}/100 |\n"
        total = scorecard.get("total_score", 0)
        scorecard_text += f"| **종합** | **{total}/100** |\n"

    risk_items = "\n".join(f"- {r}" for r in risks) if risks else "- 주요 리스크 요인이 감지되지 않았습니다."

    mitigations = []
    if survival < 75:
        mitigations.append("**생존율 관리**: 최소 6개월 운영자금 확보, 초기 3개월 집중 마케팅으로 고객 기반 조기 구축")
    if sc > 15:
        mitigations.append("**경쟁 차별화**: 시그니처 메뉴 개발, 고유한 브랜드 아이덴티티 구축, 프랜차이즈 대비 독자적 경험 제공")
    if closed > new:
        mitigations.append("**방어적 전략**: 손익분기 달성까지 비용 최소화, 임대료 협상 강화, 메뉴를 핵심 아이템으로 집중")
    if change_code in ("LL", "LH"):
        mitigations.append("**상권 변화 대응**: 배달/테이크아웃 비중 확대, 온라인 채널(스마트스토어/구독) 강화, 임대료 재협상 카드 활용")
    if not mitigations:
        mitigations.append("**지속 성장**: 고객 리텐션 강화, 분기별 메뉴 혁신, 경쟁 점포 동향 모니터링으로 장기 경쟁력 확보")
    mitigation_text = "\n".join(f"{i+1}. {m}" for i, m in enumerate(mitigations))

    return f"""## 리스크 분석

### 종합 리스크 등급: {'🔴' if risk_level == '높음' else '🟡' if risk_level == '보통' else '🟢'} {risk_level} (위험도 {risk_score}/10)

### 주요 리스크 요인

{risk_items}
{scorecard_text}

### 리스크 대응 방안

{mitigation_text}
"""


async def _section_risk(
    district: dict[str, Any],
    sim_result: dict[str, Any],
    scorecard: dict[str, Any] | None,
    industry_name: str,
    budget: int,
) -> SectionResponse:
    """Section 7: 리스크 분석 — Gemini enhanced."""
    risks = sim_result.get("risk_summary", [])
    survival = min(district.get("survival_rate", 0), 1.0) * 100
    sc = district.get("store_count", 0)
    closed = district.get("closed_stores", 0)
    new = district.get("new_stores", 0)
    change_code = district.get("change_indicator_code", "")
    name = district["district_name"]
    dtype = district["district_type"]
    franchise_r = district.get("franchise_stores", 0) / max(1, sc) * 100

    # Risk level calculation (same as fallback)
    risk_score = 0
    if survival < 60:
        risk_score += 3
    elif survival < 70:
        risk_score += 2
    elif survival < 80:
        risk_score += 1
    if sc > 25:
        risk_score += 2
    elif sc > 15:
        risk_score += 1
    if closed > new:
        risk_score += 2
    if change_code == "LL":
        risk_score += 2
    elif change_code == "LH":
        risk_score += 1

    if risk_score >= 6:
        risk_level = "높음"
    elif risk_score >= 3:
        risk_level = "보통"
    else:
        risk_level = "낮음"

    # Financial data
    revenue = sim_result.get("revenue", {})
    operating = sim_result.get("operating_cost", {})
    be = sim_result.get("break_even", {})
    monthly_rev = revenue.get("monthly_sales_per_store", 0)
    monthly_net = be.get("monthly_net_profit", 0)
    be_months_min = be.get("break_even_months_min", 0)
    be_months_max = be.get("break_even_months_max", 0)

    scorecard_summary = ""
    if scorecard and scorecard.get("categories"):
        parts = [f"{cat['name']}({cat['score']}점)" for cat in scorecard["categories"]]
        scorecard_summary = f"스코어카드: {', '.join(parts)}, 종합 {scorecard.get('total_score', 0)}점"

    risk_list_str = "\n".join(f"- {r}" for r in risks) if risks else "특별한 리스크 감지되지 않음"

    prompt = f"""당신은 맥킨지 수준의 창업 리스크 분석 컨설턴트입니다. 아래 데이터를 기반으로 리스크 분석을 작성하세요.

업종: {industry_name}
상권: {name} ({dtype})
종합 리스크 등급: {risk_level} (점수 {risk_score}/10)
2년 생존율: {_pct(survival)}
동종 업종 점포수: {sc}개, 프랜차이즈 비율: {_pct(franchise_r)}
신규 개업: {new}개, 폐업: {closed}개
상권변화지표: {_change_indicator_text(change_code)} ({change_code})
예상 월매출: {_fmt_man(monthly_rev)}, 월 순이익: {_fmt_man(monthly_net)}
투자 회수: {be_months_min}~{be_months_max}개월
총 예산: {_fmt_man_raw(budget)}
기존 감지된 리스크:
{risk_list_str}
{scorecard_summary}

분석 요구사항:
1. 아래 5가지 리스크 카테고리별로 각각 구체적 수치 근거와 함께 분석하세요:
   - **시장 리스크**: 상권 변화, 경기 침체, 트렌드 변화
   - **경쟁 리스크**: 신규 진입자, 대형 프랜차이즈 확장, 가격 전쟁
   - **재무 리스크**: 초기 자금 소진, 매출 부진, 고정비 부담
   - **운영 리스크**: 인력 관리, 식재료 원가 상승, 시설 유지보수
   - **외부 리스크**: 정책 변화, 임대료 인상, 재개발
2. 각 리스크별 **구체적 대응 전략 3가지**를 수치 근거와 함께 작성하세요.
   예: "월 순이익의 20%를 비상금으로 적립 → 6개월 내 약 XX만원 확보"
3. 리스크 발생 시 **단계별 대응 프로토콜** (경고→주의→위기)을 제시하세요.
4. 마크다운 형식. 제목(##)은 쓰지 마세요 — ###소제목과 본문만 사용하세요.
5. 최소 600자 이상 작성하세요."""

    ai_text = await _gemini_generate(prompt)

    if ai_text:
        fallback = _section_risk_fallback(district, sim_result, scorecard)
        content = fallback + "\n### AI 리스크 심층 분석\n\n" + ai_text.strip()
    else:
        content = _section_risk_fallback(district, sim_result, scorecard)

    return SectionResponse(
        id="risk",
        title="7. 리스크 분석",
        content=content,
        data={
            "risk_level": risk_level,
            "risk_score": risk_score,
            "survival_rate": round(survival, 1),
            "scorecard_total": scorecard.get("total_score") if scorecard else None,
        },
    )


# ---------------------------------------------------------------------------
# Section 8: 실행 로드맵 + 정부지원사업 (Gemini + fallback)
# ---------------------------------------------------------------------------


async def _section_roadmap(
    industry_name: str,
    budget: int,
) -> SectionResponse:
    """Section 8: 실행 로드맵 + 정부지원사업 안내."""

    base_roadmap = f"""## 실행 로드맵

### 90일 창업 체크리스트

#### Phase 1: 준비기 (D-90 ~ D-60)

| 기간 | 항목 | 상세 |
|------|------|------|
| 1주차 | 사업자등록 | 관할 세무서에 사업자등록 신청 |
| 1~2주차 | 입지 계약 | 임대차 계약 체결, 권리금 협상 |
| 2~3주차 | 인허가 | 영업신고증(식품위생법), 소방안전점검 |
| 3~4주차 | 인테리어 설계 | 컨셉 확정, 시공업체 선정, 견적 비교 (3곳 이상) |

#### Phase 2: 시공기 (D-60 ~ D-30)

| 기간 | 항목 | 상세 |
|------|------|------|
| 5~6주차 | 인테리어 시공 | 공사 진행, 주 2회 현장 확인 |
| 6~7주차 | 장비 발주 | 주요 설비/가구 발주 및 설치 |
| 7~8주차 | 메뉴 확정 | 레시피 테스트, 원가 계산, 가격 확정 |
| 8주차 | 직원 채용 | 아르바이트/직원 채용, 교육 준비 |

#### Phase 3: 오픈 준비 (D-30 ~ D-day)

| 기간 | 항목 | 상세 |
|------|------|------|
| 9주차 | 시운전 | 장비 테스트, 동선 최적화 |
| 10주차 | 직원 교육 | 서비스 매뉴얼, POS 교육, 위생 교육 |
| 11주차 | 사전 마케팅 | 네이버 플레이스 등록, SNS 티저 |
| 12주차 | 프리오픈 | 지인 초대 시운전 → 피드백 반영 |
| D-day | **그랜드 오픈** | 오픈 이벤트 시행 |

#### Phase 4: 안정화 (D+1 ~ D+30)

| 기간 | 항목 | 상세 |
|------|------|------|
| 1주차 | 운영 모니터링 | 일매출 추적, 고객 피드백 수집 |
| 2주차 | 메뉴 조정 | 판매 데이터 기반 메뉴 조정 |
| 3~4주차 | 마케팅 강화 | 리뷰 이벤트, 스탬프 카드 도입 |

"""

    gov_support = """### 정부지원사업 안내

창업 과정에서 활용 가능한 주요 정부지원 프로그램입니다.

#### 1. 소상공인진흥공단 — 신사업창업사관학교

| 항목 | 내용 |
|------|------|
| **지원 내용** | 창업 교육(이론+실습) + 사업화 자금 지원 |
| **지원 금액** | 교육비 전액 무료 + 사업화 자금 최대 1,000만원 |
| **신청 시기** | 매년 1~2월 모집 (상·하반기 각 1회) |
| **자격 요건** | 예비 창업자 또는 창업 1년 이내 소상공인 |
| **신청 방법** | 소상공인마당(sbiz.or.kr) 온라인 접수 |

#### 2. 소상공인 정책자금 (직접대출)

| 항목 | 내용 |
|------|------|
| **지원 내용** | 저금리 직접 대출 (시설자금, 운영자금) |
| **지원 금액** | 업체당 최대 1억원 (운영자금 7천만원, 시설자금 1억원) |
| **금리** | 연 2~3.5% (정책금리 연동) |
| **신청 시기** | 연중 수시 (예산 소진 시 마감) |
| **자격 요건** | 소상공인 확인서 보유, 사업자등록 후 신청 |
| **신청 방법** | 소상공인마당(sbiz.or.kr) → 소상공인정책자금 |

#### 3. 서울시 자영업지원센터

| 항목 | 내용 |
|------|------|
| **지원 내용** | 무료 경영 컨설팅, 창업 교육, 상권 분석 |
| **지원 금액** | 컨설팅 무료 (회당 2~4시간, 최대 5회) |
| **신청 시기** | 연중 수시 |
| **자격 요건** | 서울시 소재 예비 창업자 또는 기존 자영업자 |
| **신청 방법** | 서울시 자영업지원센터(secc.seoul.go.kr) 또는 전화 |

#### 4. 소상공인 역량강화 사업

| 항목 | 내용 |
|------|------|
| **지원 내용** | 업종 전환 교육, 디지털 마케팅 교육, 경영개선 컨설팅 |
| **지원 금액** | 교육비 전액 지원 (연간 최대 300만원 상당) |
| **신청 시기** | 연 2회 (상·하반기) |
| **자격 요건** | 소상공인 또는 예비 창업자 |
| **신청 방법** | 소상공인마당(sbiz.or.kr) |

#### 5. 서울신용보증재단 — 소상공인 보증지원

| 항목 | 내용 |
|------|------|
| **지원 내용** | 신용보증서 발급 → 시중은행 대출 연계 |
| **보증 금액** | 업체당 최대 8천만원 (창업 초기 기업 우대) |
| **보증료** | 연 0.5~1.0% |
| **신청 시기** | 연중 수시 |
| **자격 요건** | 서울시 소재 소상공인, 사업자등록 후 신청 |
| **신청 방법** | 서울신용보증재단 방문 또는 온라인 |

> **추천 활용 순서**: ① 자영업지원센터 무료 컨설팅 → ② 신사업창업사관학교 교육 → ③ 소상공인 정책자금 신청 → ④ 필요 시 신용보증재단 보증 대출
"""

    prompt = f"""당신은 {industry_name} 창업 전문 컨설턴트입니다.

예산 {_fmt_man_raw(budget)}으로 {industry_name} 창업을 준비하는 예비 창업자에게 다음을 작성해주세요:

1. 90일 창업 준비 과정에서 특히 주의해야 할 포인트와 실무 팁
2. 각 단계(준비기/시공기/오픈준비/안정화)별 흔한 실수와 방지법
3. 정부지원사업 활용 전략 — 어떤 순서로, 어떤 시기에, 어떻게 신청하면 좋은지 구체적 가이드
4. 위 지원사업 외에 {industry_name} 업종에 특화된 추가 지원 프로그램이 있다면 소개

마크다운 형식. 제목(##)은 쓰지 마세요. ###소제목과 본문만 사용하세요.
최소 500자 이상."""

    ai_text = await _gemini_generate(prompt)

    if ai_text:
        content = base_roadmap + gov_support + "\n### AI 창업 실무 가이드\n\n" + ai_text.strip()
    else:
        content = base_roadmap + gov_support

    return SectionResponse(
        id="roadmap",
        title="8. 실행 로드맵",
        content=content,
        data={
            "total_days": 90,
            "phases": ["준비기", "시공기", "오픈 준비", "안정화"],
            "government_programs": 5,
        },
    )


# ---------------------------------------------------------------------------
# Section 9: 프랜차이즈 vs 독립창업 비교 (NEW — Gemini + fallback)
# ---------------------------------------------------------------------------


async def _section_franchise_comparison(
    sim_result: dict[str, Any],
    industry_name: str,
    budget: int,
    district: dict[str, Any],
) -> SectionResponse:
    """Section 9: 프랜차이즈 vs 독립창업 비교 — franchise_benchmark 활용."""
    franchise_bm = sim_result.get("franchise_benchmark", {})
    startup = sim_result["startup_cost"]
    monthly_rev = sim_result["revenue"]["monthly_sales_per_store"]
    op_total = sim_result["operating_cost"]["total"]
    has_franchise = bool(franchise_bm and franchise_bm.get("startup_costs"))

    franchise_startup_costs = franchise_bm.get("startup_costs", [])
    avg_franchise_total = franchise_bm.get("avg_total_startup_cost", 0)
    brand_count = franchise_bm.get("brand_count", 0)
    franchise_store_count = franchise_bm.get("store_count", 0)
    source = franchise_bm.get("source", "")

    independent_total = startup["total_min"]
    diff = avg_franchise_total - independent_total if avg_franchise_total > 0 else 0
    diff_text = f"프랜차이즈가 {_fmt_man(abs(diff))} {'더 비쌈' if diff > 0 else '더 저렴'}" if diff != 0 else "비슷한 수준"

    franchise_local_r = district.get("franchise_stores", 0) / max(1, district.get("store_count", 1)) * 100

    # Franchise table
    franchise_table = ""
    if has_franchise:
        franchise_table = "\n### 프랜차이즈 업종별 평균 창업비용\n\n"
        franchise_table += "| 업종 | 가맹금 | 가맹비(교육) | 기타 가입비 | 합계 |\n"
        franchise_table += "|------|--------|-------------|------------|------|\n"
        for cost in franchise_startup_costs[:10]:
            franchise_table += (
                f"| {cost.get('name', '-')} "
                f"| {_fmt_man(cost.get('franchise_fee', 0))} "
                f"| {_fmt_man(cost.get('education_fee', 0))} "
                f"| {_fmt_man(cost.get('other_fee', 0))} "
                f"| {_fmt_man(cost.get('total_joining_cost', 0))} |\n"
            )
        if source:
            franchise_table += f"\n> 출처: {source}\n"

    base_content = f"""## 프랜차이즈 vs 독립창업 비교

### 비용 비교 요약

| 구분 | 독립창업 | 프랜차이즈 (평균) |
|------|----------|-------------------|
| **총 가입비(가맹금+교육+기타)** | {_fmt_man(independent_total)} | {_fmt_man(avg_franchise_total) if avg_franchise_total else '데이터 없음'} |
| **가맹비/교육비** | 없음 | {'있음 (브랜드별 상이)' if has_franchise else '데이터 없음'} |
| **월 로열티** | 없음 | 매출의 2~5% (월 {_fmt_man(int(monthly_rev * 0.03))}~{_fmt_man(int(monthly_rev * 0.05))} 추정) |
| **메뉴 자율성** | 완전 자유 | 본사 규정 준수 |
| **브랜드 인지도** | 직접 구축 필요 | 즉시 활용 가능 |
| **상권 내 프랜차이즈 비율** | - | {_pct(franchise_local_r)} |

> {diff_text}
{franchise_table}
"""

    # Gemini prompt
    brand_details = ""
    if franchise_startup_costs:
        lines = [f"- {c.get('name')}: 합계 {_fmt_man(c.get('total_joining_cost', 0))}, 가맹금 {_fmt_man(c.get('franchise_fee', 0))}, 기타 {_fmt_man(c.get('other_fee', 0))}"
                 for c in franchise_startup_costs[:5]]
        brand_details = "브랜드별 상세:\n" + "\n".join(lines)

    prompt = f"""당신은 {industry_name} 창업 컨설턴트입니다. 프랜차이즈 창업과 독립 창업을 비교 분석해주세요.

[데이터]
- 업종: {industry_name}
- 독립창업 예상 비용: {_fmt_man(independent_total)}
- 프랜차이즈 평균 창업비용: {_fmt_man(avg_franchise_total) if avg_franchise_total else '데이터 없음'}
- 프랜차이즈 브랜드 수: {brand_count}개 / 총 매장 수: {_fmt(franchise_store_count)}개
- 예상 월매출: {_fmt_man(monthly_rev)} / 월 운영비: {_fmt_man(op_total)}
- 총 예산: {_fmt_man_raw(budget)}
- 상권 내 프랜차이즈 비율: {_pct(franchise_local_r)}
{brand_details}

[작성 지침]
1. **비용 비교**: 초기 투자비, 월 로열티/수수료, 5년간 총비용 비교
2. **프랜차이즈 장점 5가지**: 브랜드, 교육, 공급망, 마케팅, 리스크 감소 등 구체적으로
3. **프랜차이즈 단점 5가지**: 로열티, 자율성, 계약 조건, 가맹비 회수, 경업금지 등 구체적으로
4. **독립창업 장점 5가지**: 자율성, 수익, 브랜드 자산 등
5. **독립창업 단점 5가지**: 브랜드 구축, 노하우, 실패율 등
6. **이 상권에서의 최종 추천**: 프랜차이즈 비율, 예산, 상권 특성을 종합 고려한 구체적 추천
7. {'구체적 브랜드를 언급하며 비교 분석하세요.' if has_franchise else '일반적인 프랜차이즈 vs 독립 비교를 하세요.'}
8. 마크다운 형식, 최소 500자 이상, 제목(##)은 쓰지 마세요."""

    ai_text = await _gemini_generate(prompt)

    if ai_text:
        content = base_content + ai_text.strip()
    else:
        # Fallback
        content = base_content + f"""### 프랜차이즈 창업

**장점:**
- **브랜드 파워**: 오픈 첫날부터 인지도 활용 가능. 초기 고객 유입이 독립창업 대비 20~30% 유리합니다.
- **검증된 시스템**: 레시피, 운영 매뉴얼, 교육이 제공되어 창업 경험 없이도 운영이 가능합니다.
- **본사 마케팅**: 전국 광고, 앱 프로모션 등 대규모 마케팅 수혜를 받을 수 있습니다.
- **안정적 공급망**: 대량 구매로 원가 절감, 안정적 원재료 공급이 보장됩니다.
- **리스크 감소**: 검증된 사업 모델로 실패 확률이 상대적으로 낮습니다.

**단점:**
- **높은 초기 비용**: {'평균 ' + _fmt_man(avg_franchise_total) + '이 필요하며, 독립창업 대비 ' + diff_text + '입니다.' if avg_franchise_total else '가맹비, 교육비 등 추가 비용이 발생합니다.'}
- **로열티 부담**: 월매출의 2~5%(월 {_fmt_man(int(monthly_rev * 0.03))}~{_fmt_man(int(monthly_rev * 0.05))}) 지급으로 순이익 감소.
- **자율성 제한**: 메뉴, 가격, 인테리어, 영업시간 등 본사 규정을 따라야 합니다.
- **계약 리스크**: 해지 시 가맹비 미환불, 경업금지 조항(보통 2년) 등 주의가 필요합니다.
- **동일 상권 출점**: 같은 브랜드가 인근에 추가 출점할 수 있는 리스크가 있습니다.

### 독립창업

**장점:**
- **완전한 자율성**: 메뉴, 가격, 컨셉 등 모든 의사결정을 자유롭게 할 수 있습니다.
- **수익 전액 확보**: 로열티 없이 월 {_fmt_man(int(monthly_rev * 0.03))}~{_fmt_man(int(monthly_rev * 0.05))} 추가 수익.
- **브랜드 자산**: 성공 시 자체 브랜드 가치가 축적되며, 추후 다점포/프랜차이즈화 가능.
- **낮은 초기 비용**: 가맹비 없이 {_fmt_man(independent_total)}으로 시작 가능.
- **빠른 의사결정**: 시장 변화에 즉시 대응 가능 (메뉴 변경, 가격 조정 등).

**단점:**
- **브랜드 구축**: 인지도를 처음부터 쌓아야 하므로 초기 3~6개월 집중 마케팅이 필요합니다.
- **모든 것을 직접**: 메뉴 개발, 원재료 소싱, 운영 시스템 구축을 본인이 해결해야 합니다.
- **높은 실패율**: 프랜차이즈 대비 폐업률이 10~20%p 높은 것으로 알려져 있습니다.
- **공급망 불안정**: 소량 구매로 원가가 높고, 공급 안정성이 떨어질 수 있습니다.
- **마케팅 부담**: 모든 마케팅을 직접 기획하고 집행해야 합니다.

### 이 상권에서의 추천

현재 상권의 프랜차이즈 비율은 **{_pct(franchise_local_r)}**입니다.

"""
        if franchise_local_r > 50:
            content += ("프랜차이즈가 이미 밀집해 있어, **독립창업으로 차별화하는 전략**이 유리합니다. "
                        "프랜차이즈와 동일한 컨셉으로는 승산이 없으며, 스페셜티/시그니처 메뉴로 독자적 포지션을 확보하세요. "
                        "예산 대비 초기 투자비도 절감되어 운영자금 여유를 확보할 수 있습니다.")
        elif franchise_local_r > 30:
            content += ("프랜차이즈와 개인 매장이 혼재된 상권입니다. "
                        "**창업 경험이 적다면 프랜차이즈**, **업종 경험이 있다면 독립창업**을 추천합니다. "
                        "독립창업 시에는 프랜차이즈에 없는 독자적 경험(핸드드립 클래스, 원두 구독 등)을 제공하여 차별화하세요.")
        else:
            content += ("프랜차이즈 비율이 낮아 **양쪽 모두 기회가 있는 상권**입니다. "
                        "프랜차이즈 브랜드로 진입하면 첫 고객 확보가 수월하고, "
                        "독립창업으로 진입하면 경쟁이 적어 독자 브랜드 구축이 용이합니다. "
                        f"예산 {_fmt_man_raw(budget)}을 고려할 때 {'프랜차이즈도 충분히 가능합니다.' if budget * 10000 >= avg_franchise_total > 0 else '독립창업이 예산에 더 적합합니다.'}")

    return SectionResponse(
        id="franchise_comparison",
        title="9. 프랜차이즈 vs 독립창업 비교",
        content=content,
        data={
            "has_franchise_data": has_franchise,
            "independent_cost": independent_total,
            "franchise_avg_cost": avg_franchise_total,
            "brand_count": brand_count,
            "franchise_store_count": franchise_store_count,
            "local_franchise_ratio": round(franchise_local_r, 1),
        },
    )


# ---------------------------------------------------------------------------
# Main Endpoint
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=BusinessPlanResponse)
async def generate_business_plan(req: BusinessPlanRequest) -> BusinessPlanResponse:
    """사업계획서 자동 생성 — Gemini Flash v3 (9개 섹션, AI 분석 + 데이터 테이블)"""
    # 1. Load data service -> get district
    data_svc = get_data_service(req.industry_code)
    district = data_svc.get_district(req.district_code)
    if district is None:
        raise HTTPException(404, f"상권 코드 {req.district_code}를 찾을 수 없습니다")

    # 2. Load config
    try:
        config = load_industry_config(req.industry_code)
    except FileNotFoundError:
        config = {}

    industry_name = config.get("display_name", config.get("name", "카페"))
    district_name = district["district_name"]

    # 3. Business name default
    business_name = req.business_name or f"{industry_name} {district_name.split()[0]}"

    # 4. Simulation
    sim_svc = get_simulation_service(req.industry_code)
    sim_result = await sim_svc.simulate(
        district_code=req.district_code,
        area_pyeong=req.area_pyeong,
    )
    if sim_result is None:
        raise HTTPException(500, "시뮬레이션 실행에 실패했습니다")

    # 5. Scorecard
    scorecard = None
    try:
        sc_svc = get_scorecard_service(req.industry_code)
        if not sc_svc._districts:
            sc_svc.set_districts(data_svc.districts)
        scorecard = sc_svc.score_district(district)
    except Exception as e:
        logger.warning("Scorecard 계산 실패: %s", e)

    # 6. Section 1 (overview) — sync, no Gemini needed
    section_overview = _section_overview(
        district, config, business_name, industry_name,
        req.area_pyeong, req.budget, req.target_customers,
    )

    # 7. Sections 2-9 — all async, run in parallel via asyncio.gather
    _section_meta = [
        ("market", "2. 상권·시장 분석"),
        ("competition", "3. 경쟁 환경"),
        ("menu", "4. 메뉴·가격 전략"),
        ("marketing", "5. 마케팅 전략"),
        ("financials", "6. 재무 계획"),
        ("risk", "7. 리스크 분석"),
        ("roadmap", "8. 실행 로드맵"),
        ("franchise_comparison", "9. 프랜차이즈 vs 독립창업 비교"),
    ]

    results = await asyncio.gather(
        _section_market_analysis(district, industry_name),
        _section_competition(district, industry_name),
        _section_menu_pricing(config, industry_name, district),
        _section_marketing(district, industry_name, req.target_customers),
        _section_financials(sim_result, req.budget, district, industry_name),
        _section_risk(district, sim_result, scorecard, industry_name, req.budget),
        _section_roadmap(industry_name, req.budget),
        _section_franchise_comparison(sim_result, industry_name, req.budget, district),
        return_exceptions=True,
    )

    section_list = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            sec_id, sec_title = _section_meta[i]
            logger.error("섹션 %d 생성 실패: %s", i + 2, r)
            r = SectionResponse(
                id=sec_id,
                title=sec_title,
                content="이 섹션을 생성하지 못했습니다. 다시 시도해주세요.",
            )
        section_list.append(r)

    sections = [section_overview] + section_list

    return BusinessPlanResponse(
        business_name=business_name,
        district_name=district_name,
        industry_name=industry_name,
        sections=sections,
        generated_at=datetime.now().isoformat(),
    )
