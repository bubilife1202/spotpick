"""
AI 사업계획서 자동 생성 API — Gemini Flash v2

8개 섹션: 사업개요, 상권시장분석, 경쟁환경, 메뉴가격전략, 마케팅전략, 재무계획, 리스크분석, 실행로드맵
섹션 2/3/5/7은 Gemini Flash가 데이터 기반 전문 분석 본문 생성.
섹션 1/4/6/8은 정형 데이터 표 기반 (룰 기반 유지).
Gemini 실패 시 기존 룰 기반 텍스트로 fallback.
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


GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"

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


# ---------------------------------------------------------------------------
# Section 1: 사업 개요 (룰 기반 유지 — 정형 테이블)
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
        # Prepend the data table, then AI analysis
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
주요 고객 연령대: {main_age}
피크 시간대: {peak_time}시
직장인구: {_fmt(worker)}명, 거주인구: {_fmt(resident)}명

분석 요구사항:
1. 경쟁 강도를 구체적으로 평가하세요 (점포 밀집도, 프랜차이즈 vs 개인 비율, 신규/폐업 추세).
2. 프랜차이즈 대비 개인 매장의 강점/약점을 분석하세요.
3. **반드시 구체적인 차별화 전략 4가지 이상**을 제안하세요. 각 전략은 실행 가능한 수준으로 상세하게:
   - 메뉴 차별화: 어떤 메뉴를 어떻게 (예: 스페셜티 원두, 시그니처 음료, 로컬 식재료 활용)
   - 시간대 차별화: 경쟁사가 약한 시간대를 구체적으로 공략 (예: 아침 7시 오픈으로 출근길 수요 선점)
   - 공간/경험 차별화: 구체적 컨셉 (예: 작업 친화적 카페 — 콘센트 전석 배치+화이트보드, 반려동물 동반 카페)
   - 타겟 차별화: 해당 상권의 인구 특성을 반영한 타겟 전략 (예: 직장인 테이크아웃 특화, 주부 디저트 카페)
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
# Section 4: 메뉴·가격 전략 (룰 기반 유지 — 정형 테이블)
# ---------------------------------------------------------------------------


def _section_menu_pricing(
    config: dict[str, Any],
    industry_name: str,
) -> SectionResponse:
    """Section 4: 메뉴·가격 전략"""
    menu_costs = config.get("MENU_COSTS", {})

    if not menu_costs:
        content = f"""## 메뉴·가격 전략

{industry_name} 업종의 메뉴 원가 데이터가 준비 중입니다. 일반적으로 식재료 원가율 30~35%를 목표로 가격을 책정하시기 바랍니다.
"""
        return SectionResponse(id="menu", title="4. 메뉴·가격 전략", content=content)

    total_margin = 0.0
    count = 0
    rows = ""
    for name, data in menu_costs.items():
        sp = data.get("selling_price", 0)
        tc = data.get("total_cost", 0)
        margin = sp - tc
        mr = margin / max(1, sp) * 100
        total_margin += mr
        count += 1
        rows += f"| {name} | {_fmt(sp)}원 | {_fmt(tc)}원 | {_fmt(margin)}원 | {_pct(mr)} |\n"

    avg_margin = total_margin / max(1, count)

    items_sorted = sorted(
        menu_costs.items(),
        key=lambda x: (x[1]["selling_price"] - x[1]["total_cost"]) / max(1, x[1]["selling_price"]),
        reverse=True,
    )
    best_name = items_sorted[0][0] if items_sorted else "-"
    worst_name = items_sorted[-1][0] if items_sorted else "-"

    content = f"""## 메뉴·가격 전략

### 메뉴별 원가 분석

| 메뉴 | 판매가 | 원가 | 마진 | 마진율 |
|------|--------|------|------|--------|
{rows}
- **평균 마진율**: {_pct(avg_margin)}
- **최고 마진 메뉴**: {best_name}
- **최저 마진 메뉴**: {worst_name}

### 가격 전략 제언

1. **주력 메뉴**: 마진율이 높은 **{best_name}**을(를) 핵심 추천 메뉴로 배치
2. **세트 구성**: 마진이 낮은 {worst_name}은(는) 고마진 음료와 세트로 묶어 평균 객단가 상승 유도
3. **시즌 메뉴**: 분기별 한정 메뉴 운영으로 재방문율 향상
"""

    return SectionResponse(
        id="menu",
        title="4. 메뉴·가격 전략",
        content=content,
        data={
            "avg_margin_rate": round(avg_margin, 1),
            "menu_count": count,
            "best_margin_menu": best_name,
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
        # Keep the target customer table as header, then AI content
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
# Section 6: 재무 계획 (룰 기반 유지 — 정형 수치 테이블)
# ---------------------------------------------------------------------------


def _section_financials(
    sim_result: dict[str, Any],
    budget: int,
) -> SectionResponse:
    """Section 6: 재무 계획"""
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

    content = f"""## 재무 계획

### 초기 투자비용

| 항목 | 금액 |
|------|------|
| **보증금** | {_fmt_man(startup['deposit'])} |
| **인테리어** | {_fmt_man(startup['interior'])} |
| **장비/설비** | {_fmt_man(startup['equipment_min'])} ~ {_fmt_man(startup['equipment_max'])} |
| **초도물품** | {_fmt_man(startup['initial_inventory_min'])} ~ {_fmt_man(startup['initial_inventory_max'])} |
| **인허가/기타** | {_fmt_man(startup['permits_misc_min'])} ~ {_fmt_man(startup['permits_misc_max'])} |
| **합계** | **{_fmt_man(startup['total_min'])} ~ {_fmt_man(startup['total_max'])}** |

> 총 예산 {_fmt_man_raw(budget)} 대비 투자비용 {_fmt_man(startup['total_min'])} ~ {_fmt_man(startup['total_max'])} \
({'예산 내 가능' if budget * 10000 >= startup['total_min'] else '예산 초과 — 조정 필요'})

### 월간 운영비

| 항목 | 금액 | 비중 |
|------|------|------|
| **임대료** | {_fmt_man(operating['rent'])} | {_pct(operating['rent'] / max(1, op_total) * 100)} |
| **식재료/원재료** | {_fmt_man(operating['cogs'])} | {_pct(operating['cogs'] / max(1, op_total) * 100)} |
| **인건비** | {_fmt_man(operating['labor'])} | {_pct(operating['labor'] / max(1, op_total) * 100)} |
| **공과금** | {_fmt_man(operating['utilities'])} | {_pct(operating['utilities'] / max(1, op_total) * 100)} |
| **기타** | {_fmt_man(operating['other'])} | {_pct(operating['other'] / max(1, op_total) * 100)} |
| **합계** | **{_fmt_man(op_total)}** | 100% |

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
"""

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
            "budget_ok": budget * 10000 >= startup["total_min"],
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
        mitigations.append("**생존율 관리**: 최소 6개월 운영자금 확보, 초기 3개월 집중 마케팅")
    if sc > 15:
        mitigations.append("**경쟁 차별화**: 시그니처 메뉴 개발, 고유한 브랜드 아이덴티티 구축")
    if closed > new:
        mitigations.append("**방어적 전략**: 손익분기 달성까지 비용 최소화, 임대료 협상 강화")
    if change_code in ("LL", "LH"):
        mitigations.append("**상권 변화 대응**: 배달/테이크아웃 비중 확대, 온라인 채널 강화")
    if not mitigations:
        mitigations.append("**지속 성장**: 고객 리텐션 강화, 메뉴 혁신으로 장기 경쟁력 확보")
    mitigation_text = "\n".join(f"{i+1}. {m}" for i, m in enumerate(mitigations))

    return f"""## 리스크 분석

### 종합 리스크 등급: {risk_level}

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
동종 업종 점포수: {sc}개
신규 개업: {new}개, 폐업: {closed}개
상권변화지표: {_change_indicator_text(change_code)} ({change_code})
예상 월매출: {_fmt_man(monthly_rev)}, 월 순이익: {_fmt_man(monthly_net)}
투자 회수: {be_months_min}~{be_months_max}개월
총 예산: {_fmt_man_raw(budget)}
기존 감지된 리스크:
{risk_list_str}
{scorecard_summary}

분석 요구사항:
1. 아래 5가지 리스크 카테고리별로 분석하세요:
   - **시장 리스크**: 상권 변화, 경기 침체, 트렌드 변화
   - **경쟁 리스크**: 신규 진입자, 대형 프랜차이즈 확장, 가격 전쟁
   - **재무 리스크**: 초기 자금 소진, 매출 부진, 고정비 부담
   - **운영 리스크**: 인력 관리, 식재료 원가 상승, 시설 유지보수
   - **외부 리스크**: 정책 변화, 임대료 인상, 재개발
2. 각 리스크에 대해 **구체적인 대응 전략**을 수치 근거와 함께 작성하세요.
   예: "월 순이익 {_fmt_man(monthly_net)} 중 20%를 비상 운영자금으로 적립 → 6개월 내 약 XX만원 확보"
3. 리스크 발생 시 **단계별 대응 프로토콜** (경고→주의→위기) 을 제시하세요.
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
# Section 8: 실행 로드맵 (룰 기반 유지)
# ---------------------------------------------------------------------------


def _section_roadmap(
    industry_name: str,
) -> SectionResponse:
    """Section 8: 실행 로드맵 (90일)"""

    content = f"""## 실행 로드맵

### 90일 창업 체크리스트

#### Phase 1: 준비기 (D-90 ~ D-60)

| 기간 | 항목 | 상세 |
|------|------|------|
| 1주차 | 사업자등록 | 관할 세무서에 사업자등록 신청 |
| 1~2주차 | 입지 계약 | 임대차 계약 체결, 권리금 협상 |
| 2~3주차 | 인허가 | 영업신고증(식품위생법), 소방안전점검 |
| 3~4주차 | 인테리어 설계 | 컨셉 확정, 시공업체 선정, 견적 비교 |

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
| 12주차 | 프리오픈 | 지인 초대 시운전 -> 피드백 반영 |
| D-day | **그랜드 오픈** | 오픈 이벤트 시행 |

#### Phase 4: 안정화 (D+1 ~ D+30)

| 기간 | 항목 | 상세 |
|------|------|------|
| 1주차 | 운영 모니터링 | 일매출 추적, 고객 피드백 수집 |
| 2주차 | 메뉴 조정 | 판매 데이터 기반 메뉴 조정 |
| 3~4주차 | 마케팅 강화 | 리뷰 이벤트, 스탬프 카드 도입 |
"""

    return SectionResponse(
        id="roadmap",
        title="8. 실행 로드맵",
        content=content,
        data={
            "total_days": 90,
            "phases": ["준비기", "시공기", "오픈 준비", "안정화"],
        },
    )


# ---------------------------------------------------------------------------
# Main Endpoint
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=BusinessPlanResponse)
async def generate_business_plan(req: BusinessPlanRequest) -> BusinessPlanResponse:
    """사업계획서 자동 생성 — Gemini Flash v2 (AI 분석 + 데이터 테이블)"""
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

    # 6. Generate sections — Gemini sections run in parallel via asyncio.gather
    # Sync sections (1, 4, 6, 8)
    section_overview = _section_overview(
        district, config, business_name, industry_name,
        req.area_pyeong, req.budget, req.target_customers,
    )
    section_menu = _section_menu_pricing(config, industry_name)
    section_financials = _section_financials(sim_result, req.budget)
    section_roadmap = _section_roadmap(industry_name)

    # Async Gemini sections (2, 3, 5, 7) — parallel
    section_market, section_competition, section_marketing_r, section_risk_r = (
        await asyncio.gather(
            _section_market_analysis(district, industry_name),
            _section_competition(district, industry_name),
            _section_marketing(district, industry_name, req.target_customers),
            _section_risk(district, sim_result, scorecard, industry_name, req.budget),
        )
    )

    sections = [
        section_overview,
        section_market,
        section_competition,
        section_menu,
        section_marketing_r,
        section_financials,
        section_risk_r,
        section_roadmap,
    ]

    return BusinessPlanResponse(
        business_name=business_name,
        district_name=district_name,
        industry_name=industry_name,
        sections=sections,
        generated_at=datetime.now().isoformat(),
    )
