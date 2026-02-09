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

from api.services.data_service import DataService, estimate_rent, get_data_service
from api.services.geocoding_service import get_geocoding_service
from api.services.kakao_local_service import KakaoLocalService, get_kakao_local_service
from api.services.competitive_analysis_service import (
    CompetitiveAnalysis,
    CompetitiveAnalysisService,
    get_competitive_analysis_service,
)
from api.services.simulation_service import SimulationService, get_simulation_service
from api.services.timeline_service import TimelineService, get_timeline_service


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
    district_code: str
    district_name: str
    district_type: str
    success_probability: float
    estimated_rent: int
    peak_time: str
    main_age_group: str
    risk_factors: list[str]
    recommendations: list[str]
    address: str
    # Backward compatible field used by the web UI.
    # NOTE: This represents per-store monthly sales (new store perspective), not total district sales.
    monthly_sales: int
    # New: explicit totals/breakdown helpers for UI
    monthly_sales_total: Optional[int]
    monthly_sales_per_store: Optional[int]
    monthly_transactions_total: Optional[int]
    avg_ticket: Optional[int]
    store_count: int
    survival_rate: float
    key_success_factors: list[str]
    coordinates: Optional[dict[str, float]]
    foot_traffic_total: int
    worker_total: int
    facility_subway: int
    change_indicator: str
    transit_percentile: float
    positioning: str
    positioning_detail: str
    purchasing_power: float
    single_household_ratio: Optional[float]
    income_info: Optional[dict[str, object]]
    scorecard: Optional[dict[str, object]]


class ChartDatum(TypedDict, total=False):
    name: str
    value: float
    label: str
    sales: int
    transactions: int


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
    comparison_failed: bool
    comparison: bool
    trend_request: bool
    trend_error: bool
    keyword: str
    districts: list[str]


class Summary(TypedDict):
    total_districts: int
    total_stores: int
    avg_monthly_sales: int
    avg_survival_rate: float
    district_types: dict[str, int]


class StructuredChatPayload(TypedDict, total=False):
    reply: str
    recommendations: list[StructuredRecommendation]
    charts: list[ChartData]
    suggested_questions: list[str]
    context: ContextMeta
    competitive: dict[str, object]
    simulation: dict[str, object]
    timeline: dict[str, object]
    trademark: dict[str, object]
    support_programs: list[dict[str, object]]
    verdict: dict[str, object]
    trend: dict[str, object]


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

    # Alias: business_type == cafe_type (backward compat)
    @property
    def business_type(self) -> Optional[str]:
        return self.cafe_type

    @business_type.setter
    def business_type(self, value: Optional[str]) -> None:
        self.cafe_type = value


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

    def __init__(self, industry_code: str = "CS100010"):
        self.industry_code = industry_code

        # Load industry config
        from config.industry_config import load_industry_config

        try:
            self.industry_config: dict[str, object] = load_industry_config(industry_code)
        except FileNotFoundError:
            self.industry_config = {}
        self.display_name: str = str(self.industry_config.get("display_name", "카페"))

        self.client: object | None = None
        if GEMINI_API_KEY and genai is not None:
            try:
                self.client = genai.Client(api_key=GEMINI_API_KEY)
            except Exception:
                logger.exception(
                    "Failed to initialize Gemini client; falling back to data-only reply"
                )

        # Use industry-aware services
        self.data_service: DataService = get_data_service(industry_code)
        self.simulation_service: SimulationService = get_simulation_service(industry_code)
        self.competitive_service: CompetitiveAnalysisService = get_competitive_analysis_service(
            industry_code
        )
        self.kakao_service: KakaoLocalService = get_kakao_local_service()
        self.timeline_service: TimelineService = get_timeline_service(industry_code)
        self.model: str = "gemini-2.5-flash"

        # Broad district tokens (구 단위/대표 지역명) used for coarse context extraction.
        # NOTE: These are NOT the 1,077 district names; these are for fallback only.
        self._broad_district_tokens: list[str] = [
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
        self._broad_district_token_set: set[str] = set(self._broad_district_tokens)

        # Fast path index: prefer matching real district_name (e.g., "강남역") from the dataset.
        # This enables disambiguation and avoids collapsing everything into "강남".
        self._district_name_index: list[str] = self._build_district_name_index()

        # 시스템 프롬프트
        self.system_prompt: str = self._build_system_prompt()

    def _sanitize_user_input(self, text: str) -> str:
        """사용자 입력에서 프롬프트 인젝션 시도를 방어"""
        dangerous_patterns = [
            r"(?i)ignore\s+(all\s+)?previous\s+instructions",
            r"(?i)system\s*:\s*",
            r"(?i)\[SYSTEM\s*(OVERRIDE|PROMPT)\]",
            r"(?i)you\s+are\s+now\s+",
            r"(?i)forget\s+(all\s+)?previous",
            r"(?i)new\s+instructions?\s*:",
        ]
        sanitized = text
        for pattern in dangerous_patterns:
            sanitized = re.sub(pattern, "[filtered]", sanitized)
        return sanitized[:5000]

    def _build_district_name_index(self) -> list[str]:
        names: list[str] = []
        try:
            for d in getattr(self.data_service, "districts", []) or []:
                if not isinstance(d, dict):
                    continue
                name = d.get("district_name")
                if isinstance(name, str):
                    name = name.strip()
                    if name:
                        names.append(name)
        except Exception:
            names = []

        # de-dup while preserving first-seen order
        seen: set[str] = set()
        unique: list[str] = []
        for n in names:
            if n in seen:
                continue
            seen.add(n)
            unique.append(n)

        # longest-first so "강남구청(청담역_8번, ...)" wins over "강남구청"
        unique.sort(key=len, reverse=True)
        return unique

    def _top_subdistricts(self, broad: str, limit: int = 4) -> list[dict[str, object]]:
        """Return TOP sub-district candidates for a broad token (e.g. "강남").

        Sorted by monthly_sales desc to surface the canonical places first.
        """
        broad = (broad or "").strip()
        if not broad:
            return []

        matches: list[dict[str, object]] = []
        try:
            for d in getattr(self.data_service, "districts", []) or []:
                if not isinstance(d, dict):
                    continue
                name = d.get("district_name")
                if not isinstance(name, str):
                    continue
                if broad in name:
                    matches.append(d)
        except Exception:
            return []

        def as_int(v: object) -> int:
            try:
                return int(v) if isinstance(v, int) else 0
            except Exception:
                return 0

        # Prefer "{broad}역" when present, then sales.
        def sort_key(d: dict[str, object]) -> tuple[int, int]:
            name = d.get("district_name")
            station_boost = 1 if isinstance(name, str) and name == f"{broad}역" else 0
            sales = as_int(d.get("monthly_sales"))
            return (station_boost, sales)

        matches.sort(key=sort_key, reverse=True)
        return matches[: max(1, limit)]

    def _estimate_monthly_rent_from_district(self, d: dict[str, object]) -> int | None:
        try:
            ms = d.get("monthly_sales")
            sc = d.get("store_count")
            dt = d.get("district_type")
            dc = d.get("district_code")
            if not ms or not isinstance(ms, (int, float)):
                return None
            if not isinstance(dt, str):
                return None
            store_count = int(sc) if isinstance(sc, (int, float)) and sc else 1
            sales_per_store = int(int(ms) / max(1, store_count))
            pctile = self.data_service._sales_percentile.get(str(dc), 0.5) if dc else 0.5
            return estimate_rent(str(dt), sales_per_store, pctile, industry_code=self.industry_code)
        except Exception:
            return None

    def _get_peak_time_slot(self, d: dict[str, object]) -> str:
        """Return peak time slot token (e.g., '11-14')."""
        peak = d.get("peak_time")
        if isinstance(peak, str) and peak:
            return peak

        # Fallback: infer from time bucket sales fields.
        buckets = [
            ("00-06", "time_00_06_sales"),
            ("06-11", "time_06_11_sales"),
            ("11-14", "time_11_14_sales"),
            ("14-17", "time_14_17_sales"),
            ("17-21", "time_17_21_sales"),
            ("21-24", "time_21_24_sales"),
        ]
        best = "11-14"
        best_val = -1
        for label, key in buckets:
            v = d.get(key)
            if isinstance(v, (int, float)) and v > best_val:
                best_val = int(v)
                best = label
        return best

    def _get_main_age_group(self, d: dict[str, object]) -> str:
        """Return main age group label (e.g., '20대')."""
        mag = d.get("main_age_group")
        if isinstance(mag, str) and mag:
            return mag

        buckets = [
            ("10대", "age_10_sales"),
            ("20대", "age_20_sales"),
            ("30대", "age_30_sales"),
            ("40대", "age_40_sales"),
            ("50대", "age_50_sales"),
            ("60대+", "age_60_sales"),
        ]
        best = "20대"
        best_val = -1
        for label, key in buckets:
            v = d.get(key)
            if isinstance(v, (int, float)) and v > best_val:
                best_val = int(v)
                best = label
        return best

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
            lines.append(
                "조건에 맞는 추천이 없습니다. 예산/지역/상권 유형을 조금 넓혀서 다시 물어보세요."
            )
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

    def _detect_comparison_request(self, message: str) -> dict[str, list[str]] | None:
        """
        비교 요청 패턴 감지: "A vs B 비교해줘", "강남 성수 비교", "홍대랑 이태원 비교"
        Returns: {"districts": ["강남", "성수"]} or None
        """
        msg_lower = message.lower()

        # Pattern 1: "A vs B"
        vs_pattern = re.search(r"(\S+)\s*vs\s*(\S+)", msg_lower)
        if vs_pattern:
            return {"districts": [vs_pattern.group(1), vs_pattern.group(2)]}

        # Pattern 2: "비교해줘" with multiple districts
        if "비교" in message:
            # Extract potential district names
            districts = []
            for district_name in self.data_service._district_by_name.keys():
                if district_name in message:
                    districts.append(district_name)

            if len(districts) >= 2:
                return {"districts": districts[:3]}  # Max 3 districts

            # Try broader tokens (강남, 홍대, etc.)
            for token in self._broad_district_token_set:
                if token in message:
                    districts.append(token)

            if len(districts) >= 2:
                return {"districts": districts[:3]}

        return None

    def _detect_trend_request(self, message: str) -> dict[str, object] | None:
        """
        트렌드 분석 요청 패턴 감지:
        - "강남 카페 트렌드", "홍대 카페 검색량", "카페 인기도"
        - "강남 홍대 트렌드 비교", "강남vs홍대 검색 트렌드"

        Returns: {"keyword": str, "districts": list[str]} or None
        """
        msg_lower = message.lower()

        # Trigger keywords
        trend_keywords = ["트렌드", "검색량", "인기도", "검색 추이", "관심도"]
        if not any(kw in message for kw in trend_keywords):
            return None

        # Extract base keyword (업종 이름)
        keyword = self.display_name  # Default to industry name

        # Extract districts
        districts = []

        # Check for district names in the message
        for district_name in self.data_service._district_by_name.keys():
            if district_name in message:
                districts.append(district_name)

        # If no specific district, try broader tokens
        if not districts:
            for token in self._broad_district_token_set:
                if token in message:
                    districts.append(token)

        # If we have districts, this is a trend request
        if districts:
            return {
                "keyword": keyword,
                "districts": districts[:5],  # Max 5 districts for Naver API
            }

        # If no districts but trend keywords present, use default districts
        if any(kw in message for kw in trend_keywords):
            # Use top 5 popular districts as default
            return {"keyword": keyword, "districts": ["강남", "홍대", "성수", "이태원", "종로"]}

        return None

    async def _handle_comparison(self, district_names: list[str]) -> StructuredChatPayload:
        """
        상권 비교 응답 생성
        district_names: 비교할 상권명 리스트 (2-3개)
        """
        from api.services.scorecard_service import get_scorecard_service

        # 상권 데이터 조회
        districts_data = []
        for name in district_names[:3]:
            district = self.data_service.get_district_by_name(name)
            if not district:
                # Try searching
                search_results = self.data_service.search_districts(name, limit=1)
                if search_results:
                    district = search_results[0]

            if district:
                districts_data.append(district)

        if len(districts_data) < 2:
            return {
                "reply": f"'{', '.join(district_names)}' 상권을 찾을 수 없어요. 정확한 상권명을 알려주시면 비교해드릴게요.",
                "recommendations": [],
                "charts": [],
                "suggested_questions": [
                    "홍대입구역 vs 신사역 비교해줘",
                    "강남역 성수동 비교해줘",
                    "이태원역 vs 명동역 비교",
                ],
                "context": {"comparison_failed": True},
            }

        # Scorecard 서비스로 점수 계산
        sc_svc = get_scorecard_service(self.industry_code)
        if not sc_svc._districts:
            sc_svc.set_districts(self.data_service.districts)

        # 추천 카드 생성 (scorecard 포함)
        recommendations = []
        for idx, d in enumerate(districts_data, 1):
            sc = d.get("store_count", 1)
            monthly_sales_per_store = int(d["monthly_sales"] / max(1, sc))
            sales_pct = self.data_service._sales_percentile.get(d["district_code"], 0.5)
            estimated_rent = estimate_rent(
                d["district_type"],
                monthly_sales_per_store,
                sales_pct,
                self.data_service._rent_ranges,
                industry_code=self.industry_code,
            )

            scorecard_result = sc_svc.score_district(d)

            recommendations.append(
                {
                    "rank": idx,
                    "district_code": d["district_code"],
                    "district_name": d["district_name"],
                    "district_type": d["district_type"],
                    "success_probability": d.get("survival_rate", 0.85),
                    "estimated_rent": estimated_rent,
                    "peak_time": self._get_peak_time_slot(d),
                    "main_age_group": self._get_main_age_group(d),
                    "risk_factors": [],
                    "recommendations": [],
                    "monthly_sales": monthly_sales_per_store,
                    "store_count": d.get("store_count", 0),
                    "survival_rate": d.get("survival_rate", 0),
                    "scorecard": scorecard_result,
                }
            )

        # 비교 텍스트 생성
        d1 = districts_data[0]
        d2 = districts_data[1]
        d1_name = d1["district_name"]
        d2_name = d2["district_name"]

        comparison_lines = [
            f"**{d1_name}** vs **{d2_name}** 비교 분석입니다.\n",
        ]

        # 5개 카테고리 비교
        if (
            len(recommendations) >= 2
            and recommendations[0].get("scorecard")
            and recommendations[1].get("scorecard")
        ):
            sc1 = recommendations[0]["scorecard"]
            sc2 = recommendations[1]["scorecard"]

            comparison_lines.append("**종합 점수**")
            comparison_lines.append(
                f"- {d1_name}: {sc1['total_score']:.1f}점 (상위 {100 - sc1['percentile']:.0f}%)"
            )
            comparison_lines.append(
                f"- {d2_name}: {sc2['total_score']:.1f}점 (상위 {100 - sc2['percentile']:.0f}%)"
            )
            comparison_lines.append("")

            # 카테고리별 차이 분석
            cat1 = {c["name"]: c["score"] for c in sc1["categories"]}
            cat2 = {c["name"]: c["score"] for c in sc2["categories"]}

            max_diff_cat = None
            max_diff_val = 0
            for cat_name in cat1.keys():
                diff = abs(cat1[cat_name] - cat2[cat_name])
                if diff > max_diff_val:
                    max_diff_val = diff
                    max_diff_cat = cat_name

            if max_diff_cat:
                winner = d1_name if cat1[max_diff_cat] > cat2[max_diff_cat] else d2_name
                comparison_lines.append(
                    f"**가장 큰 차이: {max_diff_cat}** - {winner}이(가) 우세합니다."
                )

        comparison_lines.append("\n레이더 차트와 상세 비교 테이블을 확인하세요.")

        reply = "\n".join(comparison_lines)

        return {
            "reply": reply,
            "recommendations": recommendations,
            "charts": [],
            "suggested_questions": [
                f"{d1_name}에서 {self.display_name} 시뮬레이션 보여줘",
                f"{d2_name} 경쟁 분석 해줘",
                "다른 상권도 비교해줘",
            ],
            "context": {
                "comparison": True,
                "districts": [d["district_name"] for d in districts_data],
            },
        }

    async def _handle_trend_request(
        self, keyword: str, districts: list[str] | None, message: str
    ) -> StructuredChatPayload:
        """
        트렌드 분석 요청 처리
        Naver DataLab API를 사용하여 검색 트렌드 조회 및 차트 생성

        Args:
            keyword: 기본 키워드 (업종명)
            districts: 비교할 지역 리스트
            message: 원본 메시지
        """
        from api.services.trend_service import get_trend_service

        try:
            trend_service = get_trend_service()

            # Use districts if provided, otherwise default top 5
            target_districts = districts or ["강남", "홍대", "성수", "이태원", "종로"]

            # Call Naver DataLab API
            trend_data = await trend_service.get_district_trend(
                base_keyword=keyword,
                districts=target_districts[:5],  # Max 5
                months=12,
            )

            # Build reply text
            reply_lines = [
                f"**{keyword} 검색 트렌드 분석** (최근 12개월)\n",
            ]

            if trend_data.get("summary"):
                top = trend_data["summary"].get("top_keyword")
                avg = trend_data["summary"].get("top_average", 0)
                reply_lines.append(f"가장 높은 검색량: **{top}** (평균 {avg:.1f})")

            reply_lines.append("\n지역별 검색량 추이를 차트로 확인하세요.")
            reply_lines.append(
                "높은 검색량은 높은 관심도를 의미하지만, 경쟁도 함께 높을 수 있습니다."
            )

            reply = "\n".join(reply_lines)

            # Suggested questions
            suggested = [
                f"{target_districts[0]}에서 {keyword} 추천해줘",
                f"{keyword} 경쟁 분석 보여줘",
                "다른 지역 트렌드도 비교해줘",
            ]

            return {
                "reply": reply,
                "recommendations": [],
                "charts": [],
                "trend": trend_data,
                "suggested_questions": suggested,
                "context": {
                    "trend_request": True,
                    "keyword": keyword,
                    "districts": target_districts,
                },
            }

        except Exception as e:
            logger.exception("Failed to fetch trend data")
            return {
                "reply": f"트렌드 데이터를 가져오는 중 오류가 발생했어요.\n\n{str(e)}\n\n다시 시도해주시거나, 다른 질문을 해주세요.",
                "recommendations": [],
                "charts": [],
                "suggested_questions": [
                    f"서울 강남에서 {self.display_name} 추천해줘",
                    "서울 홍대 상권 분석해줘",
                ],
                "context": {"trend_error": True},
            }

    def _build_system_prompt(self) -> str:
        """데이터 기반 시스템 프롬프트 생성 (업종별 config 템플릿 우선)"""
        summary = cast(
            Summary,
            cast(object, self.data_service.get_summary()),  # pyright: ignore[reportUnknownMemberType]
        )
        avg_survival_rate = float(summary["avg_survival_rate"])

        # If the industry config supplies a SYSTEM_PROMPT_TEMPLATE, use it.
        template = self.industry_config.get("SYSTEM_PROMPT_TEMPLATE")
        if isinstance(template, str) and template:
            try:
                return template.format(
                    total_districts=summary["total_districts"],
                    total_stores=summary["total_stores"],
                    avg_monthly_sales=f"{summary['avg_monthly_sales']:,.0f}",
                    avg_survival_rate=f"{avg_survival_rate * 100:.1f}",
                    display_name=self.display_name,
                )
            except (KeyError, IndexError, ValueError):
                logger.warning("SYSTEM_PROMPT_TEMPLATE formatting failed; using default prompt")

        # Fallback: hardcoded prompt with display_name substitution
        dn = self.display_name
        return f"""당신은 서울시 {dn} 창업 전문 AI 코치 "빌더"입니다. 컨셉은 **정직한 코치**입니다.

## 역할
- 예비 창업자에게 데이터 기반으로 **GO/CAUTION/NO_GO**를 단호하게 말합니다.
- 데이터가 나쁘면 반드시 **"추천하지 않습니다"**(NO_GO)라고 말하고, 대안을 제시합니다.
- 실제 서울시 상권 데이터를 기반으로 구체적인 조언만 합니다.

## 판정 엔진 우선 (가장 중요)
- 프롬프트에 `## 판정 결과`가 주어지면, 그 결과를 **최우선**으로 반영하세요.
- `verdict=NO_GO`면: 본문 첫 문장에 "추천하지 않습니다"를 명시하고, `alternatives`가 있으면 2~3개를 제시하세요.
- `verdict=CAUTION`이면: 가능하다고 말하되 **조건/리스크**를 먼저 걸고, 실행 체크리스트를 짧게 제시하세요.
- `verdict=GO`이면: 추천하되, 리스크 1~2개는 반드시 함께 언급하세요.

## 보유 데이터 (64개 필드, 6년 트렌드 분석)
- 서울시 {summary["total_districts"]}개 상권 분석 완료
- {dn} {summary["total_stores"]}개 점포 데이터
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

## 응답 스타일 — 짧고 강렬하게
당신은 데이터를 나열하는 도구가 아니라, 데이터를 **해석하고 맞춤형 결론을 내려주는 코파일럿**입니다.

**절대 규칙: 응답은 최대 5~8문장. 매출/투자비/BEP 숫자는 카드와 차트가 보여주므로 텍스트에서 반복하지 마세요.**

1. **한 줄 결론**: "이 상권은 ___에 적합합니다" (1문장)
2. **핵심 이유**: 왜 추천/비추인지 2~3문장
3. **리스크 + 대안**: 1~2문장
4. **차별화 한 줄**: "___로 승부하세요"

숫자 나열 금지. 해석만. 매출/투자비/원가/BEP는 이미 구조화된 카드로 사용자에게 보여지므로 텍스트에서 중복하지 마세요.

## 💰 시뮬레이션 기능 (매출·투자비·손익분기점)
"여기서 열면 얼마 벌어?", "초기 투자비는?", "몇 개월이면 본전?" 같은 질문에는 시뮬레이션 데이터를 활용해 답변합니다.

### 매출 시뮬레이션
- 점포당 예상 월매출 = 상권 전체 매출 ÷ 점포 수
- 낙관/비관 시나리오 = 같은 상권 유형 25%/75% 분위수
- 평균 객단가 = 월매출 ÷ 월 거래수

### 초기 투자비 (10평/약 33㎡ 기준, 상권유형별 차등)
{self._build_investment_prompt()}

### 운영비 (상권유형별 차등)
{self._build_operating_cost_prompt()}
- ⚠️ 업종 평균 추정치이며, 실제는 ±20% 차이 가능

### 손익분기점
- 월 순이익 = 월매출 - 운영비(임대료+원가+인건비+공과금+기타)
- 투자 회수 기간 = 초기 투자비 ÷ 월 순이익
- 일 손익분기 매출 = 월 운영비 ÷ 30

## 🧭 경쟁/차별화 · 원가/마진 · 주차 (카카오 로컬 + 벤치마크)
"이 동네 {dn} 몇 개야?", "프랜차이즈가 많아?", "뭘로 차별화해야 해?", "주차는 편해?", "메뉴 원가/마진은?" 같은 질문에는 아래 데이터를 활용합니다.

### 경쟁 분석 (카카오 로컬)
- 주변 {dn} 검색(최대 45개 샘플) 기반으로 유형 분포(프랜차이즈/디저트/브런치/로스터리/테이크아웃 등) 추정
- 시장 공백(gap)과 차별화 전략(우선순위 포함) 제안

### 주차 (카카오 로컬 PK6)
- 추천 상권 좌표 기준 반경 500m 주차장 개수/거리 요약 (좌표가 없으면 생략)

### 메뉴 원가/마진 벤치마크
- 대표 메뉴별 재료비(원가)와 마진율 벤치마크 제공
- 일일 판매 시나리오(매출/원가/매출총이익)로 감각적인 규모 추정

## 시간대 질문 예시 응답
"오전에 손님이 많은 곳" → 오전(06-11) 매출 비중 높은 상권 추천
"직장인 점심 타겟" → 점심(11-14) 매출 비중 높은 상권 추천
"야간 영업" → 저녁(17-21), 심야(21-24) 매출 비중 높은 상권 추천

## 고객층 질문 예시 응답
"20대 타겟" → 20대 매출 비중 높은 상권 추천
"직장인 타겟" → 30-40대 매출 비중 높은 상권 추천
"여성 고객 위주" → 여성 매출 비중 높은 상권 추천

## ⛔ 절대 규칙 (가장 중요)
- **아래 "추천 상권 데이터" 섹션에 나온 상권명·매출·생존율·수치만 사용하세요.**
- 데이터에 없는 상권명을 절대 생성하지 마세요 (예: 여의도 국제금융로, 을지로 카페거리 등 지어내기 금지).
- 데이터에 없는 매출액·생존율·점포수를 절대 생성하지 마세요.
- 추천 상권 데이터가 제공되지 않았다면, "현재 조건에 맞는 상권 데이터를 찾지 못했습니다"라고 솔직하게 답변하세요.
- 일반적인 창업 팁이나 {dn} 운영 조언은 데이터 없이도 답변 가능하지만, **구체적 상권명·수치는 반드시 제공된 데이터에서만** 인용하세요.

## 주의사항
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

        def get_bucket_value(breakdown: dict[str, object], bucket: str, field: str) -> int | None:
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
                                get_nested_int(
                                    customer_breakdown, ["age", "60대+", "transactions"]
                                ),
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
                                get_nested_int(
                                    customer_breakdown, ["gender", "male", "transactions"]
                                ),
                            ),
                        },
                        {
                            "name": "여성",
                            "value": to_float(customer_data.get("female_ratio")),
                            "label": format_label(
                                get_nested_int(customer_breakdown, ["gender", "female", "sales"]),
                                get_nested_int(
                                    customer_breakdown, ["gender", "female", "transactions"]
                                ),
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
            questions.append(f"{district_name}의 피크 시간대 {peak_time}에 맞는 운영 전략은?")

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
        Uses KEYWORD_DETECTION from industry config when available.
        """
        text = (message or "").strip()
        if not text:
            return False

        # Prefer config-driven keyword list; fall back to defaults with display_name.
        config_keywords = self.industry_config.get("KEYWORD_DETECTION")
        if isinstance(config_keywords, list) and config_keywords:
            keywords: list[str] = [str(k) for k in config_keywords]
        else:
            dn = self.display_name
            keywords = [
                "경쟁",
                "차별",
                "프랜차이즈",
                f"주변 {dn}",
                f"{dn} 몇",
                f"{dn}가 몇",
                "원가",
                "마진",
                "메뉴",
                "주차",
                "주차장",
            ]
        return any(k in text for k in keywords)

    async def _build_local_insights_with_data(
        self,
        message: str,
        recommendations: list[StructuredRecommendation],
    ) -> tuple[str, dict[str, object] | None]:
        if not recommendations:
            return ("", None)
        if not getattr(self.kakao_service, "available", False):
            return ("", None)

        top = recommendations[0]
        district_name = (top.get("district_name") or "").strip()
        if not district_name:
            return ("", None)

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

        analysis: CompetitiveAnalysis | None = None
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
            menu_costs = self.competitive_service.get_menu_costs()
        except Exception:
            menu_costs = None

        lines: list[str] = []
        lines.append("## 경쟁/차별화·주차·원가 (카카오 로컬 + 벤치마크)")
        lines.append(f"- 기준 상권: {district_name}")

        if analysis:
            total = int(analysis.get("total_nearby_cafes", 0))
            lines.append(f"- 주변 {self.display_name}(샘플): {total}개")

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
                        f"- 주차(500m): {pc}개"
                        + (f" | 가장 가까운: {nearest_name}{nearest_dist}" if nearest_name else "")
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
                    f"- 메뉴 원가/마진: 평균 마진율 {avg_margin_rate * 100:.1f}% | {daily.get('unit_name', '일일')} 시나리오 매출 {daily_revenue:,}원 / 원가 {daily_cogs:,}원"
                )
            except Exception:
                pass

        comp_dict: dict[str, object] | None = None
        if analysis and isinstance(analysis, dict):
            comp_dict = dict(analysis)

        return ("\n".join(lines).strip(), comp_dict)

    def _build_investment_prompt(self) -> str:
        """Build dynamic investment cost section from industry config."""
        cfg = self.industry_config
        dtf_raw = cfg.get("DISTRICT_TYPE_FACTORS")
        dtf: dict[str, object] = dtf_raw if isinstance(dtf_raw, dict) else {}
        eq_raw = cfg.get("EQUIPMENT_COST")
        eq: dict[str, object] = eq_raw if isinstance(eq_raw, dict) else {}
        inv_raw = cfg.get("INITIAL_INVENTORY")
        inv: list[int] = (
            inv_raw if isinstance(inv_raw, list) and len(inv_raw) >= 2 else [3000000, 5000000]
        )
        pm_raw = cfg.get("PERMITS_AND_MISC")
        pm: list[int] = (
            pm_raw if isinstance(pm_raw, list) and len(pm_raw) >= 2 else [5000000, 10000000]
        )

        # Interior costs
        interiors = []
        for dt in ["전통시장", "골목상권", "발달상권", "관광특구"]:
            f_raw = dtf.get(dt, {})
            f = f_raw if isinstance(f_raw, dict) else {}
            ipp = f.get("interior_per_pyeong", 0)
            if isinstance(ipp, int) and ipp > 0:
                interiors.append(f"{dt} {ipp // 10000}")

        # Equipment total
        def _eq_min(v: object) -> int:
            if isinstance(v, list) and v and isinstance(v[0], int):
                return int(v[0])
            if isinstance(v, int):
                return v
            return 0

        def _eq_max(v: object) -> int:
            if isinstance(v, list):
                if len(v) > 1 and isinstance(v[1], int):
                    return int(v[1])
                if v and isinstance(v[0], int):
                    return int(v[0])
            if isinstance(v, int):
                return v
            return 0

        eq_min = sum(_eq_min(v) for v in eq.values())
        eq_max = sum(_eq_max(v) for v in eq.values())

        lines = []
        lines.append("- 보증금: 월세 × 8~15배 (전통시장 ×8, 골목 ×10, 발달·관광특구 ×15)")
        if interiors:
            lines.append(f"- 인테리어: 평당 {' < '.join(interiors)}만원")
        lines.append(f"- 장비/설비: {eq_min // 10000:,}~{eq_max // 10000:,}만원")
        lines.append(f"- 초기 재료비: {inv[0] // 10000:,}~{inv[1] // 10000:,}만원")
        lines.append(f"- 기타(허가/간판): {pm[0] // 10000:,}~{pm[1] // 10000:,}만원")
        return "\n".join(lines)

    def _build_operating_cost_prompt(self) -> str:
        """Build dynamic operating cost section from industry config."""
        cfg = self.industry_config
        cogs_raw = cfg.get("COGS_RATIO", 0.32)
        utilities_raw = cfg.get("UTILITIES_RATIO", 0.035)
        other_raw = cfg.get("OTHER_RATIO", 0.075)
        cogs = float(cogs_raw) if isinstance(cogs_raw, (int, float)) else 0.32
        utilities = float(utilities_raw) if isinstance(utilities_raw, (int, float)) else 0.035
        other = float(other_raw) if isinstance(other_raw, (int, float)) else 0.075

        lines = []
        lines.append(f"- 원가율: {cogs * 100:.0f}%")
        lines.append("- 인건비: 24~27% (전통시장 24% < 골목 25% < 관광특구 26% < 발달 27%)")
        lines.append(f"- 공과금: {utilities * 100:.1f}%")
        lines.append(f"- 기타 운영비: {other * 100:.1f}%")
        return "\n".join(lines)

    def _normalize_budget_value(self, value: int, unit: str) -> int:
        if "백만" in unit:
            return value * 1000000
        return value * 10000

    def _extract_context_from_text(self, text: str) -> ConversationContext:
        district: str | None = None

        # 1) Prefer matching the real district_name from the dataset.
        #    This avoids collapsing "강남역" -> "강남".
        #    If user mentions multiple, we pick the longest-first match.
        try:
            for name in self._district_name_index:
                if name and name in text:
                    district = name
                    break
        except Exception:
            district = None

        # 2) Fallback: broad tokens (구 단위 등)
        if district is None:
            district = next((d for d in self._broad_district_tokens if d in text), None)

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
        # Use config BUSINESS_TYPE_MAP when available; fall back to defaults.
        config_type_map = self.industry_config.get("BUSINESS_TYPE_MAP")
        if isinstance(config_type_map, dict) and config_type_map:
            business_type_map: dict[str, str] = {str(k): str(v) for k, v in config_type_map.items()}
        else:
            business_type_map = {
                "테이크아웃": "takeout",
                "브런치": "brunch",
                "디저트": "dessert",
                "베이커리": "bakery",
                "작업": "work",
                "스터디": "study",
                "로스터리": "roastery",
                "스페셜티": "specialty",
            }
        for key, value in business_type_map.items():
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
        if incoming.gender_target is not None and incoming.gender_target != base.gender_target:
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

    def _extract_context_from_history(self, history: list[HistoryMessage]) -> ConversationContext:
        context = ConversationContext()
        for message in history[-10:]:
            # Only trust user utterances for context extraction.
            # Assistant replies contain many district names (recommendations/examples) and will pollute context.
            if message.get("role") != "user":
                continue
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
                    r for r in filtered if r["time_analysis"]["peak_time"] == target_time
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

    async def _get_relevant_data(
        self,
        query: str,
        history: list[HistoryMessage] | None = None,
        seed_context: ConversationContext | None = None,
        merged_context: ConversationContext | None = None,
    ) -> tuple[
        str,
        list[StructuredRecommendation],
        list[ChartData],
        ContextMeta,
        Optional[dict[str, object]],
    ]:
        context_parts: list[str] = []
        structured_recommendations: list[StructuredRecommendation] = []
        charts: list[ChartData] = []
        timeline_data_for_response: Optional[dict[str, object]] = None

        merged_context = merged_context or self._compute_merged_context(
            query, history, seed_context
        )

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
            context_parts.append(
                "## ⚠️ 추천 상권 데이터 (이 데이터만 사용하세요 — 아래에 없는 상권명·수치를 절대 생성하지 마세요)"
            )
            for r in recs:
                ta = r["time_analysis"]
                da = r["day_analysis"]
                ca = r["customer_analysis"]
                comp = r["competition"]

                detail = self.data_service.get_district_detail(r["district_code"])
                sales_detail = ""
                monthly_sales_total: int | None = None
                monthly_transactions_total: int | None = None
                avg_ticket_total: int | None = None
                if detail:
                    monthly_sales = detail.get("sales", {}).get("monthly")
                    monthly_transactions = detail.get("sales", {}).get("transactions")
                    avg_ticket = detail.get("sales", {}).get("avg_ticket")
                    if isinstance(monthly_sales, int):
                        monthly_sales_total = monthly_sales
                        sales_detail += f"\n- 월 매출 총액: {monthly_sales:,}원"
                    if isinstance(monthly_transactions, int):
                        monthly_transactions_total = monthly_transactions
                        sales_detail += f"\n- 월 거래수: {monthly_transactions:,}건"
                    if isinstance(avg_ticket, int):
                        avg_ticket_total = avg_ticket
                        sales_detail += f"\n- 평균 객단가: {avg_ticket:,}원"

                structured_recommendations.append(
                    {
                        "rank": r["rank"],
                        "district_code": r["district_code"],
                        "district_name": r["district_name"],
                        "district_type": r["district_type"],
                        "success_probability": r["success_probability"],
                        "estimated_rent": r["estimated_monthly_rent"],
                        "peak_time": ta["peak_time"],
                        "main_age_group": ca["main_age_group"],
                        "risk_factors": r["risk_factors"],
                        "recommendations": r["recommendations"],
                        "address": r["address"],
                        # Backward compatible: per-store (new store perspective)
                        "monthly_sales": r["estimated_monthly_sales"],
                        "monthly_sales_total": monthly_sales_total,
                        "monthly_sales_per_store": r["estimated_monthly_sales"],
                        "monthly_transactions_total": monthly_transactions_total,
                        "avg_ticket": avg_ticket_total,
                        "store_count": int(comp.get("store_count", 0)),
                        "survival_rate": r["survival_rate_2y"],
                        "key_success_factors": r["key_success_factors"],
                        "coordinates": {
                            "lat": r.get("lat", 0),
                            "lng": r.get("lng", 0),
                        }
                        if r.get("lat", 0) > 0
                        else None,
                        "foot_traffic_total": r.get("foot_traffic_total", 0),
                        "worker_total": r.get("worker_total", 0),
                        "facility_subway": r.get("facility_subway", 0),
                        "change_indicator": r.get("change_indicator", ""),
                        "transit_percentile": r.get("transit_percentile", 0.5),
                        "positioning": r.get("positioning", ""),
                        "positioning_detail": r.get("positioning_detail", ""),
                        "purchasing_power": r.get("purchasing_power", 0),
                        "single_household_ratio": None,
                        "income_info": None,
                        "scorecard": None,
                    }
                )

                # Attach scorecard if available
                try:
                    from api.services.scorecard_service import get_scorecard_service

                    sc_svc = get_scorecard_service(self.industry_code)
                    if not sc_svc._districts:
                        sc_svc.set_districts(self.data_service.districts)
                    district_raw = self.data_service.get_district(r["district_code"])
                    if district_raw:
                        structured_recommendations[-1]["scorecard"] = sc_svc.score_district(
                            district_raw
                        )
                except Exception:
                    pass

                # Attach 1인가구 비율 (서울 전체)
                try:
                    from api.services.kosis_data_service import get_single_household_ratio

                    household = await get_single_household_ratio("서울특별시")
                    if household:
                        ratio = household.get("ratio")
                        if isinstance(ratio, (int, float)):
                            structured_recommendations[-1]["single_household_ratio"] = float(ratio)
                except Exception:
                    pass

                # Attach 소득소비 데이터 (상권별)
                try:
                    from api.services.income_data_service import get_district_income_info

                    income = await get_district_income_info(r["district_code"])
                    if income:
                        structured_recommendations[-1]["income_info"] = dict(income)
                except Exception:
                    pass

                sim = await self.simulation_service.simulate(r["district_code"])
                sim_text = ""
                if isinstance(sim, dict) and sim:
                    rev = sim.get("revenue")
                    sc_data = sim.get("startup_cost")
                    be = sim.get("break_even")
                    if not (
                        isinstance(rev, dict) and isinstance(sc_data, dict) and isinstance(be, dict)
                    ):
                        rev, sc_data, be = None, None, None
                else:
                    rev, sc_data, be = None, None, None

                if isinstance(rev, dict) and isinstance(sc_data, dict) and isinstance(be, dict):

                    def as_int(x: object) -> int:
                        return (
                            int(x)
                            if isinstance(x, int)
                            else (int(x) if isinstance(x, float) else 0)
                        )

                    def as_float(x: object) -> float:
                        return float(x) if isinstance(x, (int, float)) else 0.0

                    sim_text = f"""
 - 💰 매출 시뮬레이션 (점포당):
   - 예상 월매출: {as_int(rev.get("monthly_sales_per_store")):,}원 (비관 {as_int(rev.get("pessimistic")):,} ~ 낙관 {as_int(rev.get("optimistic")):,})
   - 일평균 매출: {as_int(rev.get("daily_sales")):,}원
   - 평균 객단가: {as_int(rev.get("avg_ticket")):,}원
   - 월 거래수: {as_int(rev.get("monthly_transactions_per_store")):,}건
 - 🏗️ 초기 투자비 (10평/중급 기준): {as_int(sc_data.get("total_min")) // 10000:,}만 ~ {as_int(sc_data.get("total_max")) // 10000:,}만원
   - 보증금: {as_int(sc_data.get("deposit")) // 10000:,}만원 | 인테리어: {as_int(sc_data.get("interior")) // 10000:,}만원 | 장비: {as_int(sc_data.get("equipment_min")) // 10000:,}~{as_int(sc_data.get("equipment_max")) // 10000:,}만원
 - 📉 손익분기점:
   - 월 순이익: {as_int(be.get("monthly_net_profit")):,}원 (영업이익률 {as_float(be.get("net_profit_margin")) * 100:.1f}%)
   - 투자 회수: {as_int(be.get("break_even_months_min"))}~{as_int(be.get("break_even_months_max"))}개월
   - 일 손익분기 매출: {as_int(be.get("daily_break_even_sales")):,}원"""

                timeline_result = self.timeline_service.calculate_timeline(
                    cafe_type=merged_context.cafe_type or "일반",
                    budget_range="3천만원 이하"
                    if (merged_context.budget_max or 0) < 30000000
                    else (
                        "1억 이상" if (merged_context.budget_max or 0) >= 100000000 else "3천~1억"
                    ),
                    area_pyeong=10,
                    is_franchise=False,
                    district_type=r["district_type"],
                )
                timeline_data = cast(dict[str, object], dict(timeline_result))
                if timeline_data_for_response is None:
                    timeline_data_for_response = timeline_data

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

                positioning_name = r.get("positioning", "")
                positioning_detail = r.get("positioning_detail", "")
                transit_pctile = r.get("transit_percentile", 0.5)
                transit_label = (
                    "우수" if transit_pctile > 0.8 else ("양호" if transit_pctile > 0.4 else "보통")
                )
                if positioning_name:
                    rec_text += f"\n- 💡 포지셔닝: {positioning_name} — {positioning_detail}"
                    rec_text += (
                        f"\n- 🚇 교통 접근성: {transit_label} (상위 {transit_pctile * 100:.0f}%)"
                    )

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
                    tips.append(f"{self.display_name} 유형: {merged_context.cafe_type}")

                context_parts.append(f"\n## 사용자 선호 분석\n- " + "\n- ".join(tips))

        if not context_parts:
            summary = cast(
                Summary,
                cast(object, self.data_service.get_summary()),  # pyright: ignore[reportUnknownMemberType]
            )
            context_parts.append(f"""## 서울시 {self.display_name} 상권 현황 (2019-2025 데이터)
- 분석 상권 수: {summary["total_districts"]}개
- 총 {self.display_name} 수: {summary["total_stores"]}개
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

        return (
            "\n".join(context_parts),
            structured_recommendations,
            charts,
            context_meta,
            timeline_data_for_response,
        )

    async def chat(
        self,
        message: str,
        history: list[HistoryMessage] | None = None,
        seed_context: ConversationContext | None = None,
    ) -> StructuredChatPayload:
        """대화형 응답 생성"""

        # Sanitize user input against prompt injection
        message = self._sanitize_user_input(message)

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
                    f"서울 강남에서 월세 300만원대 {self.display_name} 추천해줘",
                    "서울 홍대에서 20대 여성 타겟 상권 추천해줘",
                    "서울 성수 골목상권 추천해줘",
                    "서울에서 점심 피크 상권 알려줘",
                ],
                "context": {"unsupported_regions": out_of_scope},
            }

        # District comparison detection (A vs B 비교해줘)
        comparison_result = self._detect_comparison_request(message)
        if comparison_result:
            return await self._handle_comparison(comparison_result["districts"])

        # Trend analysis detection (트렌드, 검색량, 인기도)
        trend_result = self._detect_trend_request(message)
        if trend_result:
            keyword_obj = trend_result.get("keyword")
            keyword = keyword_obj if isinstance(keyword_obj, str) else self.display_name

            districts_obj = trend_result.get("districts")
            districts: list[str] | None = None
            if isinstance(districts_obj, list):
                only_str = [d for d in districts_obj if isinstance(d, str) and d]
                districts = only_str or None
            return await self._handle_trend_request(
                keyword=keyword,
                districts=districts,
                message=message,
            )

        merged_context = self._compute_merged_context(message, history, seed_context)
        missing_district = merged_context.district is None
        missing_budget = merged_context.budget_max is None

        needs_district_disambiguation = False
        broad_token = merged_context.district

        already_disambiguated = False
        if history:
            for h in history[-6:]:
                ctx = h.get("context") if isinstance(h, dict) else None
                if isinstance(ctx, dict):
                    intake = ctx.get("intake_needs", [])
                    if "district_detail" in intake:
                        already_disambiguated = True
                        break

        if (
            isinstance(broad_token, str)
            and broad_token in self._broad_district_token_set
            and broad_token in message
            and not already_disambiguated
        ):
            options = self._top_subdistricts(broad_token, limit=6)
            if len(options) >= 3:
                needs_district_disambiguation = True

        if missing_district or missing_budget or needs_district_disambiguation:
            known_parts: list[str] = []
            if merged_context.district:
                known_parts.append(f"지역: {merged_context.district}")
            if merged_context.budget_min is not None and merged_context.budget_max is not None:
                known_parts.append(
                    f"월세: {merged_context.budget_min // 10000:,}~{merged_context.budget_max // 10000:,}만원"
                )
            if merged_context.cafe_type:
                known_parts.append(f"{self.display_name} 유형: {merged_context.cafe_type}")

            reply_lines: list[str] = []
            reply_lines.append("추천을 정확하게 하려면 몇 가지만 확인할게요.")
            if known_parts:
                reply_lines.append(f"(현재 파악된 정보: {', '.join(known_parts)})")
            if needs_district_disambiguation and isinstance(broad_token, str):
                reply_lines.append(
                    f"1) '{broad_token}'은 범위가 넓어요. 아래 중 **어느 상권**을 말하는지 골라주세요."
                )
                options = self._top_subdistricts(broad_token, limit=4)
                for i, opt in enumerate(options, 1):
                    name = opt.get("district_name")
                    dtype = opt.get("district_type")
                    rent = self._estimate_monthly_rent_from_district(opt)
                    if isinstance(name, str) and name:
                        if isinstance(dtype, str) and dtype:
                            if isinstance(rent, int):
                                reply_lines.append(
                                    f"   {i}) {name} ({dtype}) · 예상 월세 {rent // 10000:,}만원대"
                                )
                            else:
                                reply_lines.append(f"   {i}) {name} ({dtype})")
                        else:
                            reply_lines.append(f"   {i}) {name}")

                # Budget still matters; ask if missing.
                if missing_budget:
                    reply_lines.append("2) 월세 예산은 어느 정도인가요? (예: 200~400만원)")
            else:
                if missing_district:
                    reply_lines.append("1) 희망 지역이 어디인가요? (예: 강남/홍대/성수/종로)")
                if missing_budget:
                    reply_lines.append("2) 월세 예산은 어느 정도인가요? (예: 200~400만원)")

            reply_lines.append(
                "선택) 타겟 고객(직장인/20대/여성)이나 컨셉(테이크아웃/디저트/브런치/작업)도 알려주면 더 정확해요."
            )

            suggested: list[str] = []
            if needs_district_disambiguation and isinstance(broad_token, str):
                base_bmin = merged_context.budget_min or 2000000
                base_bmax = merged_context.budget_max or 5000000
                top_opts = self._top_subdistricts(broad_token, limit=6)
                for opt in top_opts[:4]:
                    name = opt.get("district_name")
                    if isinstance(name, str) and name:
                        rent = self._estimate_monthly_rent_from_district(opt)
                        bmin = base_bmin
                        bmax = base_bmax
                        if isinstance(rent, int) and base_bmax and rent > base_bmax:
                            bmin = int(rent * 0.8)
                            bmax = int(rent * 1.2)
                        suggested.append(
                            f"서울 {name}에서 월세 {bmin // 10000:,}~{bmax // 10000:,}만원 {self.display_name} 추천해줘"
                        )
                suggested.append(
                    f"서울 {broad_token}에서 월세 {base_bmin // 10000:,}~{base_bmax // 10000:,}만원으로 가능한 상권만 추천해줘"
                )

            elif missing_district and missing_budget:
                suggested = [
                    f"서울 홍대에서 월세 300만원대 {self.display_name} 추천해줘",
                    f"서울 강남에서 월세 200~400만원 {self.display_name} 추천해줘",
                    f"서울 성수에서 월세 250만원대, 테이크아웃 위주 추천해줘",
                    f"서울 종로에서 월세 200~300만원, 직장인 점심 타겟 추천해줘",
                ]
            elif missing_district and not missing_budget:
                bmin = merged_context.budget_min or int(
                    (merged_context.budget_max or 3000000) * 0.7
                )
                bmax = merged_context.budget_max or int(
                    (merged_context.budget_min or 3000000) * 1.3
                )
                suggested = [
                    f"서울 홍대에서 월세 {bmin // 10000:,}~{bmax // 10000:,}만원 {self.display_name} 추천해줘",
                    f"서울 강남에서 월세 {bmin // 10000:,}~{bmax // 10000:,}만원 {self.display_name} 추천해줘",
                    f"서울 성수에서 월세 {bmin // 10000:,}~{bmax // 10000:,}만원 {self.display_name} 추천해줘",
                ]
            elif missing_budget and merged_context.district:
                district = merged_context.district
                suggested = [
                    f"서울 {district}에서 월세 200~300만원대 {self.display_name} 추천해줘",
                    f"서울 {district}에서 월세 300~400만원대 {self.display_name} 추천해줘",
                    f"서울 {district}에서 월세 400~600만원대, 발달상권 추천해줘",
                ]
            else:
                suggested = [
                    f"서울 강남에서 월세 300만원대 {self.display_name} 추천해줘",
                    "서울 홍대에서 20대 여성 타겟 상권 추천해줘",
                    "서울 성수 골목상권 추천해줘",
                ]

            intake_payload: StructuredChatPayload = {
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
                            "district_detail" if needs_district_disambiguation else "",
                        ]
                        if k
                    ],
                },
            }

            # Check for support program request even during intake
            try:
                support_pattern = re.compile(
                    r"지원사업|정부지원|정부 지원|창업 지원|보조금|지원금|창업지원|지원 사업"
                )
                if support_pattern.search(message):
                    from api.services.support_program_service import get_support_program_service

                    support_svc = get_support_program_service(self.industry_code)

                    district = merged_context.district if merged_context else None
                    target_age = None
                    if re.search(r"청년|39세|청년창업", message):
                        target_age = "청년"

                    programs = support_svc.get_matched_programs(
                        district=district,
                        budget_min=None,
                        budget_max=None,
                        target_age=target_age,
                    )

                    if programs:
                        intake_payload["support_programs"] = [dict(p) for p in programs]
                        program_count = len(programs)
                        intake_payload["reply"] += (
                            f"\n\n💡 현재 신청 가능한 창업 지원사업 **{program_count}개**를 찾았습니다!"
                        )
            except Exception:
                pass

            return intake_payload

        (
            context_text,
            recommendations,
            charts,
            context_meta,
            timeline_data_for_response,
        ) = await self._get_relevant_data(
            message,
            history,
            seed_context=seed_context,
            merged_context=merged_context,
        )

        if not recommendations and not missing_district and not missing_budget:
            budget_min_man = (merged_context.budget_min or 0) // 10000
            budget_max_man = (merged_context.budget_max or 0) // 10000
            district_label = merged_context.district or "해당 지역"

            no_result_lines = [
                f"**{district_label}** 주변에서 월세 **{budget_min_man:,}~{budget_max_man:,}만원** 범위에 맞는 {self.display_name} 상권을 찾지 못했습니다.",
                "",
                "조건을 조금 조정해보시겠어요?",
            ]
            suggested = []
            if budget_max_man > 0:
                wider = int(budget_max_man * 1.5)
                suggested.append(
                    f"서울 {district_label}에서 월세 {budget_min_man:,}~{wider:,}만원 {self.display_name} 추천해줘"
                )
            suggested.append(f"서울 {district_label} 골목상권 {self.display_name} 추천해줘")
            suggested.append(f"서울 전체에서 월세 저렴한 {self.display_name} 상권 추천해줘")

            return {
                "reply": "\n".join(no_result_lines),
                "recommendations": [],
                "charts": [],
                "suggested_questions": suggested,
                "context": context_meta,
            }

        # Best-effort local insights (Kakao): always run when recommendations exist.
        competitive_data: dict[str, object] | None = None
        try:
            local_insights, comp_raw = await self._build_local_insights_with_data(
                message, recommendations
            )
            if local_insights:
                context_text = f"{context_text}\n\n{local_insights}".strip()
            if comp_raw:
                competitive_data = comp_raw
        except Exception:
            pass

        # Best-effort simulation for top recommendation
        simulation_data: dict[str, object] | None = None
        if recommendations:
            try:
                top_rec = recommendations[0]
                sim = await self.simulation_service.simulate(top_rec["district_code"])
                if sim:
                    # Also attach menu costs
                    menu_costs_data = None
                    try:
                        menu_costs_data = self.competitive_service.get_menu_costs()
                    except Exception:
                        pass
                    simulation_data = dict(sim)
                    if menu_costs_data:
                        simulation_data["menu_costs"] = dict(menu_costs_data)
            except Exception:
                pass

        # Compute verdict for top recommendation (data-only verdict engine)
        verdict: dict[str, object] | None = None
        if recommendations:
            try:
                top_rec = recommendations[0]
                district_code = top_rec.get("district_code")
                if isinstance(district_code, str) and district_code:
                    district = self.data_service._district_by_code.get(district_code)
                    if district:
                        from api.services.verdict_service import compute_verdict

                        verdict = dict(
                            compute_verdict(
                                district=district,
                                industry_code=self.industry_code,
                                budget_max=merged_context.budget_max,
                                estimated_rent=int(top_rec.get("estimated_rent", 0) or 0),
                            )
                        )
            except Exception:
                logger.exception("Failed to compute verdict")
                verdict = None

        # Inject verdict into prompt context for honest coaching
        if isinstance(verdict, dict) and verdict.get("verdict"):
            try:
                reasons = verdict.get("reasons", [])
                reason_lines: list[str] = []
                if isinstance(reasons, list):
                    for r in reasons[:8]:
                        if not isinstance(r, dict):
                            continue
                        factor = r.get("factor")
                        level = r.get("level")
                        detail = r.get("detail")
                        data_value = r.get("data_value")
                        threshold = r.get("threshold")
                        if all(
                            isinstance(x, str)
                            for x in (factor, level, detail, data_value, threshold)
                        ):
                            reason_lines.append(
                                f"- ({level}) {factor}: {detail} (값: {data_value}, 기준: {threshold})"
                            )

                alt_lines: list[str] = []
                alts = verdict.get("alternatives", [])
                if isinstance(alts, list) and alts:
                    for a in alts[:3]:
                        if not isinstance(a, dict):
                            continue
                        n = a.get("district_name")
                        t = a.get("district_type")
                        s = a.get("survival_rate")
                        if (
                            isinstance(n, str)
                            and isinstance(t, str)
                            and isinstance(s, (int, float))
                        ):
                            alt_lines.append(f"- {n} ({t}) · 생존율 {float(s) * 100:.0f}%")

                verdict_block = "\n".join(
                    [
                        "## 판정 결과",
                        f"verdict: {verdict.get('verdict')}",
                        f"confidence: {verdict.get('confidence')}%",
                        f"summary: {verdict.get('summary')}",
                        "reasons:",
                        *(reason_lines or ["- (info) 판정 근거가 제공되지 않았습니다"]),
                        "alternatives:",
                        *(alt_lines or ["- (none)"]),
                        "",
                        "위 판정 결과를 반드시 반영하여 답변하세요.",
                        "- GO: 긍정적으로 추천하되 리스크도 언급",
                        "- CAUTION: 신중하게 접근하라고 조언",
                        "- NO_GO: 솔직하게 '추천하지 않습니다'라고 말하고, 대안을 제시",
                    ]
                ).strip()
                context_text = f"{context_text}\n\n{verdict_block}".strip()
            except Exception:
                pass

        # 프롬프트 구성
        full_prompt = f"""{self.system_prompt}

---

{context_text}

---

사용자: {message}

위 "추천 상권 데이터"에 나온 상권명과 수치만 사용하여 답변해주세요. 데이터에 없는 상권이나 수치를 절대 만들어내지 마세요."""

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

위 "추천 상권 데이터"에 나온 상권명과 수치만 사용하여 답변해주세요. 데이터에 없는 상권이나 수치를 절대 만들어내지 마세요."""

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

        payload: StructuredChatPayload = {
            "reply": reply_text,
            "recommendations": recommendations,
            "charts": charts,
            "suggested_questions": suggested_questions,
            "context": context_meta,
        }
        if verdict:
            payload["verdict"] = verdict
        if timeline_data_for_response:
            payload["timeline"] = timeline_data_for_response
        if competitive_data:
            payload["competitive"] = competitive_data
        if simulation_data:
            payload["simulation"] = simulation_data

        # Trademark conflict detection
        try:
            trademark_pattern = re.compile(r"상호명|상호|간판|이름.*등록|브랜드명|상표")
            if trademark_pattern.search(message):
                # Extract the proposed name — look for quoted text or "상호명 X" pattern
                name_match = re.search(
                    r"['\"](.+?)['\"]|상호명?\s*[은는이가]?\s*(\S+)|간판\s*[은는이가]?\s*(\S+)|브랜드명?\s*[은는이가]?\s*(\S+)",
                    message,
                )
                proposed_name = None
                if name_match:
                    proposed_name = next((g for g in name_match.groups() if g), None)
                if proposed_name:
                    from api.services.trademark_service import get_trademark_service

                    tm_svc = get_trademark_service(self.industry_code)
                    trademark_result = tm_svc.check(proposed_name)
                    payload["trademark"] = trademark_result
        except Exception:
            pass

        # Support program matching detection
        try:
            support_pattern = re.compile(
                r"지원사업|정부지원|정부 지원|창업 지원|보조금|지원금|창업지원|지원 사업"
            )
            if support_pattern.search(message):
                from api.services.support_program_service import get_support_program_service

                support_svc = get_support_program_service(self.industry_code)

                # Extract context for matching
                district = merged_context.district if merged_context else None
                budget_min = merged_context.budget_min if merged_context else None
                budget_max = merged_context.budget_max if merged_context else None

                # Detect age target from message
                target_age = None
                if re.search(r"청년|39세|청년창업", message):
                    target_age = "청년"

                # Get matched programs
                programs = support_svc.get_matched_programs(
                    district=district,
                    budget_min=budget_min,
                    budget_max=budget_max,
                    target_age=target_age,
                )

                if programs:
                    payload["support_programs"] = [dict(p) for p in programs]

                    # Add to reply if not already mentioned
                    current_reply = payload.get("reply", "")
                    if isinstance(current_reply, str) and not any(
                        kw in current_reply for kw in ["지원사업", "정부지원"]
                    ):
                        program_count = len(programs)
                        payload["reply"] = (
                            current_reply
                            + f"\n\n💡 현재 신청 가능한 창업 지원사업 **{program_count}개**를 찾았습니다!"
                        )
        except Exception:
            pass

        return payload

    def chat_sync(
        self, message: str, history: list[HistoryMessage] | None = None
    ) -> StructuredChatPayload:
        """동기 버전 (테스트용)"""
        import asyncio

        return asyncio.run(self.chat(message, history))


# Registry: one ChatService per industry_code
_registry: dict[str, ChatService] = {}


def get_chat_service(industry_code: str = "CS100010") -> ChatService:
    """Get or create a ChatService for the given industry code."""
    if industry_code not in _registry:
        _registry[industry_code] = ChatService(industry_code)
    return _registry[industry_code]
