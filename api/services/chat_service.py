"""
대화형 창업 상담 서비스 - Gemini 2.5 Flash 기반
"""

from __future__ import annotations

import logging
import os
import re
import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol, TypedDict, cast
from dotenv import load_dotenv  # type: ignore[import-not-found]

from api.services.data_service import DataService, get_data_service
from api.services.geocoding_service import get_geocoding_service
from api.services.kakao_local_service import KakaoLocalService, get_kakao_local_service
from api.services.competitive_analysis_service import (
    CompetitiveAnalysisService,
    get_competitive_analysis_service,
)
from api.services.simulation_service import SimulationService, get_simulation_service


class _GeminiResponse(Protocol):
    text: str | None


class _GeminiModels(Protocol):
    def generate_content(self, model: str, contents: str) -> _GeminiResponse: ...


class _GeminiClient(Protocol):
    @property
    def models(self) -> _GeminiModels: ...

# .env 로드
_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
logger = logging.getLogger(__name__)

try:
    from google import genai  # type: ignore[import-not-found]
except Exception:  # pragma: no cover
    genai = None  # type: ignore[assignment]


class HistoryMessage(TypedDict):
    role: str
    content: str


class TimeAnalysis(TypedDict):
    peak_time: str
    time_00_06: float
    time_06_11: float
    time_11_14: float
    time_14_17: float
    time_17_21: float
    time_21_24: float


class DayAnalysis(TypedDict):
    peak_day: str
    weekday_ratio: float
    weekend_ratio: float
    mon: float
    tue: float
    wed: float
    thu: float
    fri: float
    sat: float
    sun: float


class CustomerAnalysis(TypedDict):
    main_age_group: str
    male_ratio: float
    female_ratio: float
    age_10: float
    age_20: float
    age_30: float
    age_40: float
    age_50: float
    age_60: float


class Competition(TypedDict):
    store_count: int


class Recommendation(TypedDict):
    rank: int
    district_code: str
    district_name: str
    district_type: str
    address: str
    success_probability: float
    estimated_monthly_rent: int
    estimated_monthly_sales: int
    survival_rate_2y: float
    time_analysis: TimeAnalysis
    day_analysis: DayAnalysis
    customer_analysis: CustomerAnalysis
    competition: Competition
    risk_factors: list[str]
    key_success_factors: list[str]
    recommendations: list[str]


class StructuredRecommendation(TypedDict):
    rank: int
    district_name: str
    district_type: str
    success_probability: float
    estimated_rent: int
    peak_time: str
    main_age_group: str
    risk_factors: list[str]
    recommendations: list[str]
    address: str
    monthly_sales: int
    store_count: int
    survival_rate: float
    key_success_factors: list[str]
    coordinates: Optional[dict[str, float]]


class ChartDatum(TypedDict, total=False):
    name: str
    value: float
    label: str


class ChartData(TypedDict):
    type: str
    title: str
    data: list[ChartDatum]


class ContextMeta(TypedDict, total=False):
    district: Optional[str]
    budget_min: Optional[int]
    budget_max: Optional[int]
    area_type: Optional[str]
    time_preference: Optional[str]
    age_target: Optional[str]
    gender_target: Optional[str]
    cafe_type: Optional[str]
    unsupported_regions: list[str]
    data_error: str
    llm_error: str
    intake_needs: list[str]


class Summary(TypedDict):
    total_districts: int
    total_stores: int
    avg_monthly_sales: int
    avg_survival_rate: float
    district_types: dict[str, int]


class StructuredChatPayload(TypedDict):
    reply: str
    recommendations: list[StructuredRecommendation]
    charts: list[ChartData]
    suggested_questions: list[str]
    context: ContextMeta


@dataclass
class ConversationContext:
    district: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    area_type: Optional[str] = None
    time_preference: Optional[str] = None
    age_target: Optional[str] = None
    gender_target: Optional[str] = None
    cafe_type: Optional[str] = None


class ChatService:
    OUT_OF_SCOPE_REGIONS: list[str] = [
        # Major cities/provinces outside Seoul
        "부산",
        "대구",
        "인천",
        "광주",
        "대전",
        "울산",
        "세종",
        "제주",
        "제주도",
        "경기",
        "강원",
        "충북",
        "충남",
        "전북",
        "전남",
        "경북",
        "경남",
        # Common non-Seoul places (esp. Gyeonggi)
        "수원",
        "성남",
        "분당",
        "판교",
        "용인",
        "화성",
        "부천",
        "안양",
        "평택",
        "고양",
        "일산",
        "파주",
        "김포",
        "남양주",
        "의정부",
        "구리",
        "광명",
    ]

    def __init__(self):
        self.client: object | None = None
        if GEMINI_API_KEY and genai is not None:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception:
                logger.exception("Failed to initialize Gemini client; falling back to data-only reply")

        self.data_service: DataService = get_data_service()
        self.simulation_service: SimulationService = get_simulation_service()
        self.competitive_service: CompetitiveAnalysisService = get_competitive_analysis_service()
        self.kakao_service: KakaoLocalService = get_kakao_local_service()
        self.model: str = "gemini-2.5-flash"

        # 시스템 프롬프트
        self.system_prompt: str = self._build_system_prompt()

    def _build_fallback_reply(
        self,
        user_message: str,
        recommendations: list[StructuredRecommendation],
        context: ContextMeta,
    ) -> str:
        """
        LLM 없이도 동작하는 데이터 기반 폴백 응답.
        - API 키 미설정/LLM 장애 시에도 UX가 완전히 깨지지 않게 함.
        """
        lines: list[str] = []

        if not GEMINI_API_KEY or self.client is None:
            lines.append("현재 AI 응답을 생성할 수 없어, **데이터 기반 요약**으로 안내드릴게요.")
        else:
            lines.append("AI 응답 생성에 문제가 있어, **데이터 기반 요약**으로 안내드릴게요.")

        district = context.get("district")
        budget_min = context.get("budget_min")
        budget_max = context.get("budget_max")

        if isinstance(district, str) and district:
            lines.append(f"- 선호 지역: {district}")
        if isinstance(budget_min, int) and isinstance(budget_max, int):
            lines.append(f"- 월세 예산: {budget_min:,}원 ~ {budget_max:,}원")

        lines.append("")
        lines.append(f"질문: {user_message}")

        if not recommendations:
            lines.append("")
            lines.append("조건에 맞는 추천이 없습니다. 예산/지역/상권 유형을 조금 넓혀서 다시 물어보세요.")
            return "\n".join(lines).strip()

        lines.append("")
        lines.append("### 추천 상권 TOP 3")
        for r in recommendations[:3]:
            lines.append(
                "{rank}. {name} ({dtype}) - 성공확률 {prob:.0f}%, 월세 {rent}만원대, 피크 {peak}, 주요 {age}".format(
                    rank=r["rank"],
                    name=r["district_name"],
                    dtype=r["district_type"],
                    prob=r["success_probability"] * 100,
                    rent=r["estimated_rent"] // 10000,
                    peak=r["peak_time"],
                    age=r["main_age_group"],
                )
            )
            if r.get("risk_factors"):
                lines.append(f"   - 리스크: {', '.join(r['risk_factors'][:2])}")
            if r.get("recommendations"):
                lines.append(f"   - 추천: {r['recommendations'][0]}")

        lines.append("")
        lines.append("원하시면 아래 중 하나를 더 알려주시면 추천을 더 좁혀드릴게요:")
        lines.append("- 원하는 시간대(오전/점심/오후/저녁/심야)")
        lines.append("- 타겟(20대/직장인/여성 고객 등)")
        lines.append("- 상권 유형(골목/발달/시장/관광)")

        return "\n".join(lines).strip()

    async def _enrich_recommendations_with_coordinates(
        self, recommendations: list[StructuredRecommendation]
    ) -> None:
        """
        Attach `coordinates` (lat/lng) to the top recommendations when possible.

        Notes:
        - Uses Nominatim (OSM) via `GeocodingService`
        - Never fails the chat response on errors
        - Only enriches TOP 3 to keep latency bounded
        """
        if not recommendations:
            return

        geocoder = get_geocoding_service()

        for r in recommendations[:3]:
            try:
                if r.get("coordinates"):
                    continue

                district_name = (r.get("district_name") or "").strip()
                address = (r.get("address") or "").strip()
                if not address:
                    address = f"서울특별시 {district_name}".strip()

                # Build multiple query candidates because 상권명은 "OO역 2번" / "(...)" 등
                # 일반 주소로 바로 지오코딩이 실패하는 경우가 많음.
                queries: list[str] = []

                def add(q: str) -> None:
                    q = (q or "").strip()
                    if q and q not in queries:
                        queries.append(q)

                add(address)
                add(f"서울 {district_name}")

                # Remove parenthetical info for a simpler place name.
                base = re.sub(r"\(.*?\)", "", district_name).strip()
                add(f"서울 {base}")
                add(base)

                # Drop trailing "N번" suffix (e.g., "강남구청역 2번" -> "강남구청역")
                no_num = re.sub(r"\s+\d+번$", "", base).strip()
                add(f"서울 {no_num}")
                add(no_num)

                # If it contains a station name, geocode by the station (usually works best).
                m_station = re.search(r"(.+?역)", no_num)
                if m_station:
                    station = m_station.group(1).strip()
                    add(f"서울 {station}")
                    add(station)

                # If it contains road name stuck to a district prefix (e.g., "강남언주로"),
                # insert a space to improve geocoding ("강남 언주로").
                seoul_prefixes = [
                    "강남",
                    "서초",
                    "마포",
                    "홍대",
                    "이태원",
                    "성수",
                    "용산",
                    "종로",
                    "강동",
                    "송파",
                    "영등포",
                    "구로",
                    "관악",
                    "동대문",
                    "성북",
                    "노원",
                    "강북",
                    "은평",
                    "서대문",
                    "양천",
                    "강서",
                    "금천",
                    "성동",
                    "광진",
                    "중랑",
                    "도봉",
                    "중구",
                ]
                for p in seoul_prefixes:
                    if no_num.startswith(p) and len(no_num) > len(p):
                        rest = no_num[len(p) :].strip()
                        if rest and not rest.startswith("구"):
                            add(f"서울 {p} {rest}")
                            add(f"{p} {rest}")
                        break

                # Extract inner tokens in parentheses and try them as well.
                m_inner = re.search(r"\((.*?)\)", district_name)
                if m_inner:
                    inner = m_inner.group(1).replace("_", " ")
                    for part in inner.split(","):
                        token = part.strip()
                        if not token:
                            continue
                        token = re.sub(r"\s*\d+번", "", token).strip()
                        if token:
                            add(f"서울 {token}")
                            add(token)

                coords = None
                for q in queries:
                    coords = await geocoder.geocode(q)
                    if coords is not None:
                        break

                if coords is not None:
                    r["coordinates"] = {"lat": coords.lat, "lng": coords.lng}
            except Exception:
                continue

    def _detect_out_of_scope_regions(self, text: str) -> list[str]:
        matches: list[str] = []
        for token in self.OUT_OF_SCOPE_REGIONS:
            if token in text:
                matches.append(token)

        unique: list[str] = []
        for m in matches:
            if m not in unique:
                unique.append(m)
        return unique

    def _build_system_prompt(self) -> str:
        """데이터 기반 시스템 프롬프트 생성"""
        summary = cast(
            Summary,
            cast(object, self.data_service.get_summary()),  # pyright: ignore[reportUnknownMemberType]
        )
        avg_survival_rate = float(summary["avg_survival_rate"])

        return f"""당신은 서울시 커피숍 창업 전문 AI 컨설턴트 "빌더"입니다.

## 역할
- 예비 창업자의 질문에 친절하고 전문적으로 답변
- 실제 서울시 상권 데이터를 기반으로 구체적인 추천 제공
- 복잡한 상권 분석을 쉽게 설명

## 보유 데이터 (64개 필드, 6년 트렌드 분석)
- 서울시 {summary["total_districts"]}개 상권 분석 완료
- 커피숍 {summary["total_stores"]}개 점포 데이터
- 평균 월 매출: {summary["avg_monthly_sales"]:,.0f}원
- 평균 2년 생존율: {avg_survival_rate * 100:.1f}%
- 상권 유형: 골목상권, 발달상권, 전통시장, 관광특구

### 분석 가능한 인사이트
- ⏰ **시간대별 매출**: 새벽(00-06), 오전(06-11), 점심(11-14), 오후(14-17), 저녁(17-21), 심야(21-24)
- 📅 **요일별 매출**: 월~일 각각의 매출 패턴
- 👥 **연령대별 고객**: 10대, 20대, 30대, 40대, 50대, 60대+ 각 연령대 매출 비중
- 🚻 **성별 매출**: 남성/여성 고객 비율
- 📊 **경쟁 현황**: 점포수, 신규 개업, 폐업, 프랜차이즈 비율
- 📈 **6년 트렌드**: 2019~2025년 분기별 매출 추이

## 응답 스타일
1. 간결하고 핵심적으로 답변
2. 구체적인 숫자와 데이터 제시
3. 리스크도 솔직하게 언급
4. 실행 가능한 조언 제공
5. 이모지 적절히 사용

## 추천 시 포함할 정보
- 추천 상권명과 유형
- 예상 월세 범위
- 예상 월 매출 (점포당) + 낙관/비관 시나리오
- 2년 생존율
- ⏰ 피크 시간대/요일 (언제 가장 바쁜지)
- 👥 주요 고객층 (연령대, 성별)
- 주요 리스크
- 핵심 성공 요인

## 💰 시뮬레이션 기능 (매출·투자비·손익분기점)
"여기서 열면 얼마 벌어?", "초기 투자비는?", "몇 개월이면 본전?" 같은 질문에는 시뮬레이션 데이터를 활용해 답변합니다.

### 매출 시뮬레이션
- 점포당 예상 월매출 = 상권 전체 매출 ÷ 점포 수
- 낙관/비관 시나리오 = 같은 상권 유형 25%/75% 분위수
- 평균 객단가 = 월매출 ÷ 월 거래수

### 초기 투자비 (10평 기준, 업계 벤치마크)
- 보증금: 월세 × 10~15배 (골목: ×10, 발달: ×15)
- 인테리어: 평당 160~275만원 (기본/중급/프리미엄)
- 장비/설비: 2,700~4,600만원
- 초기 재료비: 300~500만원
- 기타(허가/간판): 500~1,000만원

### 운영비 (업계 평균 비율)
- 원가율: 32%
- 인건비: 25%
- 공과금: 3.5%
- 기타 운영비: 7.5%

### 손익분기점
- 월 순이익 = 월매출 - 운영비(임대료+원가+인건비+공과금+기타)
- 투자 회수 기간 = 초기 투자비 ÷ 월 순이익
- 일 손익분기 매출 = 월 운영비 ÷ 30

## 🧭 경쟁/차별화 · 원가/마진 · 주차 (카카오 로컬 + 벤치마크)
"이 동네 카페 몇 개야?", "프랜차이즈가 많아?", "뭘로 차별화해야 해?", "주차는 편해?", "메뉴 원가/마진은?" 같은 질문에는 아래 데이터를 활용합니다.

### 경쟁 분석 (카카오 로컬)
- 주변 카페 검색(최대 45개 샘플) 기반으로 카페 유형 분포(프랜차이즈/디저트/브런치/로스터리/테이크아웃 등) 추정
- 시장 공백(gap)과 차별화 전략(우선순위 포함) 제안

### 주차 (카카오 로컬 PK6)
- 추천 상권 좌표 기준 반경 500m 주차장 개수/거리 요약 (좌표가 없으면 생략)

### 메뉴 원가/마진 벤치마크
- 대표 메뉴별 재료비(원가)와 마진율 벤치마크 제공
- 일 100잔 시나리오(매출/원가/매출총이익)로 감각적인 규모 추정

## 시간대 질문 예시 응답
"오전에 손님이 많은 곳" → 오전(06-11) 매출 비중 높은 상권 추천
"직장인 점심 타겟" → 점심(11-14) 매출 비중 높은 상권 추천
"야간 영업" → 저녁(17-21), 심야(21-24) 매출 비중 높은 상권 추천

## 고객층 질문 예시 응답
"20대 타겟" → 20대 매출 비중 높은 상권 추천
"직장인 타겟" → 30-40대 매출 비중 높은 상권 추천
"여성 고객 위주" → 여성 매출 비중 높은 상권 추천

## 주의사항
- 데이터에 없는 내용은 추측이라고 명시
- 투자 결정은 본인 책임임을 언급
- 현장 답사 권유"""

    def _build_chart_data(
        self, recommendation: Recommendation, detail: dict[str, object] | None = None
    ) -> list[ChartData]:
        charts: list[ChartData] = []
        time_data = recommendation.get("time_analysis", {})
        day_data = recommendation.get("day_analysis", {})
        customer_data = recommendation.get("customer_analysis", {})

        def as_dict(value: object) -> dict[str, object]:
            return value if isinstance(value, dict) else {}

        def as_int(value: object) -> int | None:
            return int(value) if isinstance(value, int) else None

        def get_bucket_value(
            breakdown: dict[str, object], bucket: str, field: str
        ) -> int | None:
            b = breakdown.get(bucket)
            if isinstance(b, dict):
                return as_int(b.get(field))
            return None

        def get_nested_int(root: dict[str, object], keys: list[str]) -> int | None:
            cur: object = root
            for k in keys:
                if not isinstance(cur, dict):
                    return None
                cur = cur.get(k)
            return as_int(cur)

        time_breakdown = as_dict(detail.get("time_breakdown")) if detail else {}
        day_breakdown = as_dict(detail.get("day_breakdown")) if detail else {}
        customer_breakdown = as_dict(detail.get("customer_breakdown")) if detail else {}

        def format_label(sales: int | None, transactions: int | None) -> str:
            parts: list[str] = []
            if sales is not None:
                parts.append(f"매출 {sales:,}원")
            if transactions is not None:
                parts.append(f"거래 {transactions:,}건")
            return " · ".join(parts) if parts else ""

        def to_float(value: object) -> float:
            if isinstance(value, (int, float)):
                return float(value)
            return 0.0

        if time_data:
            charts.append(
                {
                    "type": "time",
                    "title": f"{recommendation.get('district_name', '')} 시간대별 매출 비중",
                    "data": [
                        {
                            "name": "00-06",
                            "value": to_float(time_data.get("time_00_06")),
                            "label": format_label(
                                get_bucket_value(time_breakdown, "새벽(0-6시)", "sales"),
                                get_bucket_value(time_breakdown, "새벽(0-6시)", "transactions"),
                            ),
                        },
                        {
                            "name": "06-11",
                            "value": to_float(time_data.get("time_06_11")),
                            "label": format_label(
                                get_bucket_value(time_breakdown, "아침(6-11시)", "sales"),
                                get_bucket_value(time_breakdown, "아침(6-11시)", "transactions"),
                            ),
                        },
                        {
                            "name": "11-14",
                            "value": to_float(time_data.get("time_11_14")),
                            "label": format_label(
                                get_bucket_value(time_breakdown, "점심(11-14시)", "sales"),
                                get_bucket_value(time_breakdown, "점심(11-14시)", "transactions"),
                            ),
                        },
                        {
                            "name": "14-17",
                            "value": to_float(time_data.get("time_14_17")),
                            "label": format_label(
                                get_bucket_value(time_breakdown, "오후(14-17시)", "sales"),
                                get_bucket_value(time_breakdown, "오후(14-17시)", "transactions"),
                            ),
                        },
                        {
                            "name": "17-21",
                            "value": to_float(time_data.get("time_17_21")),
                            "label": format_label(
                                get_bucket_value(time_breakdown, "저녁(17-21시)", "sales"),
                                get_bucket_value(time_breakdown, "저녁(17-21시)", "transactions"),
                            ),
                        },
                        {
                            "name": "21-24",
                            "value": to_float(time_data.get("time_21_24")),
                            "label": format_label(
                                get_bucket_value(time_breakdown, "밤(21-24시)", "sales"),
                                get_bucket_value(time_breakdown, "밤(21-24시)", "transactions"),
                            ),
                        },
                    ],
                }
            )

        if day_data:
            charts.append(
                {
                    "type": "day",
                    "title": f"{recommendation.get('district_name', '')} 요일별 매출 비중",
                    "data": [
                        {
                            "name": "월",
                            "value": to_float(day_data.get("mon")),
                            "label": format_label(
                                get_bucket_value(day_breakdown, "월", "sales"),
                                get_bucket_value(day_breakdown, "월", "transactions"),
                            ),
                        },
                        {
                            "name": "화",
                            "value": to_float(day_data.get("tue")),
                            "label": format_label(
                                get_bucket_value(day_breakdown, "화", "sales"),
                                get_bucket_value(day_breakdown, "화", "transactions"),
                            ),
                        },
                        {
                            "name": "수",
                            "value": to_float(day_data.get("wed")),
                            "label": format_label(
                                get_bucket_value(day_breakdown, "수", "sales"),
                                get_bucket_value(day_breakdown, "수", "transactions"),
                            ),
                        },
                        {
                            "name": "목",
                            "value": to_float(day_data.get("thu")),
                            "label": format_label(
                                get_bucket_value(day_breakdown, "목", "sales"),
                                get_bucket_value(day_breakdown, "목", "transactions"),
                            ),
                        },
                        {
                            "name": "금",
                            "value": to_float(day_data.get("fri")),
                            "label": format_label(
                                get_bucket_value(day_breakdown, "금", "sales"),
                                get_bucket_value(day_breakdown, "금", "transactions"),
                            ),
                        },
                        {
                            "name": "토",
                            "value": to_float(day_data.get("sat")),
                            "label": format_label(
                                get_bucket_value(day_breakdown, "토", "sales"),
                                get_bucket_value(day_breakdown, "토", "transactions"),
                            ),
                        },
                        {
                            "name": "일",
                            "value": to_float(day_data.get("sun")),
                            "label": format_label(
                                get_bucket_value(day_breakdown, "일", "sales"),
                                get_bucket_value(day_breakdown, "일", "transactions"),
                            ),
                        },
                    ],
                }
            )

        if customer_data:
            charts.append(
                {
                    "type": "age",
                    "title": f"{recommendation.get('district_name', '')} 연령대별 매출 비중",
                    "data": [
                        {
                            "name": "10대",
                            "value": to_float(customer_data.get("age_10")),
                            "label": format_label(
                                get_nested_int(customer_breakdown, ["age", "10대", "sales"]),
                                get_nested_int(customer_breakdown, ["age", "10대", "transactions"]),
                            ),
                        },
                        {
                            "name": "20대",
                            "value": to_float(customer_data.get("age_20")),
                            "label": format_label(
                                get_nested_int(customer_breakdown, ["age", "20대", "sales"]),
                                get_nested_int(customer_breakdown, ["age", "20대", "transactions"]),
                            ),
                        },
                        {
                            "name": "30대",
                            "value": to_float(customer_data.get("age_30")),
                            "label": format_label(
                                get_nested_int(customer_breakdown, ["age", "30대", "sales"]),
                                get_nested_int(customer_breakdown, ["age", "30대", "transactions"]),
                            ),
                        },
                        {
                            "name": "40대",
                            "value": to_float(customer_data.get("age_40")),
                            "label": format_label(
                                get_nested_int(customer_breakdown, ["age", "40대", "sales"]),
                                get_nested_int(customer_breakdown, ["age", "40대", "transactions"]),
                            ),
                        },
                        {
                            "name": "50대",
                            "value": to_float(customer_data.get("age_50")),
                            "label": format_label(
                                get_nested_int(customer_breakdown, ["age", "50대", "sales"]),
                                get_nested_int(customer_breakdown, ["age", "50대", "transactions"]),
                            ),
                        },
                        {
                            "name": "60대+",
                            "value": to_float(customer_data.get("age_60")),
                            "label": format_label(
                                get_nested_int(customer_breakdown, ["age", "60대+", "sales"]),
                                get_nested_int(customer_breakdown, ["age", "60대+", "transactions"]),
                            ),
                        },
                    ],
                }
            )

            charts.append(
                {
                    "type": "gender",
                    "title": f"{recommendation.get('district_name', '')} 성별 매출 비중",
                    "data": [
                        {
                            "name": "남성",
                            "value": to_float(customer_data.get("male_ratio")),
                            "label": format_label(
                                get_nested_int(customer_breakdown, ["gender", "male", "sales"]),
                                get_nested_int(customer_breakdown, ["gender", "male", "transactions"]),
                            ),
                        },
                        {
                            "name": "여성",
                            "value": to_float(customer_data.get("female_ratio")),
                            "label": format_label(
                                get_nested_int(customer_breakdown, ["gender", "female", "sales"]),
                                get_nested_int(customer_breakdown, ["gender", "female", "transactions"]),
                            ),
                        },
                    ],
                }
            )

        return charts

    def _generate_suggested_questions(
        self, context: ContextMeta, recommendations: list[StructuredRecommendation]
    ) -> list[str]:
        questions: list[str] = []
        if recommendations:
            top = recommendations[0]
            district_name = top["district_name"]
            estimated_rent = top["estimated_rent"]
            peak_time = top["peak_time"]
            questions.append(
                f"{district_name}에서 월세 {estimated_rent // 10000}만원대 상권을 더 추천해줘"
            )
            questions.append(
                f"{district_name}의 피크 시간대 {peak_time}에 맞는 운영 전략은?"
            )

        district = context.get("district")
        if isinstance(district, str) and district:
            questions.append(f"{district}에서 경쟁이 덜한 상권은 어디야?")

        time_preference = context.get("time_preference")
        if isinstance(time_preference, str):
            time_name = {
                "late_night": "심야",
                "morning": "오전",
                "lunch": "점심",
                "afternoon": "오후",
                "evening": "저녁",
            }.get(time_preference, time_preference)
            questions.append(f"{time_name} 시간대 매출이 강한 상권을 더 알려줘")

        age_target = context.get("age_target")
        if isinstance(age_target, str):
            age_name = {
                "10": "10대",
                "20": "20대",
                "30": "30대",
                "30-40": "30-40대",
                "40": "40대",
                "50": "50대",
                "60": "60대+",
            }.get(age_target, age_target)
            questions.append(f"{age_name} 고객 비중이 높은 상권을 보여줘")

        unique_questions: list[str] = []
        for q in questions:
            if q not in unique_questions:
                unique_questions.append(q)

        return unique_questions[:4]

    def _should_fetch_local_insights(self, message: str) -> bool:
        """Decide whether to call external local APIs.

        We keep this conservative to bound latency/cost.
        """
        text = (message or "").strip()
        if not text:
            return False

        keywords = [
            "경쟁",
            "차별",
            "프랜차이즈",
            "주변 카페",
            "카페 몇",
            "카페가 몇",
            "원가",
            "마진",
            "메뉴",
            "주차",
            "주차장",
        ]
        return any(k in text for k in keywords)

    async def _build_local_insights_context(
        self,
        message: str,
        recommendations: list[StructuredRecommendation],
    ) -> str:
        """Build best-effort context from Kakao Local + benchmarks.

        - Only uses TOP1 recommendation
        - Never raises (caller should also guard)
        """
        if not recommendations:
            return ""
        if not self._should_fetch_local_insights(message):
            return ""
        if not getattr(self.kakao_service, "available", False):
            return ""

        top = recommendations[0]
        district_name = (top.get("district_name") or "").strip()
        if not district_name:
            return ""

        coords = top.get("coordinates")
        if not coords:
            try:
                geocoder = get_geocoding_service()
                c = await asyncio.wait_for(
                    geocoder.geocode(f"서울 {district_name}"),
                    timeout=3.5,
                )
                if c is not None:
                    coords = {"lat": c.lat, "lng": c.lng}
                    top["coordinates"] = coords
            except Exception:
                coords = None

        x = None
        y = None
        if isinstance(coords, dict) and "lng" in coords and "lat" in coords:
            try:
                x = float(coords["lng"])
                y = float(coords["lat"])
            except Exception:
                x = None
                y = None

        analysis_task: asyncio.Task[object] | None = None
        parking_task: asyncio.Task[object] | None = None

        try:
            analysis_task = asyncio.create_task(
                self.competitive_service.analyze_competition(query=district_name, x=x, y=y)
            )
        except Exception:
            analysis_task = None

        if x is not None and y is not None:
            try:
                parking_task = asyncio.create_task(
                    self.kakao_service.search_nearby_parking(x=x, y=y, radius=500, size=10)
                )
            except Exception:
                parking_task = None

        analysis = None
        if analysis_task is not None:
            try:
                analysis = await asyncio.wait_for(analysis_task, timeout=6.5)
            except Exception:
                analysis = None

        parking = None
        if parking_task is not None:
            try:
                parking = await asyncio.wait_for(parking_task, timeout=4.0)
            except Exception:
                parking = None

        menu_costs = None
        try:
            menu_costs = CompetitiveAnalysisService.get_menu_costs()
        except Exception:
            menu_costs = None

        lines: list[str] = []
        lines.append("## 경쟁/차별화·주차·원가 (카카오 로컬 + 벤치마크)")
        lines.append(f"- 기준 상권: {district_name}")

        if analysis:
            total = int(analysis.get("total_nearby_cafes", 0))
            lines.append(f"- 주변 카페(샘플): {total}개")

            cafe_types = analysis.get("cafe_types", [])
            if isinstance(cafe_types, list) and cafe_types:
                top_types: list[str] = []
                for item in cafe_types[:4]:
                    try:
                        top_types.append(f"{item['type']} {item['ratio']}%")
                    except Exception:
                        continue
                if top_types:
                    lines.append(f"- 유형 분포: {', '.join(top_types)}")

            gaps = analysis.get("market_gaps", [])
            if isinstance(gaps, list) and gaps:
                gap_texts: list[str] = []
                for g in gaps[:3]:
                    try:
                        gap_texts.append(f"{g['gap_type']} (점수 {g['opportunity_score']})")
                    except Exception:
                        continue
                if gap_texts:
                    lines.append(f"- 시장 공백: {', '.join(gap_texts)}")

            strategies = analysis.get("strategies", [])
            if isinstance(strategies, list) and strategies:
                strategy_texts: list[str] = []
                for s in strategies[:3]:
                    try:
                        strategy_texts.append(f"{s['strategy']}[{s['priority']}]")
                    except Exception:
                        continue
                if strategy_texts:
                    lines.append(f"- 차별화 아이디어: {', '.join(strategy_texts)}")

            competitors = analysis.get("top_competitors", [])
            if isinstance(competitors, list) and competitors:
                names: list[str] = []
                for c in competitors[:5]:
                    try:
                        names.append(str(c.get("name")))
                    except Exception:
                        continue
                if names:
                    lines.append(f"- 주요 경쟁자 예시: {', '.join(names)}")

        if parking:
            try:
                pc = int(parking.get("total_count", 0))
                nearest = parking.get("stores", [])
                nearest_name = ""
                nearest_dist = ""
                if isinstance(nearest, list) and nearest:
                    nearest_name = str(nearest[0].get("name", ""))
                    d = nearest[0].get("distance")
                    if isinstance(d, int) and d > 0:
                        nearest_dist = f" ({d}m)"
                if pc > 0:
                    lines.append(
                        f"- 주차(500m): {pc}개" + (f" | 가장 가까운: {nearest_name}{nearest_dist}" if nearest_name else "")
                    )
                else:
                    lines.append("- 주차(500m): 결과 없음")
            except Exception:
                pass

        if menu_costs:
            try:
                avg_margin_rate = float(menu_costs.get("avg_margin_rate", 0.0))
                daily = menu_costs.get("daily_sales_scenario", {})
                daily_revenue = int(daily.get("daily_revenue", 0))
                daily_cogs = int(daily.get("daily_cogs", 0))
                lines.append(
                    f"- 메뉴 원가/마진: 평균 마진율 {avg_margin_rate * 100:.1f}% | 일100잔 시나리오 매출 {daily_revenue:,}원 / 원가 {daily_cogs:,}원"
                )
            except Exception:
                pass

        return "\n".join(lines).strip()

    def _normalize_budget_value(self, value: int, unit: str) -> int:
        if "백만" in unit:
            return value * 1000000
        return value * 10000

    def _extract_context_from_text(self, text: str) -> ConversationContext:
        districts = [
            "강남",
            "서초",
            "마포",
            "홍대",
            "이태원",
            "성수",
            "용산",
            "종로",
            "강동",
            "송파",
            "영등포",
            "구로",
            "관악",
            "동대문",
            "성북",
            "노원",
            "강북",
            "은평",
            "서대문",
            "양천",
            "강서",
            "금천",
            "성동",
            "광진",
            "중랑",
            "도봉",
            "중구",
        ]

        district = next((d for d in districts if d in text), None)

        budget_min = None
        budget_max = None
        range_match = re.search(r"(\d+)\s*~\s*(\d+)\s*(만원|만|백만원|백만)", text)
        if range_match:
            start_value = int(range_match.group(1))
            end_value = int(range_match.group(2))
            unit = range_match.group(3)
            budget_min = self._normalize_budget_value(start_value, unit)
            budget_max = self._normalize_budget_value(end_value, unit)
        else:
            budget_match = re.search(r"(\d+)\s*(만원|만|백만원|백만)", text)
            if budget_match:
                amount = self._normalize_budget_value(
                    int(budget_match.group(1)), budget_match.group(2)
                )
                budget_min = int(amount * 0.7)
                budget_max = int(amount * 1.3)
            else:
                budget_match = re.search(r"예산\s*(\d+)", text)
                if budget_match:
                    amount = int(budget_match.group(1)) * 10000
                    budget_min = int(amount * 0.7)
                    budget_max = int(amount * 1.3)

        area_type = None
        if "골목" in text:
            area_type = "골목상권"
        elif any(k in text for k in ["발달", "번화가", "대로"]):
            area_type = "발달상권"
        elif any(k in text for k in ["시장", "전통"]):
            area_type = "전통시장"
        elif "관광" in text:
            area_type = "관광특구"

        time_preference = None
        if any(k in text for k in ["새벽", "심야", "밤", "야간"]):
            time_preference = "late_night"
        elif any(k in text for k in ["아침", "오전", "출근"]):
            time_preference = "morning"
        elif any(k in text for k in ["점심", "런치"]):
            time_preference = "lunch"
        elif any(k in text for k in ["오후", "티타임"]):
            time_preference = "afternoon"
        elif any(k in text for k in ["저녁", "퇴근"]):
            time_preference = "evening"

        age_target = None
        if any(k in text for k in ["10대", "청소년", "학생"]):
            age_target = "10"
        elif any(k in text for k in ["20대", "대학생", "MZ"]):
            age_target = "20"
        elif "30대" in text:
            age_target = "30"
        elif "직장인" in text:
            age_target = "30-40"
        elif any(k in text for k in ["40대", "중년"]):
            age_target = "40"
        elif any(k in text for k in ["50대", "5060"]):
            age_target = "50"
        elif any(k in text for k in ["60대", "시니어", "어르신"]):
            age_target = "60"

        gender_target = None
        if any(k in text for k in ["여성", "여자", "여성고객"]):
            gender_target = "female"
        elif any(k in text for k in ["남성", "남자", "남성고객"]):
            gender_target = "male"

        cafe_type = None
        cafe_type_map = {
            "테이크아웃": "takeout",
            "브런치": "brunch",
            "디저트": "dessert",
            "베이커리": "bakery",
            "작업": "work",
            "스터디": "study",
            "로스터리": "roastery",
            "스페셜티": "specialty",
        }
        for key, value in cafe_type_map.items():
            if key in text:
                cafe_type = value
                break

        return ConversationContext(
            district=district,
            budget_min=budget_min,
            budget_max=budget_max,
            area_type=area_type,
            time_preference=time_preference,
            age_target=age_target,
            gender_target=gender_target,
            cafe_type=cafe_type,
        )

    def _merge_context(
        self,
        base: ConversationContext,
        incoming: ConversationContext,
        source: str,
    ) -> ConversationContext:
        if incoming.district is not None and incoming.district != base.district:
            logger.info(
                "Context updated from %s: district %s -> %s",
                source,
                base.district,
                incoming.district,
            )
            base.district = incoming.district
        if incoming.budget_min is not None and incoming.budget_min != base.budget_min:
            logger.info(
                "Context updated from %s: budget_min %s -> %s",
                source,
                base.budget_min,
                incoming.budget_min,
            )
            base.budget_min = incoming.budget_min
        if incoming.budget_max is not None and incoming.budget_max != base.budget_max:
            logger.info(
                "Context updated from %s: budget_max %s -> %s",
                source,
                base.budget_max,
                incoming.budget_max,
            )
            base.budget_max = incoming.budget_max
        if incoming.area_type is not None and incoming.area_type != base.area_type:
            logger.info(
                "Context updated from %s: area_type %s -> %s",
                source,
                base.area_type,
                incoming.area_type,
            )
            base.area_type = incoming.area_type
        if (
            incoming.time_preference is not None
            and incoming.time_preference != base.time_preference
        ):
            logger.info(
                "Context updated from %s: time_preference %s -> %s",
                source,
                base.time_preference,
                incoming.time_preference,
            )
            base.time_preference = incoming.time_preference
        if incoming.age_target is not None and incoming.age_target != base.age_target:
            logger.info(
                "Context updated from %s: age_target %s -> %s",
                source,
                base.age_target,
                incoming.age_target,
            )
            base.age_target = incoming.age_target
        if (
            incoming.gender_target is not None
            and incoming.gender_target != base.gender_target
        ):
            logger.info(
                "Context updated from %s: gender_target %s -> %s",
                source,
                base.gender_target,
                incoming.gender_target,
            )
            base.gender_target = incoming.gender_target
        if incoming.cafe_type is not None and incoming.cafe_type != base.cafe_type:
            logger.info(
                "Context updated from %s: cafe_type %s -> %s",
                source,
                base.cafe_type,
                incoming.cafe_type,
            )
            base.cafe_type = incoming.cafe_type
        return base

    def _extract_context_from_history(
        self, history: list[HistoryMessage]
    ) -> ConversationContext:
        context = ConversationContext()
        for message in history[-10:]:
            content = message.get("content")
            if not content:
                continue
            extracted = self._extract_context_from_text(content)
            context = self._merge_context(context, extracted, "history")
        return context

    def _compute_merged_context(
        self,
        query: str,
        history: list[HistoryMessage] | None,
        seed_context: ConversationContext | None,
    ) -> ConversationContext:
        base = ConversationContext()
        if seed_context is not None:
            base = self._merge_context(base, seed_context, "seed")
        history_context = self._extract_context_from_history(history or [])
        base = self._merge_context(base, history_context, "history")
        current_context = self._extract_context_from_text(query)
        base = self._merge_context(base, current_context, "current")
        return base

    def _filter_recommendations_by_context(
        self,
        recs: list[Recommendation],
        context: ConversationContext,
    ) -> list[Recommendation]:
        filtered: list[Recommendation] = recs

        if context.time_preference:
            time_map = {
                "late_night": "21-24",
                "morning": "06-11",
                "lunch": "11-14",
                "afternoon": "14-17",
                "evening": "17-21",
            }
            target_time = time_map.get(context.time_preference)
            if target_time:
                time_filtered = [
                    r
                    for r in filtered
                    if r["time_analysis"]["peak_time"] == target_time
                ]
                if time_filtered:
                    filtered = time_filtered

        if context.age_target:
            age_filtered: list[Recommendation] = []
            for r in filtered:
                main_age = r["customer_analysis"]["main_age_group"]
                if context.age_target == "30-40":
                    if "30" in main_age or "40" in main_age:
                        age_filtered.append(r)
                elif context.age_target in main_age:
                    age_filtered.append(r)
            if age_filtered:
                filtered = age_filtered

        if context.gender_target:
            gender_filtered: list[Recommendation] = []
            for r in filtered:
                analysis = r["customer_analysis"]
                male_ratio = analysis["male_ratio"]
                female_ratio = analysis["female_ratio"]
                if context.gender_target == "female" and female_ratio >= 55:
                    gender_filtered.append(r)
                elif context.gender_target == "male" and male_ratio >= 55:
                    gender_filtered.append(r)
            if gender_filtered:
                filtered = gender_filtered

        return filtered

    def _get_relevant_data(
        self,
        query: str,
        history: list[HistoryMessage] | None = None,
        seed_context: ConversationContext | None = None,
        merged_context: ConversationContext | None = None,
    ) -> tuple[str, list[StructuredRecommendation], list[ChartData], ContextMeta]:
        context_parts: list[str] = []
        structured_recommendations: list[StructuredRecommendation] = []
        charts: list[ChartData] = []

        merged_context = merged_context or self._compute_merged_context(query, history, seed_context)

        budget_min = merged_context.budget_min or 1500000
        budget_max = merged_context.budget_max or 10000000

        context_meta: ContextMeta = {
            "district": merged_context.district,
            "budget_min": budget_min,
            "budget_max": budget_max,
            "area_type": merged_context.area_type,
            "time_preference": merged_context.time_preference,
            "age_target": merged_context.age_target,
            "gender_target": merged_context.gender_target,
            "cafe_type": merged_context.cafe_type,
        }

        try:
            recs = cast(
                list[Recommendation],
                self.data_service.get_recommendations(  # pyright: ignore[reportUnknownMemberType]
                    budget_min=budget_min,
                    budget_max=budget_max,
                    preferred_district=merged_context.district,
                    preferred_area_type=merged_context.area_type,
                    top_n=5,
                ),
            )  # type: ignore[reportUnknownMemberType]
            recs = self._filter_recommendations_by_context(recs, merged_context)
        except Exception as exc:
            recs = []
            context_meta["data_error"] = str(exc)

        if recs:
            context_parts.append("## 추천 상권 데이터 (64개 필드 기반 분석)")
            for r in recs:
                ta = r["time_analysis"]
                da = r["day_analysis"]
                ca = r["customer_analysis"]
                comp = r["competition"]

                detail = self.data_service.get_district_detail(r["district_code"])
                sales_detail = ""
                if detail:
                    monthly_sales = detail.get("sales", {}).get("monthly")
                    monthly_transactions = detail.get("sales", {}).get("transactions")
                    avg_ticket = detail.get("sales", {}).get("avg_ticket")
                    if isinstance(monthly_sales, int):
                        sales_detail += f"\n- 월 매출 총액: {monthly_sales:,}원"
                    if isinstance(monthly_transactions, int):
                        sales_detail += f"\n- 월 거래수: {monthly_transactions:,}건"
                    if isinstance(avg_ticket, int):
                        sales_detail += f"\n- 평균 객단가: {avg_ticket:,}원"

                structured_recommendations.append(
                    {
                        "rank": r["rank"],
                        "district_name": r["district_name"],
                        "district_type": r["district_type"],
                        "success_probability": r["success_probability"],
                        "estimated_rent": r["estimated_monthly_rent"],
                        "peak_time": ta["peak_time"],
                        "main_age_group": ca["main_age_group"],
                        "risk_factors": r["risk_factors"],
                        "recommendations": r["recommendations"],
                        "address": r["address"],
                        "monthly_sales": r["estimated_monthly_sales"],
                        "store_count": int(comp.get("store_count", 0)),
                        "survival_rate": r["survival_rate_2y"],
                        "key_success_factors": r["key_success_factors"],
                        "coordinates": None,
                    }
                )

                sim = self.simulation_service.simulate(r["district_code"])
                sim_text = ""
                if sim:
                    rev = sim["revenue"]
                    sc_data = sim["startup_cost"]
                    be = sim["break_even"]
                    sim_text = f"""
- 💰 매출 시뮬레이션 (점포당):
  - 예상 월매출: {rev["monthly_sales_per_store"]:,}원 (비관 {rev["pessimistic"]:,} ~ 낙관 {rev["optimistic"]:,})
  - 일평균 매출: {rev["daily_sales"]:,}원
  - 평균 객단가: {rev["avg_ticket"]:,}원
  - 월 거래수: {rev["monthly_transactions_per_store"]:,}건
- 🏗️ 초기 투자비 (10평/중급 기준): {sc_data["total_min"] // 10000:,}만 ~ {sc_data["total_max"] // 10000:,}만원
  - 보증금: {sc_data["deposit"] // 10000:,}만원 | 인테리어: {sc_data["interior"] // 10000:,}만원 | 장비: {sc_data["equipment_min"] // 10000:,}~{sc_data["equipment_max"] // 10000:,}만원
- 📉 손익분기점:
  - 월 순이익: {be["monthly_net_profit"]:,}원 (영업이익률 {be["net_profit_margin"] * 100:.1f}%)
  - 투자 회수: {be["break_even_months_min"]}~{be["break_even_months_max"]}개월
  - 일 손익분기 매출: {be["daily_break_even_sales"]:,}원"""

                rec_text = f"""
### {r["rank"]}. {r["district_name"]} ({r["district_type"]})
- 주소: {r["address"]}
- 성공확률: {r["success_probability"] * 100:.0f}%
- 예상 월세: {r["estimated_monthly_rent"]:,}원
- 예상 월매출: {r["estimated_monthly_sales"]:,}원
{sales_detail}
- 2년 생존율: {r["survival_rate_2y"] * 100:.0f}%
- 경쟁 점포: {comp.get("store_count", 0)}개
- ⏰ 피크 시간대: {ta.get("peak_time", "정보없음")}
- 📅 피크 요일: {da.get("peak_day", "정보없음")}
- 👥 주요 고객층: {ca.get("main_age_group", "정보없음")}
- 🚻 성별 비율: 남성 {ca.get("male_ratio", 0):.1f}% / 여성 {ca.get("female_ratio", 0):.1f}%
- ⚠️ 리스크: {", ".join(r["risk_factors"][:2]) if r["risk_factors"] else "특별한 리스크 없음"}
- ✅ 성공요인: {", ".join(r["key_success_factors"][:3])}
{sim_text}"""

                context_parts.append(rec_text)

            top_detail = self.data_service.get_district_detail(recs[0]["district_code"])
            charts = self._build_chart_data(recs[0], top_detail)

            if (
                merged_context.time_preference
                or merged_context.age_target
                or merged_context.gender_target
                or merged_context.cafe_type
            ):
                tips: list[str] = []
                if merged_context.time_preference:
                    time_names = {
                        "late_night": "심야(21-24시)",
                        "morning": "오전(06-11시)",
                        "lunch": "점심(11-14시)",
                        "afternoon": "오후(14-17시)",
                        "evening": "저녁(17-21시)",
                    }
                    tips.append(
                        f"시간대 선호: {time_names.get(merged_context.time_preference, merged_context.time_preference)}"
                    )
                if merged_context.age_target:
                    age_names = {
                        "10": "10대",
                        "20": "20대",
                        "30": "30대",
                        "30-40": "30-40대",
                        "40": "40대",
                        "50": "50대",
                        "60": "60대+",
                    }
                    tips.append(
                        f"타겟 연령대: {age_names.get(merged_context.age_target, merged_context.age_target)}"
                    )
                if merged_context.gender_target:
                    tips.append(
                        f"타겟 성별: {'여성' if merged_context.gender_target == 'female' else '남성'}"
                    )
                if merged_context.cafe_type:
                    tips.append(f"카페 유형: {merged_context.cafe_type}")

                context_parts.append(f"\n## 사용자 선호 분석\n- " + "\n- ".join(tips))

        if not context_parts:
            summary = cast(
                Summary,
                cast(object, self.data_service.get_summary()),  # pyright: ignore[reportUnknownMemberType]
            )
            context_parts.append(f"""## 서울시 커피숍 상권 현황 (2019-2025 데이터)
- 분석 상권 수: {summary["total_districts"]}개
- 총 커피숍 수: {summary["total_stores"]}개
- 평균 월 매출: {summary["avg_monthly_sales"]:,.0f}원
- 평균 2년 생존율: {summary["avg_survival_rate"] * 100:.1f}%
- 상권 유형별: 골목상권 {summary["district_types"].get("골목상권", 0)}개, 발달상권 {summary["district_types"].get("발달상권", 0)}개

### 분석 가능 항목
- 시간대별 매출 분석 (6개 시간대)
- 요일별 매출 분석 (월~일)
- 연령대별 고객 분석 (10대~60대+)
- 성별 매출 분석
- 개폐업 동향 및 프랜차이즈 비율
- 6년 트렌드 분석
""")

        return "\n".join(context_parts), structured_recommendations, charts, context_meta

    async def chat(
        self,
        message: str,
        history: list[HistoryMessage] | None = None,
        seed_context: ConversationContext | None = None,
    ) -> StructuredChatPayload:
        """대화형 응답 생성"""

        # Seoul-only scope guard (beta)
        out_of_scope = self._detect_out_of_scope_regions(message)
        if out_of_scope and "서울" not in message:
            reply = (
                "현재 베타 서비스에서는 **서울 지역 데이터만** 제공하고 있어요.\n"
                f"입력하신 지역({', '.join(out_of_scope)})은 아직 지원하지 않습니다.\n\n"
                "서울에서 희망 지역(예: 강남/홍대/성수/이태원/종로 등)과 예산(월세)을 알려주시면\n"
                "서울 상권 데이터 기반으로 추천해드릴게요."
            )
            return {
                "reply": reply,
                "recommendations": [],
                "charts": [],
                "suggested_questions": [
                    "서울 강남에서 월세 300만원대 카페 추천해줘",
                    "서울 홍대에서 20대 여성 타겟 상권 추천해줘",
                    "서울 성수 골목상권 추천해줘",
                    "서울에서 점심 피크 상권 알려줘",
                ],
                "context": {"unsupported_regions": out_of_scope},
            }

        merged_context = self._compute_merged_context(message, history, seed_context)
        missing_district = merged_context.district is None
        missing_budget = merged_context.budget_max is None

        if missing_district or missing_budget:
            known_parts: list[str] = []
            if merged_context.district:
                known_parts.append(f"지역: {merged_context.district}")
            if merged_context.budget_min is not None and merged_context.budget_max is not None:
                known_parts.append(
                    f"월세: {merged_context.budget_min // 10000:,}~{merged_context.budget_max // 10000:,}만원"
                )
            if merged_context.cafe_type:
                known_parts.append(f"카페 유형: {merged_context.cafe_type}")

            reply_lines: list[str] = []
            reply_lines.append("추천을 정확하게 하려면 몇 가지만 확인할게요.")
            if known_parts:
                reply_lines.append(f"(현재 파악된 정보: {', '.join(known_parts)})")
            if missing_district:
                reply_lines.append("1) 희망 지역이 어디인가요? (예: 강남/홍대/성수/종로)")
            if missing_budget:
                reply_lines.append("2) 월세 예산은 어느 정도인가요? (예: 200~400만원)")
            reply_lines.append("선택) 타겟 고객(직장인/20대/여성)이나 컨셉(테이크아웃/디저트/브런치/작업)도 알려주면 더 정확해요.")

            district = merged_context.district or ""
            suggested: list[str] = []
            if missing_district and missing_budget:
                suggested = [
                    "서울 홍대에서 월세 300만원대 카페 추천해줘",
                    "서울 강남에서 월세 200~400만원 카페 추천해줘",
                    "서울 성수에서 월세 250만원대, 테이크아웃 위주 추천해줘",
                    "서울 종로에서 월세 200~300만원, 직장인 점심 타겟 추천해줘",
                ]
            elif missing_district and not missing_budget:
                bmin = merged_context.budget_min or int((merged_context.budget_max or 3000000) * 0.7)
                bmax = merged_context.budget_max or int((merged_context.budget_min or 3000000) * 1.3)
                suggested = [
                    f"서울 홍대에서 월세 {bmin // 10000:,}~{bmax // 10000:,}만원 카페 추천해줘",
                    f"서울 강남에서 월세 {bmin // 10000:,}~{bmax // 10000:,}만원 카페 추천해줘",
                    f"서울 성수에서 월세 {bmin // 10000:,}~{bmax // 10000:,}만원 카페 추천해줘",
                ]
            elif missing_budget and district:
                suggested = [
                    f"서울 {district}에서 월세 200~300만원대 카페 추천해줘",
                    f"서울 {district}에서 월세 300~400만원대 카페 추천해줘",
                    f"서울 {district}에서 월세 400~600만원대, 발달상권 추천해줘",
                ]
            else:
                suggested = [
                    "서울 강남에서 월세 300만원대 카페 추천해줘",
                    "서울 홍대에서 20대 여성 타겟 상권 추천해줘",
                    "서울 성수 골목상권 추천해줘",
                ]

            return {
                "reply": "\n".join(reply_lines).strip(),
                "recommendations": [],
                "charts": [],
                "suggested_questions": suggested,
                "context": {
                    "district": merged_context.district,
                    "budget_min": merged_context.budget_min,
                    "budget_max": merged_context.budget_max,
                    "area_type": merged_context.area_type,
                    "time_preference": merged_context.time_preference,
                    "age_target": merged_context.age_target,
                    "gender_target": merged_context.gender_target,
                    "cafe_type": merged_context.cafe_type,
                    "intake_needs": [
                        k
                        for k in [
                            "district" if missing_district else "",
                            "budget" if missing_budget else "",
                        ]
                        if k
                    ],
                },
            }

        # 관련 데이터 조회
        context_text, recommendations, charts, context_meta = self._get_relevant_data(
            message,
            history,
            seed_context=seed_context,
            merged_context=merged_context,
        )

        # Best-effort local insights (Kakao): only when user asks.
        try:
            local_insights = await self._build_local_insights_context(message, recommendations)
            if local_insights:
                context_text = f"{context_text}\n\n{local_insights}".strip()
        except Exception:
            pass

        # 프롬프트 구성
        full_prompt = f"""{self.system_prompt}

---

        {context_text}

---

사용자: {message}

위 데이터를 참고하여 친절하고 전문적으로 답변해주세요."""

        # 이전 대화가 있으면 포함
        if history:
            history_text = "\n".join(
                [
                    f"{'사용자' if h['role'] == 'user' else 'AI'}: {h['content']}"
                    for h in history[-4:]  # 최근 4개만
                ]
            )
            full_prompt = f"""{self.system_prompt}

---

이전 대화:
{history_text}

---

            {context_text}

---

사용자: {message}

위 데이터와 이전 대화를 참고하여 답변해주세요."""

        # Gemini 호출
        reply_text = ""
        try:
            if self.client is None:
                raise RuntimeError("Gemini client is not configured")

            client = cast(_GeminiClient, self.client)
            response = client.models.generate_content(
                model=self.model,
                contents=full_prompt,
            )
            reply_text = response.text or ""
        except Exception as exc:
            context_meta["llm_error"] = str(exc)
            reply_text = self._build_fallback_reply(message, recommendations, context_meta)

        if out_of_scope:
            context_meta["unsupported_regions"] = out_of_scope
            reply_text = (
                "참고: 현재 베타 서비스에서는 **서울 지역 데이터만** 지원합니다.\n"
                f"({', '.join(out_of_scope)}) 관련 추천은 아직 제공하지 못해요.\n\n"
            ) + reply_text

        suggested_questions = self._generate_suggested_questions(context_meta, recommendations)

        # Map enrichment (best-effort): attach coordinates for in-app map rendering.
        await self._enrich_recommendations_with_coordinates(recommendations)

        return {
            "reply": reply_text,
            "recommendations": recommendations,
            "charts": charts,
            "suggested_questions": suggested_questions,
            "context": context_meta,
        }

    def chat_sync(
        self, message: str, history: list[HistoryMessage] | None = None
    ) -> StructuredChatPayload:
        """동기 버전 (테스트용)"""
        import asyncio

        return asyncio.run(self.chat(message, history))


# 싱글톤
_chat_service = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service
