"""
매출 시뮬레이션 · 초기 투자비용 · 손익분기점 분석 서비스

모든 금액 단위: 원(KRW)
"""

from __future__ import annotations

import logging
import math
from typing import Any, Optional, TypedDict

from api.services.data_service import DataService, estimate_rent, get_data_service
from config.industry_config import load_industry_config, DEFAULT_INDUSTRY

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 업계 벤치마크 상수 (기본값 — config 미로드 시 폴백)
# ---------------------------------------------------------------------------

DISTRICT_TYPE_FACTORS = {
    "골목상권": {"interior_per_pyeong": 1_800_000, "labor_ratio": 0.25, "deposit_mult": 10},
    "발달상권": {"interior_per_pyeong": 2_500_000, "labor_ratio": 0.27, "deposit_mult": 15},
    "전통시장": {"interior_per_pyeong": 1_500_000, "labor_ratio": 0.24, "deposit_mult": 8},
    "관광특구": {"interior_per_pyeong": 2_800_000, "labor_ratio": 0.26, "deposit_mult": 15},
}

EQUIPMENT_COST = {
    "espresso_machine": (8_000_000, 15_000_000),
    "grinder": (2_000_000, 5_000_000),
    "refrigeration": (5_000_000, 8_000_000),
    "furniture": (10_000_000, 15_000_000),
    "pos": (2_000_000, 3_000_000),
}

INITIAL_INVENTORY = (3_000_000, 5_000_000)
PERMITS_AND_MISC = (5_000_000, 10_000_000)

COGS_RATIO = 0.32
UTILITIES_RATIO = 0.035
OTHER_RATIO = 0.075

OPERATING_MARGIN_RANGE = (0.08, 0.15)


def estimate_seats(pyeong: int) -> tuple[int, int]:
    return (int(pyeong * 0.8), int(pyeong * 1.2))


# ---------------------------------------------------------------------------
# 타입 정의
# ---------------------------------------------------------------------------

class RevenueEstimate(TypedDict):
    monthly_sales_per_store: int
    monthly_transactions_per_store: int
    avg_ticket: int
    pessimistic: int
    optimistic: int
    daily_sales: int
    peak_time_sales: int
    peak_time: str
    peak_day_sales: int
    peak_day: str


class StartupCost(TypedDict):
    deposit: int
    interior: int
    equipment_min: int
    equipment_max: int
    initial_inventory_min: int
    initial_inventory_max: int
    permits_misc_min: int
    permits_misc_max: int
    total_min: int
    total_max: int
    interior_grade: str
    area_pyeong: int


class OperatingCost(TypedDict):
    rent: int
    cogs: int
    labor: int
    utilities: int
    other: int
    total: int


class BreakEvenResult(TypedDict):
    monthly_revenue: int
    monthly_operating_cost: int
    monthly_net_profit: int
    net_profit_margin: float
    initial_investment_min: int
    initial_investment_max: int
    break_even_months_min: int
    break_even_months_max: int
    daily_break_even_sales: int


class SimulationAssumptions(TypedDict):
    area_pyeong: int
    area_sqm: int
    seats_min: int
    seats_max: int
    summary: str
    disclaimer: str


class SimulationResult(TypedDict, total=False):
    district_name: str
    district_type: str
    district_code: str
    revenue: RevenueEstimate
    startup_cost: StartupCost
    operating_cost: OperatingCost
    break_even: BreakEvenResult
    assumptions: SimulationAssumptions
    competition: dict[str, Any]
    risk_summary: list[str]
    franchise_benchmark: dict[str, Any]
    cost_data_source: str


# ---------------------------------------------------------------------------
# 서비스
# ---------------------------------------------------------------------------

class SimulationService:
    def __init__(
        self,
        data_service: DataService | None = None,
        industry_code: str = DEFAULT_INDUSTRY,
    ) -> None:
        self.industry_code = industry_code
        self.data_service = data_service or get_data_service(industry_code)

        # Load industry config and extract simulation constants
        self._load_config()

        self._build_percentile_cache()

        # KOSIS 보강 상태
        self._kosis_enriched: bool = False
        self._cost_data_source: str = "업종 평균 추정치"

    # -------------------------------------------------------------------
    # Config loading with fallback to module-level defaults
    # -------------------------------------------------------------------

    def _load_config(self) -> None:
        try:
            cfg = load_industry_config(self.industry_code)
        except FileNotFoundError:
            cfg = {}

        self.display_name: str = cfg.get("display_name", cfg.get("name", "카페"))

        # DISTRICT_TYPE_FACTORS
        try:
            raw_dtf = cfg["DISTRICT_TYPE_FACTORS"]
            # Ensure each sub-dict has required keys; keep as-is (values are plain dicts)
            self._district_type_factors: dict[str, dict[str, Any]] = raw_dtf
        except (KeyError, TypeError):
            self._district_type_factors = DISTRICT_TYPE_FACTORS

        # EQUIPMENT_COST — config stores [min, max] lists; convert to tuples
        try:
            raw_eq = cfg["EQUIPMENT_COST"]
            self._equipment_cost: dict[str, tuple[int, int]] = {
                k: (v[0], v[1]) for k, v in raw_eq.items()
            }
        except (KeyError, TypeError):
            self._equipment_cost = EQUIPMENT_COST

        # Scalar ratios
        try:
            self._cogs_ratio: float = float(cfg["COGS_RATIO"])
        except (KeyError, TypeError, ValueError):
            self._cogs_ratio = COGS_RATIO

        try:
            self._utilities_ratio: float = float(cfg["UTILITIES_RATIO"])
        except (KeyError, TypeError, ValueError):
            self._utilities_ratio = UTILITIES_RATIO

        try:
            self._other_ratio: float = float(cfg["OTHER_RATIO"])
        except (KeyError, TypeError, ValueError):
            self._other_ratio = OTHER_RATIO

        # INITIAL_INVENTORY — config stores [min, max] list
        try:
            raw_inv = cfg["INITIAL_INVENTORY"]
            self._initial_inventory: tuple[int, int] = (raw_inv[0], raw_inv[1])
        except (KeyError, TypeError, IndexError):
            self._initial_inventory = INITIAL_INVENTORY

        # PERMITS_AND_MISC — config stores [min, max] list
        try:
            raw_pm = cfg["PERMITS_AND_MISC"]
            self._permits_and_misc: tuple[int, int] = (raw_pm[0], raw_pm[1])
        except (KeyError, TypeError, IndexError):
            self._permits_and_misc = PERMITS_AND_MISC

    def _build_percentile_cache(self) -> None:
        type_sales: dict[str, list[int]] = {}
        for d in self.data_service.districts:
            sc = max(1, d.get("store_count", 1))
            sps = int(d["monthly_sales"] / sc)
            dt = d["district_type"]
            type_sales.setdefault(dt, []).append(sps)

        self._percentiles: dict[str, tuple[int, int, int]] = {}
        for dt, values in type_sales.items():
            values.sort()
            n = len(values)
            p25 = values[max(0, int(n * 0.25))]
            p50 = values[max(0, int(n * 0.50))]
            p75 = values[max(0, int(n * 0.75))]
            self._percentiles[dt] = (p25, p50, p75)

    # -----------------------------------------------------------------------
    # KOSIS 데이터로 원가율 보강 (최초 1회만 실행)
    # -----------------------------------------------------------------------

    async def _enrich_with_kosis(self) -> None:
        """KOSIS 외식업체경영실태조사 데이터로 원가율을 실측치로 대체."""
        if self._kosis_enriched:
            return

        self._kosis_enriched = True  # 실패해도 재시도 방지

        try:
            from api.services.kosis_data_service import get_cost_structure

            cost = await get_cost_structure(self.industry_code)
            if cost is None:
                logger.info("KOSIS 데이터 없음 — config 기본값 사용 (%s)", self.industry_code)
                return

            updated = False

            # 식재료비 비율 → _cogs_ratio
            if cost.get("food_cost_ratio"):
                self._cogs_ratio = cost["food_cost_ratio"]
                updated = True
                logger.info(
                    "KOSIS 식재료비 비율 적용: %.1f%% (%s)",
                    self._cogs_ratio * 100, self.industry_code,
                )

            # 인건비 비율 → DISTRICT_TYPE_FACTORS의 labor_ratio
            if cost.get("labor_cost_ratio"):
                kosis_labor = cost["labor_cost_ratio"]
                # 상권 유형별 보정 계수를 유지하되, 기준값을 KOSIS로 대체
                for dt_name, factors in self._district_type_factors.items():
                    original = factors.get("labor_ratio", 0.25)
                    # 기존 기본값(0.25) 대비 각 상권 유형의 편차를 유지
                    delta = original - 0.25
                    factors["labor_ratio"] = round(kosis_labor + delta, 4)
                updated = True
                logger.info(
                    "KOSIS 인건비 비율 적용: %.1f%% (기준) (%s)",
                    kosis_labor * 100, self.industry_code,
                )

            # 임차료 비율 (참고용 — 시뮬레이션은 실제 임대료 추정값 사용)
            if cost.get("rent_ratio"):
                self._rent_ratio: float = cost["rent_ratio"]
                updated = True

            # 영업이익률
            if cost.get("profit_margin"):
                self._kosis_profit_margin: float = cost["profit_margin"]
                updated = True

            if updated:
                year = cost.get("year", "2023")
                self._cost_data_source = f"KOSIS 외식업체경영실태조사 {year}"
                logger.info("KOSIS 원가구조 반영 완료 (%s)", self.industry_code)

        except Exception as e:
            logger.warning("KOSIS 보강 실패 (config 기본값 사용): %s", e)

    # -----------------------------------------------------------------------
    # 1. 매출 시뮬레이션
    # -----------------------------------------------------------------------

    def estimate_revenue(self, district: dict[str, Any]) -> RevenueEstimate:
        sc = max(1, district.get("store_count", 1))
        monthly_sales = district["monthly_sales"]
        monthly_tx = district.get("monthly_transactions", 0)

        sps = int(monthly_sales / sc)
        tx_per_store = int(monthly_tx / sc)
        avg_ticket = int(sps / max(1, tx_per_store))

        p25, _, p75 = self._percentiles.get(
            district["district_type"], (int(sps * 0.7), sps, int(sps * 1.3))
        )
        pessimistic = max(p25, int(sps * 0.7))
        optimistic = min(p75, int(sps * 1.3))

        daily = int(sps / 30)

        peak_time = district.get("peak_time", "11-14")
        time_fields = {
            "00-06": "time_00_06_sales",
            "06-11": "time_06_11_sales",
            "11-14": "time_11_14_sales",
            "14-17": "time_14_17_sales",
            "17-21": "time_17_21_sales",
            "21-24": "time_21_24_sales",
        }
        peak_time_total = district.get(time_fields.get(peak_time, "time_11_14_sales"), 0)
        peak_time_sales = int(peak_time_total / sc)

        peak_day = district.get("peak_day", "월")
        day_fields = {
            "월": "mon_sales", "화": "tue_sales", "수": "wed_sales",
            "목": "thu_sales", "금": "fri_sales", "토": "sat_sales", "일": "sun_sales",
        }
        peak_day_total = district.get(day_fields.get(peak_day, "mon_sales"), 0)
        peak_day_sales = int(peak_day_total / sc)

        return RevenueEstimate(
            monthly_sales_per_store=sps,
            monthly_transactions_per_store=tx_per_store,
            avg_ticket=avg_ticket,
            pessimistic=pessimistic,
            optimistic=optimistic,
            daily_sales=daily,
            peak_time_sales=peak_time_sales,
            peak_time=peak_time,
            peak_day_sales=peak_day_sales,
            peak_day=peak_day,
        )

    # -----------------------------------------------------------------------
    # 2. 초기 투자비용
    # -----------------------------------------------------------------------

    def estimate_startup_cost(
        self,
        monthly_rent: int,
        district_type: str,
        area_pyeong: int = 10,
    ) -> StartupCost:
        factors = self._district_type_factors.get(
            district_type, self._district_type_factors.get("골목상권", DISTRICT_TYPE_FACTORS["골목상권"])
        )
        deposit_mult = factors["deposit_mult"]
        deposit = int(monthly_rent * deposit_mult)

        interior = int(factors["interior_per_pyeong"] * area_pyeong)

        eq_min = sum(lo for lo, _ in self._equipment_cost.values())
        eq_max = sum(hi for _, hi in self._equipment_cost.values())

        return StartupCost(
            deposit=deposit,
            interior=interior,
            equipment_min=eq_min,
            equipment_max=eq_max,
            initial_inventory_min=self._initial_inventory[0],
            initial_inventory_max=self._initial_inventory[1],
            permits_misc_min=self._permits_and_misc[0],
            permits_misc_max=self._permits_and_misc[1],
            total_min=int(deposit + interior + eq_min + self._initial_inventory[0] + self._permits_and_misc[0]),
            total_max=int(deposit + interior + eq_max + self._initial_inventory[1] + self._permits_and_misc[1]),
            interior_grade="mid",
            area_pyeong=area_pyeong,
        )

    # -----------------------------------------------------------------------
    # 3. 운영비
    # -----------------------------------------------------------------------

    def estimate_operating_cost(
        self,
        monthly_revenue: int,
        monthly_rent: int,
        district_type: str,
    ) -> OperatingCost:
        factors = self._district_type_factors.get(
            district_type, self._district_type_factors.get("골목상권", DISTRICT_TYPE_FACTORS["골목상권"])
        )
        cogs = int(monthly_revenue * self._cogs_ratio)
        labor = int(monthly_revenue * factors["labor_ratio"])
        utilities = int(monthly_revenue * self._utilities_ratio)
        other = int(monthly_revenue * self._other_ratio)
        total = monthly_rent + cogs + labor + utilities + other

        return OperatingCost(
            rent=monthly_rent,
            cogs=cogs,
            labor=labor,
            utilities=utilities,
            other=other,
            total=total,
        )

    # -----------------------------------------------------------------------
    # 4. 손익분기점
    # -----------------------------------------------------------------------

    def calculate_break_even(
        self,
        monthly_revenue: int,
        operating_cost: OperatingCost,
        startup_cost: StartupCost,
    ) -> BreakEvenResult:
        net_profit = monthly_revenue - operating_cost["total"]
        margin = net_profit / max(1, monthly_revenue)

        if net_profit <= 0:
            be_min = 999
            be_max = 999
        else:
            be_min = math.ceil(startup_cost["total_min"] / net_profit)
            be_max = math.ceil(startup_cost["total_max"] / net_profit)

        daily_be = int(operating_cost["total"] / 30)

        return BreakEvenResult(
            monthly_revenue=monthly_revenue,
            monthly_operating_cost=operating_cost["total"],
            monthly_net_profit=net_profit,
            net_profit_margin=round(margin, 4),
            initial_investment_min=startup_cost["total_min"],
            initial_investment_max=startup_cost["total_max"],
            break_even_months_min=be_min,
            break_even_months_max=be_max,
            daily_break_even_sales=daily_be,
        )

    # -----------------------------------------------------------------------
    # 공정위 가맹사업 벤치마크 보강
    # -----------------------------------------------------------------------

    async def enrich_with_franchise_data(
        self, result: SimulationResult,
    ) -> SimulationResult:
        """공정위 가맹사업 데이터로 시뮬레이션 결과를 보강한다."""
        try:
            from api.services.franchise_data_service import get_franchise_benchmark

            benchmark = await get_franchise_benchmark(self.industry_code)
            if benchmark and benchmark.get("available"):
                franchise_info: dict[str, Any] = {
                    "source": f"공정거래위원회 가맹사업 정보공개서 {benchmark.get('year', '')}".strip(),
                }
                if benchmark.get("avg_total_startup_cost"):
                    franchise_info["avg_total_startup_cost"] = benchmark["avg_total_startup_cost"]
                if benchmark.get("avg_interior_cost"):
                    franchise_info["avg_interior_cost"] = benchmark["avg_interior_cost"]
                # 개별 소분류별 창업비용 상세 (프론트엔드 비교표용)
                if benchmark.get("startup_costs"):
                    franchise_info["startup_costs"] = benchmark["startup_costs"]
                # 브랜드 수, 가맹점 수 합산
                statuses = benchmark.get("industry_status", [])
                if statuses:
                    franchise_info["brand_count"] = sum(
                        s.get("brand_count", 0) for s in statuses
                    )
                    franchise_info["store_count"] = sum(
                        s.get("store_count", 0) for s in statuses
                    )
                result["franchise_benchmark"] = franchise_info
        except Exception as e:
            logger.warning("공정위 데이터 보강 실패 (무시): %s", e)

        return result

    # -----------------------------------------------------------------------
    # 통합 시뮬레이션
    # -----------------------------------------------------------------------

    async def simulate(
        self,
        district_code: str,
        area_pyeong: int = 10,
    ) -> SimulationResult | None:
        # KOSIS 데이터로 원가율 보강 (최초 1회)
        await self._enrich_with_kosis()

        detail_raw: dict[str, Any] | None = None
        district: dict[str, Any] | None = None

        for d in self.data_service.districts:
            if d["district_code"] == district_code:
                district = d
                break

        if district is None:
            return None

        sc = max(1, district.get("store_count", 1))
        sps = int(district["monthly_sales"] / sc)
        pctile = self.data_service._sales_percentile.get(district["district_code"], 0.5)
        estimated_rent = estimate_rent(district["district_type"], sps, pctile)

        revenue = self.estimate_revenue(district)
        startup = self.estimate_startup_cost(
            monthly_rent=estimated_rent,
            district_type=district["district_type"],
            area_pyeong=area_pyeong,
        )
        operating = self.estimate_operating_cost(
            monthly_revenue=revenue["monthly_sales_per_store"],
            monthly_rent=estimated_rent,
            district_type=district["district_type"],
        )
        break_even = self.calculate_break_even(
            monthly_revenue=revenue["monthly_sales_per_store"],
            operating_cost=operating,
            startup_cost=startup,
        )

        risks: list[str] = []
        if district.get("store_count", 0) > 20:
            risks.append(f"높은 경쟁 밀도 ({self.display_name} {district['store_count']}개)")
        if district.get("survival_rate", 1) < 0.7:
            risks.append(f"낮은 생존율 ({district['survival_rate'] * 100:.0f}%)")
        if district.get("closed_stores", 0) > district.get("new_stores", 0):
            risks.append("폐업이 개업보다 많은 상권")
        if break_even["break_even_months_max"] > 36:
            risks.append("투자 회수 3년 이상 소요 예상")

        area_sqm = int(area_pyeong * 3.3)
        seats_min, seats_max = estimate_seats(area_pyeong)
        assumptions = SimulationAssumptions(
            area_pyeong=area_pyeong,
            area_sqm=area_sqm,
            seats_min=seats_min,
            seats_max=seats_max,
            summary=f"{area_pyeong}평(약 {area_sqm}㎡) / {seats_min}~{seats_max}석 기준",
            disclaimer="업종 평균 기준 추정치입니다. 실제 비용은 입지·인테리어 수준에 따라 ±20% 차이가 있을 수 있습니다.",
        )

        result = SimulationResult(
            district_name=district["district_name"],
            district_type=district["district_type"],
            district_code=district_code,
            revenue=revenue,
            startup_cost=startup,
            operating_cost=operating,
            break_even=break_even,
            assumptions=assumptions,
            competition={
                "store_count": district.get("store_count", 0),
                "new_stores": district.get("new_stores", 0),
                "closed_stores": district.get("closed_stores", 0),
                "franchise_stores": district.get("franchise_stores", 0),
                "franchise_ratio": round(
                    district.get("franchise_stores", 0)
                    / max(1, district.get("store_count", 1))
                    * 100,
                    1,
                ),
                "survival_rate": district.get("survival_rate", 0),
            },
            risk_summary=risks,
            cost_data_source=self._cost_data_source,
        )

        # 공정위 가맹사업 벤치마크 데이터 보강
        result = await self.enrich_with_franchise_data(result)

        return result


# ---------------------------------------------------------------------------
# 레지스트리 패턴 (업종별 인스턴스)
# ---------------------------------------------------------------------------

_registry: dict[str, SimulationService] = {}


def get_simulation_service(industry_code: str = DEFAULT_INDUSTRY) -> SimulationService:
    """Get or create a SimulationService for the given industry code."""
    if industry_code not in _registry:
        _registry[industry_code] = SimulationService(industry_code=industry_code)
    return _registry[industry_code]
