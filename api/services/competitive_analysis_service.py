"""
경쟁 차별점 분석 + 메뉴별 원가계산 서비스

Multi-industry support: constants are loaded from config JSON files
(data/industries/<code>.json) with fallback to module-level defaults
for backward compatibility with CS100010 (카페).
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, TypedDict

from api.services.kakao_local_service import (
    KakaoLocalService,
    NearbyStore,
    NearbyStoresResult,
    get_kakao_local_service,
)
from config.industry_config import DEFAULT_INDUSTRY, load_industry_config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 메뉴별 원가 벤치마크 (2024-2025 업계 평균) — CS100010 카페 기본값
# ---------------------------------------------------------------------------

MENU_COSTS: dict[str, dict[str, Any]] = {
    "아메리카노": {
        "selling_price": 4500,
        "ingredients": {
            "원두": {"amount": "15g", "cost": 450},
            "물": {"amount": "240ml", "cost": 5},
            "종이컵+뚜껑+슬리브": {"amount": "1set", "cost": 180},
        },
        "total_cost": 635,
        "margin_rate": 0.859,
        "category": "커피",
    },
    "카페라떼": {
        "selling_price": 5000,
        "ingredients": {
            "원두": {"amount": "15g", "cost": 450},
            "우유": {"amount": "200ml", "cost": 400},
            "종이컵+뚜껑": {"amount": "1set", "cost": 180},
        },
        "total_cost": 1030,
        "margin_rate": 0.794,
        "category": "커피",
    },
    "바닐라라떼": {
        "selling_price": 5500,
        "ingredients": {
            "원두": {"amount": "15g", "cost": 450},
            "우유": {"amount": "200ml", "cost": 400},
            "바닐라시럽": {"amount": "20ml", "cost": 150},
            "종이컵+뚜껑": {"amount": "1set", "cost": 180},
        },
        "total_cost": 1180,
        "margin_rate": 0.785,
        "category": "커피",
    },
    "카페모카": {
        "selling_price": 5500,
        "ingredients": {
            "원두": {"amount": "15g", "cost": 450},
            "우유": {"amount": "200ml", "cost": 400},
            "초코시럽": {"amount": "20ml", "cost": 200},
            "휘핑크림": {"amount": "30g", "cost": 150},
            "종이컵+뚜껑": {"amount": "1set", "cost": 180},
        },
        "total_cost": 1380,
        "margin_rate": 0.749,
        "category": "커피",
    },
    "콜드브루": {
        "selling_price": 5000,
        "ingredients": {
            "콜드브루원액": {"amount": "100ml", "cost": 600},
            "물/얼음": {"amount": "300ml", "cost": 30},
            "플라스틱컵+뚜껑": {"amount": "1set", "cost": 200},
        },
        "total_cost": 830,
        "margin_rate": 0.834,
        "category": "커피",
    },
    "녹차라떼": {
        "selling_price": 5500,
        "ingredients": {
            "말차파우더": {"amount": "10g", "cost": 500},
            "우유": {"amount": "250ml", "cost": 500},
            "종이컵+뚜껑": {"amount": "1set", "cost": 180},
        },
        "total_cost": 1180,
        "margin_rate": 0.785,
        "category": "논커피",
    },
    "딸기스무디": {
        "selling_price": 6000,
        "ingredients": {
            "냉동딸기": {"amount": "100g", "cost": 800},
            "우유": {"amount": "150ml", "cost": 300},
            "요거트": {"amount": "50g", "cost": 200},
            "얼음": {"amount": "200g", "cost": 20},
            "플라스틱컵+뚜껑": {"amount": "1set", "cost": 200},
        },
        "total_cost": 1520,
        "margin_rate": 0.747,
        "category": "논커피",
    },
    "크로와상": {
        "selling_price": 4000,
        "ingredients": {
            "냉동크로와상": {"amount": "1ea", "cost": 1200},
            "포장지": {"amount": "1set", "cost": 50},
        },
        "total_cost": 1250,
        "margin_rate": 0.688,
        "category": "디저트",
    },
    "티라미수": {
        "selling_price": 7000,
        "ingredients": {
            "마스카포네": {"amount": "80g", "cost": 1600},
            "에스프레소": {"amount": "30ml", "cost": 150},
            "레이디핑거": {"amount": "3ea", "cost": 300},
            "코코아파우더": {"amount": "5g", "cost": 50},
            "용기": {"amount": "1ea", "cost": 300},
        },
        "total_cost": 2400,
        "margin_rate": 0.657,
        "category": "디저트",
    },
    "아이스티": {
        "selling_price": 4500,
        "ingredients": {
            "티백/찻잎": {"amount": "5g", "cost": 200},
            "설탕시럽": {"amount": "15ml", "cost": 30},
            "얼음+물": {"amount": "400ml", "cost": 30},
            "플라스틱컵+뚜껑": {"amount": "1set", "cost": 200},
        },
        "total_cost": 460,
        "margin_rate": 0.898,
        "category": "논커피",
    },
}

RAW_MATERIAL_PRICES: dict[str, dict[str, Any]] = {
    "원두 (kg)": {"price": 30000, "unit": "kg", "note": "스페셜티 기준, 상업용 15,000~20,000"},
    "우유 (L)": {"price": 2000, "unit": "L", "note": "서울우유 기준"},
    "종이컵 (개)": {"price": 100, "unit": "개", "note": "12oz 기준, 뚜껑 별도 50원"},
    "플라스틱컵 (개)": {"price": 120, "unit": "개", "note": "16oz ICE용"},
    "바닐라시럽 (750ml)": {"price": 8500, "unit": "병", "note": "모닌 기준 ~40잔 분량"},
    "초코시럽 (750ml)": {"price": 9000, "unit": "병", "note": "~37잔 분량"},
    "휘핑크림 (L)": {"price": 5000, "unit": "L", "note": "~33잔 분량"},
    "냉동딸기 (kg)": {"price": 8000, "unit": "kg", "note": "~10잔 분량"},
    "말차파우더 (100g)": {"price": 5000, "unit": "100g", "note": "~10잔 분량"},
}


# ---------------------------------------------------------------------------
# 카페 유형 분류 키워드 — CS100010 기본값
# ---------------------------------------------------------------------------

CAFE_TYPE_KEYWORDS: dict[str, list[str]] = {
    "프랜차이즈": [
        "스타벅스", "투썸", "이디야", "메가", "컴포즈", "빽다방", "할리스",
        "폴바셋", "파스쿠찌", "엔제리너스", "커피빈", "탐앤탐스", "더벤티",
        "매머드", "감성커피", "커피에반하다", "요거프레소",
    ],
    "디저트카페": ["디저트", "케이크", "베이커리", "빵", "마카롱", "와플"],
    "브런치카페": ["브런치", "샌드위치", "베이글", "토스트"],
    "테마카페": ["테마", "보드게임", "방탈출", "북카페", "스터디", "고양이", "강아지"],
    "로스터리/스페셜티": ["로스터리", "로스팅", "스페셜티", "핸드드립", "싱글오리진"],
    "테이크아웃": ["테이크아웃", "저가"],
}


# ---------------------------------------------------------------------------
# 타입 정의
# ---------------------------------------------------------------------------

class CafeTypeBreakdown(TypedDict):
    type: str
    count: int
    ratio: float
    examples: list[str]


class MarketGap(TypedDict):
    gap_type: str
    description: str
    opportunity_score: float


class DifferentiationStrategy(TypedDict):
    strategy: str
    reason: str
    priority: str


class CompetitiveAnalysis(TypedDict):
    total_nearby_cafes: int
    cafe_types: list[CafeTypeBreakdown]
    market_gaps: list[MarketGap]
    strategies: list[DifferentiationStrategy]
    top_competitors: list[dict[str, str]]


class MenuCostItem(TypedDict):
    menu: str
    selling_price: int
    cost: int
    margin: int
    margin_rate: float
    category: str
    ingredients: dict[str, dict[str, Any]]


class CostSimulation(TypedDict):
    menu_costs: list[MenuCostItem]
    avg_margin_rate: float
    raw_material_prices: dict[str, dict[str, Any]]
    daily_sales_scenario: dict[str, Any]


# ---------------------------------------------------------------------------
# 서비스
# ---------------------------------------------------------------------------

class CompetitiveAnalysisService:
    """Competitive analysis + menu cost service.

    Loads industry-specific constants from config JSON with fallback to
    module-level defaults (CS100010 / 카페).
    """

    def __init__(self, industry_code: str = DEFAULT_INDUSTRY) -> None:
        self.industry_code = industry_code
        self.kakao = get_kakao_local_service()

        # -- Load config with fallback to module-level defaults ------------
        try:
            cfg = load_industry_config(industry_code)
        except Exception:
            logger.warning(
                "Failed to load industry config for %s; using module defaults",
                industry_code,
            )
            cfg = {}

        self._display_name: str = cfg.get("display_name", "카페")

        # MENU_COSTS
        try:
            self._menu_costs: dict[str, dict[str, Any]] = cfg["MENU_COSTS"]
        except KeyError:
            self._menu_costs = MENU_COSTS

        # STORE_TYPE_KEYWORDS (config key is CAFE_TYPE_KEYWORDS for backward compat)
        try:
            self._store_type_keywords: dict[str, list[str]] = cfg["CAFE_TYPE_KEYWORDS"]
        except KeyError:
            self._store_type_keywords = CAFE_TYPE_KEYWORDS

        # RAW_MATERIAL_PRICES
        try:
            self._raw_material_prices: dict[str, dict[str, Any]] = cfg["RAW_MATERIAL_PRICES"]
        except KeyError:
            self._raw_material_prices = RAW_MATERIAL_PRICES

        # DAILY_SCENARIO (industry-specific daily order scenario)
        ds = cfg.get("DAILY_SCENARIO", {})
        self._daily_orders: int = ds.get("daily_orders", 100)
        self._main_ratio: float = ds.get("main_ratio", 0.70)
        self._main_category: str = ds.get("main_category", "커피")
        self._unit: str = ds.get("unit", "잔")
        self._unit_name: str = ds.get("unit_name", "일 100잔")

    # -------------------------------------------------------------------
    # Store classification (renamed from _classify_cafe)
    # -------------------------------------------------------------------

    def _classify_store(self, name: str, category: str) -> str:
        """Classify a store by matching name/category against keyword sets."""
        text = f"{name} {category}".lower()
        for store_type, keywords in self._store_type_keywords.items():
            for kw in keywords:
                if kw.lower() in text:
                    return store_type
        if "카페" in category or "커피" in category:
            return "일반카페"
        return f"일반{self._display_name}"

    async def analyze_competition(self, query: str, x: float | None = None, y: float | None = None) -> CompetitiveAnalysis:
        if not self.kakao.available:
            return CompetitiveAnalysis(
                total_nearby_cafes=0,
                cafe_types=[],
                market_gaps=[],
                strategies=[],
                top_competitors=[],
            )

        all_stores: list[NearbyStore] = []
        for page in range(1, 4):
            result = await self.kakao.search_nearby_cafes(query=query, x=x, y=y, size=15, page=page)
            all_stores.extend(result["stores"])
            if len(result["stores"]) < 15:
                break

        type_counter: Counter[str] = Counter()
        type_examples: dict[str, list[str]] = {}
        for store in all_stores:
            store_type = self._classify_store(store["name"], store["category"])
            type_counter[store_type] += 1
            type_examples.setdefault(store_type, [])
            if len(type_examples[store_type]) < 3:
                type_examples[store_type].append(store["name"])

        total = max(1, len(all_stores))
        cafe_types: list[CafeTypeBreakdown] = []
        for ct, count in type_counter.most_common():
            cafe_types.append(CafeTypeBreakdown(
                type=ct,
                count=count,
                ratio=round(count / total * 100, 1),
                examples=type_examples.get(ct, []),
            ))

        gaps = self._find_market_gaps(type_counter, total)
        strategies = self._generate_strategies(type_counter, total, cafe_types)

        top_competitors = []
        for store in all_stores[:5]:
            top_competitors.append({
                "name": store["name"],
                "category": store["category"],
                "address": store["road_address"] or store["address"],
                "place_url": store["place_url"],
            })

        return CompetitiveAnalysis(
            total_nearby_cafes=total,
            cafe_types=cafe_types,
            market_gaps=gaps,
            strategies=strategies,
            top_competitors=top_competitors,
        )

    def _find_market_gaps(self, type_counter: Counter[str], total: int) -> list[MarketGap]:
        gaps: list[MarketGap] = []
        franchise_ratio = type_counter.get("프랜차이즈", 0) / total

        if type_counter.get("디저트카페", 0) / total < 0.1:
            gaps.append(MarketGap(
                gap_type="디저트카페",
                description="디저트·케이크 특화 카페가 부족한 상권입니다",
                opportunity_score=0.85 if franchise_ratio > 0.3 else 0.65,
            ))

        if type_counter.get("브런치카페", 0) / total < 0.05:
            gaps.append(MarketGap(
                gap_type="브런치카페",
                description="브런치·베이글 카페가 거의 없는 상권입니다",
                opportunity_score=0.80,
            ))

        if type_counter.get("로스터리/스페셜티", 0) / total < 0.05:
            gaps.append(MarketGap(
                gap_type="로스터리/스페셜티",
                description="스페셜티 커피·자가 로스팅 카페가 부족합니다",
                opportunity_score=0.75,
            ))

        if type_counter.get("테마카페", 0) / total < 0.05:
            gaps.append(MarketGap(
                gap_type="테마카페",
                description="북카페·보드게임 등 체험형 카페가 없습니다",
                opportunity_score=0.60,
            ))

        if franchise_ratio > 0.5:
            gaps.append(MarketGap(
                gap_type="개인카페",
                description=f"프랜차이즈가 {franchise_ratio * 100:.0f}%를 차지해 개성 있는 개인카페에 수요가 있습니다",
                opportunity_score=0.70,
            ))

        gaps.sort(key=lambda g: g["opportunity_score"], reverse=True)
        return gaps[:5]

    def _generate_strategies(
        self, type_counter: Counter[str], total: int, cafe_types: list[CafeTypeBreakdown]
    ) -> list[DifferentiationStrategy]:
        strategies: list[DifferentiationStrategy] = []
        franchise_ratio = type_counter.get("프랜차이즈", 0) / total

        if franchise_ratio > 0.4:
            strategies.append(DifferentiationStrategy(
                strategy="감성 인테리어 + SNS 마케팅",
                reason=f"프랜차이즈 비율 {franchise_ratio * 100:.0f}% — 획일적 공간 대비 포토존·감성 인테리어로 차별화",
                priority="높음",
            ))

        if type_counter.get("디저트카페", 0) < 3:
            strategies.append(DifferentiationStrategy(
                strategy="시그니처 디저트 + 커피 페어링",
                reason="디저트 특화 카페 부족 — 객단가 상승(+2,000~5,000원)과 재방문율 증가 기대",
                priority="높음",
            ))

        if type_counter.get("테이크아웃", 0) / total < 0.15:
            strategies.append(DifferentiationStrategy(
                strategy="테이크아웃 전문 + 저가 전략",
                reason="저가 테이크아웃 카페 부족 — 직장인 출퇴근 시간대 빠른 회전율 공략",
                priority="중간",
            ))

        if type_counter.get("로스터리/스페셜티", 0) < 2:
            strategies.append(DifferentiationStrategy(
                strategy="자가 로스팅 + 원두 구독 서비스",
                reason="스페셜티 커피 공백 — 프리미엄 고객층 확보 + 원두 판매로 추가 수익",
                priority="중간",
            ))

        strategies.append(DifferentiationStrategy(
            strategy="배달/픽업 전용 메뉴 운영",
            reason="배달 수요 공략 — 배달 전용 세트(커피+디저트) 구성으로 배달앱 노출 극대화",
            priority="중간",
        ))

        return strategies[:5]

    # -----------------------------------------------------------------------
    # 원가계산
    # -----------------------------------------------------------------------

    def get_menu_costs(self) -> CostSimulation:
        """Build cost simulation using instance menu costs (config-driven)."""
        items: list[MenuCostItem] = []
        for menu, data in self._menu_costs.items():
            selling = data["selling_price"]
            cost = data["total_cost"]
            items.append(MenuCostItem(
                menu=menu,
                selling_price=selling,
                cost=cost,
                margin=selling - cost,
                margin_rate=round((selling - cost) / selling, 3),
                category=data["category"],
                ingredients=data["ingredients"],
            ))

        avg_margin = sum(i["margin_rate"] for i in items) / max(1, len(items))

        daily_scenario = self._build_daily_scenario(items)

        return CostSimulation(
            menu_costs=items,
            avg_margin_rate=round(avg_margin, 3),
            raw_material_prices=self._raw_material_prices,
            daily_sales_scenario=daily_scenario,
        )

    def _build_daily_scenario(self, items: list[MenuCostItem]) -> dict[str, Any]:
        """Build daily sales scenario using industry-specific config."""
        main_items = [i for i in items if i["category"] == self._main_category]
        sub_items = [i for i in items if i["category"] != self._main_category]

        daily_orders = self._daily_orders
        main_ratio = self._main_ratio
        main_orders = int(daily_orders * main_ratio)
        sub_orders = daily_orders - main_orders

        avg_main_price = sum(i["selling_price"] for i in main_items) // max(1, len(main_items)) if main_items else 8000
        avg_main_cost = sum(i["cost"] for i in main_items) // max(1, len(main_items)) if main_items else 3000
        avg_sub_price = sum(i["selling_price"] for i in sub_items) // max(1, len(sub_items)) if sub_items else 5000
        avg_sub_cost = sum(i["cost"] for i in sub_items) // max(1, len(sub_items)) if sub_items else 1500

        daily_revenue = (main_orders * avg_main_price) + (sub_orders * avg_sub_price)
        daily_cogs = (main_orders * avg_main_cost) + (sub_orders * avg_sub_cost)

        return {
            "daily_orders": daily_orders,
            "main_orders": main_orders,
            "sub_orders": sub_orders,
            "unit": self._unit,
            "unit_name": self._unit_name,
            "daily_revenue": daily_revenue,
            "daily_cogs": daily_cogs,
            "daily_gross_profit": daily_revenue - daily_cogs,
            "gross_margin_rate": round((daily_revenue - daily_cogs) / max(1, daily_revenue), 3),
            "monthly_revenue": daily_revenue * 30,
            "monthly_cogs": daily_cogs * 30,
            "monthly_gross_profit": (daily_revenue - daily_cogs) * 30,
        }

    @staticmethod
    def calculate_custom_menu_cost(
        selling_price: int,
        ingredients: dict[str, int],
    ) -> MenuCostItem:
        total_cost = sum(ingredients.values())
        return MenuCostItem(
            menu="커스텀 메뉴",
            selling_price=selling_price,
            cost=total_cost,
            margin=selling_price - total_cost,
            margin_rate=round((selling_price - total_cost) / max(1, selling_price), 3),
            category="커스텀",
            ingredients={k: {"cost": v} for k, v in ingredients.items()},
        )


# ---------------------------------------------------------------------------
# Registry pattern — one instance per industry_code
# ---------------------------------------------------------------------------

_registry: dict[str, CompetitiveAnalysisService] = {}


def get_competitive_analysis_service(
    industry_code: str = DEFAULT_INDUSTRY,
) -> CompetitiveAnalysisService:
    """Return a cached CompetitiveAnalysisService for the given industry."""
    if industry_code not in _registry:
        _registry[industry_code] = CompetitiveAnalysisService(industry_code)
    return _registry[industry_code]
