# SpotPick 수정기획안 v3 — 파일 단위 구현 명세

> 작성일: 2026-02-09 (D-10) | 제출 마감: 2026-02-19 (D-0)
> 현재: v0.9.1 → 목표: v1.0.0
> 원칙: **기존 패턴 100% 준수. 새로운 라이브러리 추가 최소화.**

---

## 0. 기존 아키텍처 패턴 요약

이 기획안의 모든 구현은 아래 패턴을 따름:

```
Backend Route 등록:
  api/app.py → importlib.import_module("api.routes.{name}").router
  → app.include_router(router, prefix="/api/v1", tags=[...])

Backend Service 패턴:
  api/services/{name}_service.py → class + get_{name}_service() 레지스트리
  → get_data_service(industry_code) 참조하여 데이터 조회

Frontend Page 패턴:
  web/src/app/{name}/page.tsx → "use client" + useSearchParams + Suspense
  → const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1"
  → fetch(`${API_BASE}/...`)

Frontend Store 패턴:
  web/src/lib/{name}-store.ts → zustand create<State>()
  → useAnalyzeStore / useJourneyStore 참조
```

---

## 1. 구현 항목 우선순위

| 순서 | 기능 | 신규 파일 | 수정 파일 | 난이도 | 일정 |
|------|------|----------|----------|--------|------|
| **1** | 상권 비교 (Compare) | 2 BE + 1 FE | 1 BE + 1 FE | 중 | D-10 |
| **2** | 폐업 위험도 경보 | 1 BE service | 1 BE route + 1 FE | 중 | D-9 |
| **3** | AI 실시간 브리핑 | 0 (기존 활용) | 1 BE route + 1 FE | 하 | D-9 |
| **4** | 창업 타임라인 | 1 BE route + 1 데이터 | 1 FE | 중 | D-8 |
| **5** | 인허가 체크리스트 | 1 데이터 파일 | 1 FE (timeline에 포함) | 하 | D-8 |
| **6** | 애널리틱스 | 1 BE route + 1 FE lib | 2 FE page | 중 | D-7 |
| **7** | /dev-log 페이지 | 1 FE page | 0 | 하 | D-7 |
| **8** | UI 폴리시 + 에러 핸들링 | 0 | 다수 FE | 중 | D-6 |

---

## 2. 기능 1: 상권 비교 (Compare)

### 2-1. 백엔드 — `api/routes/compare.py` (신규)

```python
"""상권 A vs B 비교 분석 + AI 판정"""
from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/compare")


class CompareResponse(BaseModel):
    district_a: dict[str, Any]
    district_b: dict[str, Any]
    comparison: dict[str, Any]  # 지표별 승패
    ai_verdict: str             # Gemini 판정문


@router.get("", response_model=CompareResponse)
async def compare_districts(
    a: str = Query(..., description="상권 A 코드"),
    b: str = Query(..., description="상권 B 코드"),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    from api.services.data_service import get_data_service, estimate_rent
    from api.services.scorecard_service import get_scorecard_service

    svc = get_data_service(industry_code=industry_code)
    sc_svc = get_scorecard_service(industry_code)

    # 두 상권 데이터 조회
    dist_a = svc.get_district_by_code(a)
    dist_b = svc.get_district_by_code(b)

    if not dist_a or not dist_b:
        from fastapi import HTTPException
        raise HTTPException(404, "상권을 찾을 수 없습니다")

    # 스코어카드 계산
    score_a = sc_svc.score_district(dist_a)
    score_b = sc_svc.score_district(dist_b)

    # 핵심 지표 비교
    metrics = _build_comparison_metrics(dist_a, dist_b, score_a, score_b, svc)

    # Gemini 판정
    ai_verdict = await _generate_verdict(dist_a, dist_b, score_a, score_b, svc.display_name)

    return CompareResponse(
        district_a=_serialize_district(dist_a, score_a, svc),
        district_b=_serialize_district(dist_b, score_b, svc),
        comparison=metrics,
        ai_verdict=ai_verdict,
    )


def _serialize_district(d: dict, score: dict, svc) -> dict:
    """프론트에 보낼 상권 요약 데이터"""
    monthly_sales = d.get("monthly_sales", 0)
    store_count = d.get("store_count", 1)
    return {
        "district_code": d["district_code"],
        "district_name": d.get("district_name", ""),
        "district_type": d.get("district_type", ""),
        "scorecard_total": score.get("total_score", 0),
        "monthly_sales_per_store": monthly_sales // max(store_count, 1),
        "monthly_sales": monthly_sales,
        "store_count": store_count,
        "survival_rate": d.get("survival_rate", 0),
        "foot_traffic": d.get("foot_traffic_total", 0),
        "estimated_rent": estimate_rent(
            d.get("district_type", "골목상권"),
            monthly_sales // max(store_count, 1),
            score.get("percentile", 0.5),
            industry_code=svc.industry_code,
        ),
        "peak_time": d.get("peak_time", ""),
        "main_age_group": d.get("main_age_group", ""),
        "new_stores": d.get("new_stores", 0),
        "closed_stores": d.get("closed_stores", 0),
        "categories": score.get("categories", []),
    }


def _build_comparison_metrics(a, b, sa, sb, svc) -> dict:
    """지표별 승자 판정"""
    def winner(va, vb, lower_better=False):
        if lower_better:
            return "A" if va < vb else "B" if vb < va else "TIE"
        return "A" if va > vb else "B" if vb > va else "TIE"

    sc_a = sa.get("total_score", 0)
    sc_b = sb.get("total_score", 0)
    ms_a = a.get("monthly_sales", 0) // max(a.get("store_count", 1), 1)
    ms_b = b.get("monthly_sales", 0) // max(b.get("store_count", 1), 1)

    return {
        "scorecard": {"a": sc_a, "b": sc_b, "winner": winner(sc_a, sc_b)},
        "monthly_sales": {"a": ms_a, "b": ms_b, "winner": winner(ms_a, ms_b)},
        "survival_rate": {
            "a": a.get("survival_rate", 0), "b": b.get("survival_rate", 0),
            "winner": winner(a.get("survival_rate", 0), b.get("survival_rate", 0)),
        },
        "store_count": {
            "a": a.get("store_count", 0), "b": b.get("store_count", 0),
            "winner": winner(a.get("store_count", 0), b.get("store_count", 0), lower_better=True),
        },
        "foot_traffic": {
            "a": a.get("foot_traffic_total", 0), "b": b.get("foot_traffic_total", 0),
            "winner": winner(a.get("foot_traffic_total", 0), b.get("foot_traffic_total", 0)),
        },
    }


async def _generate_verdict(a, b, sa, sb, industry_name: str) -> str:
    """Gemini로 비교 판정문 생성 (실패 시 규칙 기반 폴백)"""
    try:
        from google import genai

        client = genai.Client()
        prompt = f"""당신은 상권 분석 전문가입니다. 두 상권을 비교 판정해주세요.

[상권 A: {a.get('district_name', '')} ({a.get('district_type', '')})]
종합점수: {sa.get('total_score', 0)}점, 점포당 월매출: {a.get('monthly_sales', 0) // max(a.get('store_count', 1), 1):,}원
생존율: {a.get('survival_rate', 0):.0%}, 경쟁점포: {a.get('store_count', 0)}개, 유동인구: {a.get('foot_traffic_total', 0):,}명

[상권 B: {b.get('district_name', '')} ({b.get('district_type', '')})]
종합점수: {sb.get('total_score', 0)}점, 점포당 월매출: {b.get('monthly_sales', 0) // max(b.get('store_count', 1), 1):,}원
생존율: {b.get('survival_rate', 0):.0%}, 경쟁점포: {b.get('store_count', 0)}개, 유동인구: {b.get('foot_traffic_total', 0):,}명

업종: {industry_name}

3~4문장으로 어느 상권이 더 유리한지 판정하고, 핵심 근거를 제시하세요.
마크다운 없이 일반 텍스트로 응답하세요."""

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        return response.text.strip() if response.text else _fallback_verdict(sa, sb, a, b)
    except Exception:
        return _fallback_verdict(sa, sb, a, b)


def _fallback_verdict(sa, sb, a, b) -> str:
    """Gemini 실패 시 규칙 기반 판정"""
    score_a = sa.get("total_score", 0)
    score_b = sb.get("total_score", 0)
    name_a = a.get("district_name", "A")
    name_b = b.get("district_name", "B")
    if score_a > score_b:
        return f"{name_a} 상권이 종합점수 {score_a}점으로 {name_b}({score_b}점) 대비 유리합니다."
    elif score_b > score_a:
        return f"{name_b} 상권이 종합점수 {score_b}점으로 {name_a}({score_a}점) 대비 유리합니다."
    return f"두 상권의 종합점수가 {score_a}점으로 동일합니다. 세부 지표를 비교하여 판단하세요."
```

### 2-2. 백엔드 등록 — `api/app.py` 수정

```python
# 기존 패턴과 동일하게 추가 (location_router 아래)
compare_router = cast(APIRouter, import_module("api.routes.compare").router)
app.include_router(compare_router, prefix="/api/v1", tags=["Compare"])
```

### 2-3. 프론트엔드 — `web/src/app/compare/page.tsx` (신규)

```
구조:
├── "use client" + Suspense 래핑
├── 상단: 상권 A/B 드롭다운 선택 (districts/search API 활용)
├── 중단: 6개 지표 나란히 비교 (승자 하이라이트)
│   ├── 종합점수 / 점포당 매출 / 생존율
│   └── 경쟁점포 / 유동인구 / 추정임대료
├── 하단: AI 판정문 (스트리밍 아님 — 한 번에 표시)
└── CTA: "A 상권 상세 분석" / "B 상권 상세 분석" → /report 링크

API 호출:
  GET ${API_BASE}/compare?a=${codeA}&b=${codeB}&industry_code=${industryCode}

상권 검색:
  GET ${API_BASE}/districts/search?q=${query}&industry_code=${industryCode}&limit=10
  → 기존 districts/search 엔드포인트 그대로 활용

State:
  - useSearchParams()로 a, b, industry_code 읽기
  - 내부 state: districtA, districtB, result, loading

컴포넌트 크기: ~300줄 (단일 파일)
```

### 2-4. 랜딩 페이지 진입점 — `web/src/app/page.tsx` 수정

```
ENTRY_POINTS 배열에 추가:
{
  question: "A vs B 어디가 나아?",
  label: "상권 비교",
  desc: "두 상권을 나란히 비교하고 AI가 판정해드려요",
  href: "/compare",
  icon: GitCompareArrows,  // lucide-react 아이콘
  color: "from-cyan-500 to-cyan-600",
}

Header nav에 "비교" 링크 추가
```

---

## 3. 기능 2: 폐업 위험도 경보

### 3-1. 백엔드 서비스 — `api/services/risk_service.py` (신규)

```python
"""폐업 위험 신호 탐지 — DataService 데이터 기반 순수 계산 (AI 호출 없음)"""
from __future__ import annotations
from typing import Any

# 임계값 상수
THRESHOLDS = {
    "survival_rate_danger": 0.55,       # 생존율 55% 미만 = 위험
    "survival_rate_warning": 0.65,      # 65% 미만 = 주의
    "competition_danger": 100,           # 동종 점포 100개 이상
    "competition_warning": 60,           # 60개 이상
    "rent_ratio_danger": 0.30,          # 임대료/매출 30% 이상
    "rent_ratio_warning": 0.20,         # 20% 이상
    "closed_ratio_danger": 0.15,        # 폐업 비율 15% 이상
    "closed_ratio_warning": 0.10,       # 10% 이상
    "new_store_surge": 0.25,            # 신규 점포 25% 이상 급증
}


def analyze_risk(
    district: dict[str, Any],
    estimated_rent: int,
    industry_display_name: str = "",
) -> dict[str, Any]:
    """
    district: DataService에서 가져온 상권 dict (64개 필드)
    estimated_rent: estimate_rent()로 계산된 추정 임대료
    Returns: {risk_score: 0-100, risk_level, signals[], alternative_suggestion}
    """
    signals: list[dict[str, str]] = []
    score = 0

    # 1) 생존율
    survival = district.get("survival_rate", 0)
    if isinstance(survival, (int, float)):
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
            "detail": f"신규 {new_stores}개 (기존 대비 {new_stores/store_count:.0%})",
            "advice": "시장이 과열 상태일 수 있습니다. 6개월 후 경쟁 심화에 대비하세요",
        })
        score += 10

    risk_score = min(score, 100)
    risk_level = "high" if risk_score >= 50 else "medium" if risk_score >= 25 else "low"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "signals": signals,
        "signal_count": len(signals),
        "danger_count": sum(1 for s in signals if s["level"] == "danger"),
        "warning_count": sum(1 for s in signals if s["level"] == "warning"),
    }
```

### 3-2. 백엔드 엔드포인트 — `api/routes/districts.py` 수정

기존 districts 라우터에 엔드포인트 추가:

```python
@router.get("/{district_code}/risk")
def get_risk_analysis(
    district_code: str,
    industry_code: str = Query("CS100010"),
):
    """폐업 위험도 분석"""
    from ..services.data_service import get_data_service, estimate_rent
    from ..services.risk_service import analyze_risk
    from ..services.scorecard_service import get_scorecard_service

    svc = get_data_service(industry_code=industry_code)
    district = svc.get_district_by_code(district_code)
    if not district:
        from fastapi import HTTPException
        raise HTTPException(404, "상권을 찾을 수 없습니다")

    sc_svc = get_scorecard_service(industry_code)
    score = sc_svc.score_district(district)

    monthly_sales = district.get("monthly_sales", 0)
    store_count = max(district.get("store_count", 1), 1)
    est_rent = estimate_rent(
        district.get("district_type", "골목상권"),
        monthly_sales // store_count,
        score.get("percentile", 0.5),
        industry_code=industry_code,
    )

    return analyze_risk(district, est_rent, svc.display_name)
```

### 3-3. 프론트엔드 — 리포트 페이지에 위험도 배너 삽입

**수정 파일**: `web/src/app/analyze/report/page.tsx`

```
삽입 위치: Top3Section 아래, 상세 분석 섹션 위

로직:
  1. selectedDistrictCode가 변경되면 → fetch risk API
  2. risk_level === "high" → 빨간 배너 표시
  3. risk_level === "medium" → 노란 배너 표시
  4. risk_level === "low" → 표시 안 함

컴포넌트: RiskAlertBanner (인라인 정의, ~80줄)
  - API: GET ${API_BASE}/districts/${code}/risk?industry_code=${industryCode}
  - 표시: 위험도 바 + 신호 리스트 (접기/펼치기)
  - "대안 상권 찾기" → /compare 링크
```

---

## 4. 기능 3: AI 실시간 브리핑

### 4-1. 백엔드 — `api/routes/districts.py`에 엔드포인트 추가

```python
@router.get("/{district_code}/briefing")
async def get_ai_briefing(
    district_code: str,
    industry_code: str = Query("CS100010"),
):
    """AI 실시간 상권 브리핑 — 종합 데이터 기반 3~5문장 해석"""
    from ..services.data_service import get_data_service, estimate_rent
    from ..services.scorecard_service import get_scorecard_service
    from ..services.simulation_service import SimulationService
    from ..services.risk_service import analyze_risk

    svc = get_data_service(industry_code=industry_code)
    district = svc.get_district_by_code(district_code)
    if not district:
        from fastapi import HTTPException
        raise HTTPException(404, "상권을 찾을 수 없습니다")

    # 데이터 수집 (동기 — 모두 인메모리 계산이라 빠름)
    sc_svc = get_scorecard_service(industry_code)
    score = sc_svc.score_district(district)
    sim_svc = SimulationService()

    monthly_sales = district.get("monthly_sales", 0)
    store_count = max(district.get("store_count", 1), 1)
    sps = monthly_sales // store_count
    est_rent = estimate_rent(
        district.get("district_type", "골목상권"), sps,
        score.get("percentile", 0.5), industry_code=industry_code,
    )

    risk = analyze_risk(district, est_rent, svc.display_name)

    # Gemini 브리핑 생성
    try:
        from google import genai
        client = genai.Client()

        prompt = f"""당신은 상권 분석 전문 컨설턴트입니다.
아래 데이터를 바탕으로 {svc.display_name} 업종 예비 창업자에게 이 상권에 대한 핵심 브리핑을 해주세요.

상권: {district.get('district_name', '')} ({district.get('district_type', '')})
종합점수: {score.get('total_score', 0)}점 (상위 {score.get('percentile', 0.5)*100:.0f}%)
점포당 월매출: {sps:,}원
추정 임대료: {est_rent:,}원
생존율: {district.get('survival_rate', 0):.0%}
경쟁 점포: {store_count}개
유동인구: {district.get('foot_traffic_total', 0):,}명/분기
주요 고객층: {district.get('main_age_group', '')}
피크 시간대: {district.get('peak_time', '')}
위험도: {risk['risk_score']}점 ({risk['risk_level']})
위험 신호: {risk['signal_count']}건

4~6문장으로 다음을 포함하여 브리핑하세요:
1) 이 상권의 한 줄 평가 (좋다/보통/위험)
2) 가장 큰 강점 1개
3) 가장 큰 약점 또는 주의점 1개
4) 구체적 추천 전략 1개
5) 예상 손익분기 시점

마크다운 없이 자연스러운 구어체로 작성하세요."""

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        briefing_text = response.text.strip() if response.text else ""
    except Exception:
        briefing_text = ""

    # 폴백
    if not briefing_text:
        total = score.get("total_score", 0)
        grade = "우수" if total >= 75 else "보통" if total >= 50 else "취약"
        briefing_text = (
            f"{district.get('district_name', '')} 상권은 종합 {total}점으로 {grade} 등급입니다. "
            f"점포당 월매출 {sps//10000:,}만원, 생존율 {district.get('survival_rate', 0):.0%}입니다. "
            f"{'주의가 필요한 상권입니다.' if risk['risk_level'] == 'high' else '세부 분석을 확인하세요.'}"
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
```

### 4-2. 프론트엔드 — 리포트 페이지에 브리핑 카드 추가

**수정 파일**: `web/src/app/analyze/report/page.tsx`

```
삽입 위치: Top3Section에서 상권 선택 직후 (RiskAlertBanner 위)

컴포넌트: AiBriefingCard (~60줄)
  - API: GET ${API_BASE}/districts/${code}/briefing?industry_code=${industryCode}
  - 로딩: "AI가 분석하고 있습니다..." (Sparkles 아이콘 + pulse 애니메이션)
  - 표시: 파란 배경 카드에 브리핑 텍스트 + 요약 지표 4개
  - 하단: "자세히 보기" → 섹션 스크롤, "비교하기" → /compare
```

---

## 5. 기능 4: 창업 타임라인 + 인허가 체크리스트

### 5-1. 인허가 데이터 — `api/data/industry_permits.json` (신규)

```json
{
  "CS100010": {
    "name": "카페",
    "permits": [
      {"order": 1, "name": "사업자등록", "agency": "국세청 홈택스", "duration": "즉시~3일", "cost": 0, "required": true},
      {"order": 2, "name": "식품위생교육", "agency": "한국외식산업협회", "duration": "1일(8시간)", "cost": 40000, "required": true},
      {"order": 3, "name": "영업신고 (일반음식점)", "agency": "관할 구청 위생과", "duration": "7~14일", "cost": 0, "required": true},
      {"order": 4, "name": "음식물폐기물 배출 신고", "agency": "관할 구청", "duration": "3일", "cost": 0, "required": true},
      {"order": 5, "name": "옥외광고물 표시 허가", "agency": "관할 구청", "duration": "7일", "cost": 50000, "required": false}
    ],
    "notes": ["건물 용도가 근린생활시설인지 반드시 확인", "배달 영업 시 통신판매업 신고 필요"]
  },
  "CS100007": {
    "name": "치킨전문점",
    "permits": [
      {"order": 1, "name": "사업자등록", "agency": "국세청 홈택스", "duration": "즉시~3일", "cost": 0, "required": true},
      {"order": 2, "name": "식품위생교육", "agency": "한국외식산업협회", "duration": "1일(8시간)", "cost": 40000, "required": true},
      {"order": 3, "name": "영업신고", "agency": "관할 구청 위생과", "duration": "7~14일", "cost": 0, "required": true},
      {"order": 4, "name": "소방안전관리 신고", "agency": "소방서", "duration": "3일", "cost": 0, "required": true},
      {"order": 5, "name": "음식물폐기물 배출 신고", "agency": "관할 구청", "duration": "3일", "cost": 0, "required": true},
      {"order": 6, "name": "옥외광고물 표시 허가", "agency": "관할 구청", "duration": "7일", "cost": 50000, "required": false}
    ],
    "notes": ["튀김유 폐식용유 별도 처리 계약 필요", "환기 시설 기준 충족 확인"]
  }
}
```

나머지 8개 업종도 동일 구조로 작성. 대부분의 음식업종은 1~3번(사업자등록, 위생교육, 영업신고)이 동일하고 업종별 특수 항목만 다름.

### 5-2. 백엔드 — `api/routes/timeline.py` (신규)

```python
"""창업 타임라인 + 인허가 체크리스트 생성"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query, HTTPException

router = APIRouter(prefix="/timeline")

PERMITS_PATH = Path(__file__).resolve().parent.parent / "data" / "industry_permits.json"

def _load_permits() -> dict:
    try:
        with open(PERMITS_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


@router.get("/permits")
def get_permits(industry_code: str = Query("CS100010")):
    """업종별 인허가 체크리스트 반환 (정적 데이터)"""
    permits = _load_permits()
    data = permits.get(industry_code)
    if not data:
        # 기본값: 카페 기준
        data = permits.get("CS100010", {"name": "", "permits": [], "notes": []})
    return data


@router.get("/generate")
async def generate_timeline(
    district_code: str = Query(...),
    industry_code: str = Query("CS100010"),
    budget: int = Query(5000, description="총 예산 (만원)"),
):
    """AI 기반 맞춤 창업 타임라인 생성"""
    from ..services.data_service import get_data_service, estimate_rent
    from ..services.simulation_service import SimulationService
    from ..services.scorecard_service import get_scorecard_service

    svc = get_data_service(industry_code=industry_code)
    district = svc.get_district_by_code(district_code)
    if not district:
        raise HTTPException(404, "상권을 찾을 수 없습니다")

    # 시뮬레이션 데이터
    sim_svc = SimulationService()
    sc_svc = get_scorecard_service(industry_code)
    score = sc_svc.score_district(district)

    monthly_sales = district.get("monthly_sales", 0)
    store_count = max(district.get("store_count", 1), 1)
    sps = monthly_sales // store_count
    est_rent = estimate_rent(
        district.get("district_type", "골목상권"), sps,
        score.get("percentile", 0.5), industry_code=industry_code,
    )

    # 인허가 데이터
    permits_data = _load_permits().get(industry_code, {})
    permits_list = permits_data.get("permits", [])
    notes = permits_data.get("notes", [])

    # Gemini 타임라인 생성
    try:
        from google import genai
        client = genai.Client()

        prompt = f"""창업 실행 타임라인을 JSON 배열로 생성하세요.

조건:
- 업종: {svc.display_name}
- 상권: {district.get('district_name', '')} ({district.get('district_type', '')})
- 예산: {budget}만원
- 추정 임대료: {est_rent:,}원/월
- 필요 인허가: {json.dumps([p['name'] for p in permits_list], ensure_ascii=False)}

D-90(오픈 90일 전)부터 D+90(오픈 후 90일)까지 10~15개 마일스톤을 생성하세요.
각 항목: {{"day": -90, "title": "제목", "detail": "1줄 설명", "cost_man": 0, "duration": "3일", "category": "인허가|자금|시설|운영|마케팅"}}

JSON 배열만 반환하세요. 다른 텍스트 없이."""

        response = await client.aio.models.generate_content(
            model="gemini-2.5-flash", contents=prompt,
        )
        text = (response.text or "").strip()
        # JSON 파싱 (```json ... ``` 래퍼 제거)
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
        timeline = json.loads(text)
    except Exception:
        # 규칙 기반 폴백 타임라인
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


def _fallback_timeline(permits, est_rent, budget) -> list[dict]:
    """Gemini 실패 시 규칙 기반 타임라인"""
    base = [
        {"day": -90, "title": "사업 구상 확정", "detail": "메뉴, 콘셉트, 타겟 고객 확정", "cost_man": 0, "duration": "7일", "category": "운영"},
        {"day": -80, "title": "자금 확보", "detail": "대출 상담, 지원금 신청", "cost_man": 0, "duration": "14일", "category": "자금"},
        {"day": -75, "title": "점포 물색 및 계약", "detail": "임대차 계약 체결", "cost_man": int(est_rent / 10000 * 10), "duration": "14일", "category": "시설"},
        {"day": -60, "title": "인테리어 설계 및 시공", "detail": "도면 작성, 시공업체 선정, 시공", "cost_man": int(budget * 0.3), "duration": "30일", "category": "시설"},
    ]
    for p in permits:
        base.append({
            "day": -45 + (p.get("order", 1) - 1) * 5,
            "title": p["name"],
            "detail": f'{p.get("agency", "")} | 소요: {p.get("duration", "")}',
            "cost_man": p.get("cost", 0) // 10000,
            "duration": p.get("duration", "7일"),
            "category": "인허가",
        })
    base.extend([
        {"day": -14, "title": "장비 입고 및 설치", "detail": "주방 장비, 가구, 인테리어 마무리", "cost_man": int(budget * 0.15), "duration": "7일", "category": "시설"},
        {"day": -7, "title": "시범 운영", "detail": "소프트 오픈, 지인 초대, 메뉴 최종 점검", "cost_man": 50, "duration": "7일", "category": "운영"},
        {"day": 0, "title": "정식 오픈", "detail": "그랜드 오픈 + 오픈 이벤트", "cost_man": 100, "duration": "1일", "category": "마케팅"},
        {"day": 30, "title": "1개월 운영 점검", "detail": "매출 분석, 메뉴 조정, 고객 피드백 반영", "cost_man": 0, "duration": "지속", "category": "운영"},
        {"day": 90, "title": "3개월 성과 평가", "detail": "손익분기 도달 여부 확인, 전략 수정", "cost_man": 0, "duration": "지속", "category": "운영"},
    ])
    return sorted(base, key=lambda x: x["day"])
```

### 5-3. 백엔드 등록 — `api/app.py` 수정

```python
timeline_router = cast(APIRouter, import_module("api.routes.timeline").router)
app.include_router(timeline_router, prefix="/api/v1", tags=["Timeline"])
```

### 5-4. 프론트엔드 — `web/src/app/timeline/page.tsx` (신규)

```
구조:
├── 상단: 상권명 + 업종 + 예산 표시 (searchParams에서 읽기)
├── 중단: 세로 타임라인 UI
│   ├── 각 마일스톤: day 라벨 + 제목 + 설명 + 비용 + 카테고리 뱃지
│   ├── D-0 (오픈일)에 강조 마커
│   ├── 카테고리별 색상: 인허가(파랑) / 자금(초록) / 시설(주황) / 운영(보라) / 마케팅(핑크)
│   └── 총 예상비용 합계 표시
├── 하단: 인허가 체크리스트 섹션
│   ├── 체크박스 + 항목명 + 기관 + 소요기간 + 비용
│   └── 체크 상태 localStorage 저장
└── CTA: "사업계획서에 반영" → /analyze/action 링크

API 호출:
  GET ${API_BASE}/timeline/generate?district_code=${code}&industry_code=${ind}&budget=${budget}

searchParams: district_code, industry_code, budget
컴포넌트 크기: ~250줄
```

---

## 6. 기능 5: 애널리틱스

### 6-1. 백엔드 — `api/routes/analytics.py` (신규)

```python
"""이벤트 수집 — JSONL 파일 로깅 (경량)"""
from __future__ import annotations

import json
import hashlib
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/analytics")

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "analytics"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class EventPayload(BaseModel):
    event: str
    session_id: str = ""
    timestamp: str = ""
    page: str = ""
    referrer: str = ""
    props: dict = {}


@router.post("/event")
async def receive_event(payload: EventPayload, request: Request):
    """이벤트 수신 → JSONL 파일에 append"""
    # IP 해시 (개인정보 보호)
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:12]

    today = datetime.utcnow().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"events_{today}.jsonl"

    entry = {
        "event": payload.event,
        "session_id": payload.session_id,
        "timestamp": payload.timestamp or datetime.utcnow().isoformat(),
        "page": payload.page,
        "referrer": payload.referrer,
        "ip_hash": ip_hash,
        "props": payload.props,
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"ok": True}


@router.get("/summary")
def get_summary(date: str = ""):
    """일별 이벤트 집계 (내부용)"""
    target_date = date or datetime.utcnow().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"events_{target_date}.jsonl"

    if not log_file.exists():
        return {"date": target_date, "total_events": 0, "unique_sessions": 0, "events": {}}

    events: dict[str, int] = {}
    sessions: set[str] = set()
    with open(log_file, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                ev = entry.get("event", "unknown")
                events[ev] = events.get(ev, 0) + 1
                if entry.get("session_id"):
                    sessions.add(entry["session_id"])
            except Exception:
                continue

    return {
        "date": target_date,
        "total_events": sum(events.values()),
        "unique_sessions": len(sessions),
        "events": events,
    }
```

### 6-2. 백엔드 등록 — `api/app.py` 수정

```python
analytics_router = cast(APIRouter, import_module("api.routes.analytics").router)
app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])
```

### 6-3. 프론트엔드 — `web/src/lib/analytics.ts` (신규)

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_URL || "/api/v1";

let _sessionId: string | null = null;
function getSessionId(): string {
  if (!_sessionId) {
    _sessionId = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  }
  return _sessionId;
}

export function track(
  event: string,
  props?: Record<string, string | number>,
) {
  if (typeof window === "undefined") return;

  const payload = {
    event,
    session_id: getSessionId(),
    timestamp: new Date().toISOString(),
    page: window.location.pathname,
    referrer: document.referrer,
    props: props || {},
  };

  try {
    const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
    if (navigator.sendBeacon) {
      navigator.sendBeacon(`${API_BASE}/analytics/event`, blob);
    } else {
      fetch(`${API_BASE}/analytics/event`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        keepalive: true,
      }).catch(() => {});
    }
  } catch {
    // 무시
  }
}
```

### 6-4. 이벤트 삽입 위치

| 이벤트 | 파일 | 삽입 위치 |
|--------|------|----------|
| `page_view` | `web/src/app/layout.tsx` | 루트 레이아웃 useEffect (pathname 변경 시) |
| `journey_start` | `web/src/app/analyze/page.tsx` | "분석 시작" 버튼 onClick |
| `industry_select` | `web/src/app/analyze/page.tsx` | 업종 카드 onClick |
| `report_view` | `web/src/app/analyze/report/page.tsx` | 데이터 로드 완료 시 |
| `compare_start` | `web/src/app/compare/page.tsx` | 비교 결과 로드 시 |
| `risk_alert_view` | `web/src/app/analyze/report/page.tsx` | RiskAlertBanner 표시 시 |
| `simulation_run` | `web/src/app/simulator/page.tsx` | 슬라이더 변경 완료 시 |
| `plan_generate` | `web/src/app/analyze/action/page.tsx` | 계획서 생성 완료 시 |
| `plan_download` | `web/src/components/PDFExportButton.tsx` | PDF 다운로드 클릭 시 |
| `timeline_view` | `web/src/app/timeline/page.tsx` | 타임라인 로드 완료 시 |

---

## 7. 기능 6: /dev-log 페이지 (심사위원용)

### 7-1. 프론트엔드 — `web/src/app/dev-log/page.tsx` (신규)

```
정적 페이지 (API 호출 없음). 하드코딩 데이터.

구조:
├── 섹션 1: 개발 통계
│   - 총 커밋 수, 배포 횟수, API 엔드포인트 수, 코드 라인 수
│   - "1인 개발 · AI 네이티브 · 14일 완성"
│
├── 섹션 2: 제품 내 AI 활용
│   - Gemini 2.5 Flash 활용처 5개 (상권분석, 사업계획서, 브리핑, 비교, 상담)
│   - 각 항목에 실제 사용 예시 1줄
│
├── 섹션 3: 개발 과정 AI 활용
│   - Claude Code 활용: 전체 프론트/백엔드 개발
│   - "25+ API 엔드포인트, 15개 페이지, 13개 서비스"
│
├── 섹션 4: 배포 이력
│   - Git tag 목록 (하드코딩)
│   - v0.1.0 → v0.9.1 → v1.0.0 진행 표시
│
└── 섹션 5: 기술 스택
    - Frontend: Next.js 14, TypeScript, Tailwind, Zustand, MapLibre
    - Backend: FastAPI, Gemini 2.5 Flash, Pandas
    - Data: 서울시 7종 공공데이터, 1,077개 상권

컴포넌트 크기: ~150줄 (정적)
```

---

## 8. UI 폴리시 + 에러 핸들링

### 8-1. 수정 대상 파일 목록

| 파일 | 수정 내용 |
|------|----------|
| `web/src/app/analyze/report/page.tsx` | 브리핑 카드 삽입 + 위험도 배너 삽입 + 에러 UI 통일 |
| `web/src/app/page.tsx` | Header nav에 "비교" 추가 + EntryPoints에 "상권 비교" 추가 |
| `web/src/app/analyze/action/page.tsx` | 에러 시 빈 화면 → 에러 메시지 + 재시도 버튼 |
| `web/src/app/report/page.tsx` | 브리핑 + 위험도 동일 적용 |
| `web/src/app/layout.tsx` | analytics page_view 이벤트 추가 |
| `web/src/app/simulator/page.tsx` | "타임라인 보기" CTA 추가 |
| `web/src/app/support/page.tsx` | "타임라인 보기" CTA 추가 |

### 8-2. 공통 에러 UI 패턴

모든 API 호출 실패 시 동일한 에러 UI 표시:

```tsx
// 인라인 패턴 (컴포넌트화 불필요 — 3줄)
{error && (
  <div className="flex flex-col items-center py-12 text-center">
    <AlertTriangle className="h-8 w-8 text-slate-300" />
    <p className="mt-2 text-sm text-slate-500">{error}</p>
    <button onClick={retry} className="mt-3 text-sm text-blue-600 underline">다시 시도</button>
  </div>
)}
```

### 8-3. OG 메타태그

**수정 파일**: `web/src/app/layout.tsx`

```tsx
export const metadata: Metadata = {
  title: "SpotPick — AI 창업 의사결정 플랫폼",
  description: "서울 1,077개 상권 데이터 + AI 분석. 업종선택부터 사업계획서까지 5분 완성.",
  openGraph: {
    title: "SpotPick — 창업, 감으로 하지 마세요",
    description: "AI가 최적 상권을 찾고, 수익을 예측하고, 사업계획서를 만들어드립니다.",
    type: "website",
  },
};
```

---

## 9. 전체 파일 변경 요약

### 신규 파일 (8개)

| # | 파일 경로 | 설명 | 예상 줄수 |
|---|----------|------|----------|
| 1 | `api/routes/compare.py` | 상권 비교 API | ~150줄 |
| 2 | `api/services/risk_service.py` | 폐업 위험도 분석 | ~120줄 |
| 3 | `api/routes/timeline.py` | 타임라인 + 인허가 API | ~150줄 |
| 4 | `api/routes/analytics.py` | 이벤트 수집 API | ~80줄 |
| 5 | `api/data/industry_permits.json` | 업종별 인허가 데이터 | ~200줄 |
| 6 | `web/src/app/compare/page.tsx` | 상권 비교 페이지 | ~300줄 |
| 7 | `web/src/app/timeline/page.tsx` | 창업 타임라인 페이지 | ~250줄 |
| 8 | `web/src/app/dev-log/page.tsx` | AI 네이티브 증거 페이지 | ~150줄 |
| 9 | `web/src/lib/analytics.ts` | 프론트 이벤트 트래킹 | ~40줄 |

### 수정 파일 (7개)

| # | 파일 경로 | 변경 내용 | 변경량 |
|---|----------|----------|--------|
| 1 | `api/app.py` | 3개 라우터 등록 (compare, timeline, analytics) | +9줄 |
| 2 | `api/routes/districts.py` | risk + briefing 엔드포인트 추가 | +80줄 |
| 3 | `web/src/app/analyze/report/page.tsx` | 브리핑카드 + 위험도배너 삽입 | +150줄 |
| 4 | `web/src/app/page.tsx` | nav에 "비교" + EntryPoints에 항목 추가 | +15줄 |
| 5 | `web/src/app/layout.tsx` | OG 메타태그 + analytics page_view | +20줄 |
| 6 | `web/src/app/simulator/page.tsx` | "타임라인 보기" CTA 추가 | +5줄 |
| 7 | `web/src/app/support/page.tsx` | "타임라인 보기" CTA 추가 | +5줄 |

---

## 10. 일별 실행 계획 (수정본)

```
D-10 (2/09 일) ─── 상권 비교 (Compare)
  ├── api/routes/compare.py 생성
  ├── api/app.py에 compare_router 등록
  ├── web/src/app/compare/page.tsx 생성
  ├── web/src/app/page.tsx에 진입점 추가
  └── 배포: v0.9.2

D-9 (2/10 월) ─── 폐업 위험도 + AI 브리핑
  ├── api/services/risk_service.py 생성
  ├── api/routes/districts.py에 risk + briefing 추가
  ├── web/src/app/analyze/report/page.tsx에 배너+브리핑 삽입
  └── 배포: v0.9.3

D-8 (2/11 화) ─── 타임라인 + 인허가
  ├── api/data/industry_permits.json 생성
  ├── api/routes/timeline.py 생성
  ├── api/app.py에 timeline_router 등록
  ├── web/src/app/timeline/page.tsx 생성
  └── 배포: v0.9.4

D-7 (2/12 수) ─── 애널리틱스 + /dev-log
  ├── api/routes/analytics.py 생성
  ├── api/app.py에 analytics_router 등록
  ├── web/src/lib/analytics.ts 생성
  ├── 10개 페이지에 이벤트 삽입
  ├── web/src/app/dev-log/page.tsx 생성
  └── 배포: v0.9.5

D-6 (2/13 목) ─── UI 폴리시 + 에러 핸들링
  ├── 전 페이지 에러 UI 통일
  ├── OG 메타태그 추가
  ├── 모바일 반응형 검수
  ├── CTA 연결 확인 (타임라인 등)
  └── 배포: v0.9.6

D-5 (2/14 금) ─── 통합 테스트 + 성능
  ├── 전체 워크플로우 수동 테스트
  ├── API 응답 속도 확인 (2초 이내)
  ├── 불필요 import 제거
  └── 배포: v0.9.7

D-4 (2/15 토) ─── 버그 수정 + 예비일
  └── 배포: v0.9.8

D-3 (2/16 일) ─── 실사용자 테스트
  ├── 지인 5명 테스트
  ├── 피드백 즉시 반영
  └── 배포: v0.9.9

D-2 (2/17 월) ─── 트랙션 수집
  ├── 커뮤니티 배포 (창업 갤러리 등)
  ├── 애널리틱스 데이터 수집 시작
  └── 배포: v1.0.0-rc

D-1 (2/18 화) ─── 데모 + 제출 준비
  ├── 1분 데모 영상 촬영
  ├── 200자 제출 설명문 확정
  └── 배포: v1.0.0

D-0 (2/19 수) ─── 제출
```

---

## 11. 핵심 제약 조건

1. **새 npm 패키지 추가 금지** — 기존 의존성만 사용
2. **새 Python 패키지 추가 금지** — google-genai, fastapi 등 이미 설치된 것만 사용
3. **기존 API 계약 변경 금지** — 새 엔드포인트만 추가, 기존 응답 형태 유지
4. **DataService 구조 변경 금지** — get_data_service() 레지스트리 패턴 그대로
5. **Gemini 호출에는 반드시 폴백** — 모든 AI 생성에 규칙 기반 fallback 필수
6. **ESLint strict 준수** — unused-vars 에러 수정, Suspense 래핑 필수
