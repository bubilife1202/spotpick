"""
매출 시뮬레이션 · 초기 투자비용 · 손익분기점 분석 서비스

모든 금액 단위: 원(KRW)
"""

from __future__ import annotations

import json
import logging
import math
from pathlib import Path
from typing import Any, TypedDict

from api.services.data_service import DataService, estimate_rent, get_data_service
from config.industry_config import load_industry_config, DEFAULT_INDUSTRY

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 업계 벤치마크 상수 (DEPRECATED)
# - KREI 데이터가 존재하면 runtime에 실데이터로 대체된다.
# ---------------------------------------------------------------------------

_LEGACY_FALLBACK = {
    "골목상권": {"interior_per_pyeong": 1_800_000, "labor_ratio": 0.25, "deposit_mult": 10},
    "발달상권": {"interior_per_pyeong": 2_500_000, "labor_ratio": 0.27, "deposit_mult": 15},
    "전통시장": {"interior_per_pyeong": 1_500_000, "labor_ratio": 0.24, "deposit_mult": 8},
    "관광특구": {"interior_per_pyeong": 2_800_000, "labor_ratio": 0.26, "deposit_mult": 15},
}

# DEPRECATED: legacy equipment ranges (use KREI kitchen_total when available)
EQUIPMENT_COST = {
    "espresso_machine": (8_000_000, 15_000_000),
    "grinder": (2_000_000, 5_000_000),
    "refrigeration": (5_000_000, 8_000_000),
    "furniture": (10_000_000, 15_000_000),
    "pos": (2_000_000, 3_000_000),
}

INITIAL_INVENTORY = (3_000_000, 5_000_000)

# DEPRECATED: only used if KREI/permitting data unavailable
_LEGACY_PERMITS_AND_MISC = (5_000_000, 10_000_000)

# DEPRECATED: replaced by KREI food_pct
_LEGACY_COGS_RATIO = 0.32

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
        self._cost_data_source: str = "Legacy config defaults (KREI 미적용)"
        self._rent_ratio: float = 0.0
        self._kosis_profit_margin: float = 0.0

        # 가능한 경우, 초기화 시점에 KREI를 우선 적용 (sync)
        self._try_krei_enrichment()

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
            self._district_type_factors = _LEGACY_FALLBACK

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
            self._cogs_ratio = _LEGACY_COGS_RATIO

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
            self._permits_and_misc = _LEGACY_PERMITS_AND_MISC

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
    # KREI 원시자료 → KOSIS API 폴백 체인으로 원가율 보강 (최초 1회)
    # -----------------------------------------------------------------------

    async def _enrich_with_kosis(self) -> None:
        """KREI 원시자료 우선, KOSIS API 폴백으로 원가율을 실측치로 대체."""
        if self._kosis_enriched:
            return

        self._kosis_enriched = True  # 실패해도 재시도 방지

        # --- 1단계: KREI 원시자료 ---
        krei_ok = self._try_krei_enrichment()
        if krei_ok:
            return

        # --- 2단계: KOSIS API 폴백 ---
        await self._try_kosis_enrichment()

    def _try_krei_enrichment(self) -> bool:
        """KREI 원시자료 데이터로 원가율 보강. 성공하면 True."""
        try:
            from api.services.krei_data_service import get_cost_benchmarks

            base = get_cost_benchmarks(self.industry_code, district_type=None, seoul_only=True)
            if base is None or base.get("n", 0) < 5:
                logger.info("KREI 데이터 부족 — KOSIS 폴백 (%s)", self.industry_code)
                return False

            updated = False
            n = int(base.get("n", 0) or 0)

            # 식재료비 비율 → _cogs_ratio
            food_pct = base.get("food_pct")
            if isinstance(food_pct, (int, float)):
                self._cogs_ratio = float(food_pct)
                updated = True
                logger.info(
                    "KREI 식재료비 비율 적용: %.1f%% (%s)",
                    float(food_pct) * 100.0,
                    self.industry_code,
                )

            # 임차료 비율 (참고용)
            rent_pct = base.get("rent_pct")
            if isinstance(rent_pct, (int, float)):
                self._rent_ratio = float(rent_pct)
                updated = True

            # 영업이익률
            profit_pct = base.get("profit_pct")
            if isinstance(profit_pct, (int, float)):
                self._kosis_profit_margin = float(profit_pct)
                updated = True

            # 상권유형별 벤치마크 적용 (노동비/인테리어/보증금 배수)
            for dt_name, factors in self._district_type_factors.items():
                bm = get_cost_benchmarks(self.industry_code, district_type=dt_name, seoul_only=True)
                if not bm:
                    continue

                labor_pct = bm.get("labor_pct")
                if isinstance(labor_pct, (int, float)):
                    factors["labor_ratio"] = float(labor_pct)
                    updated = True

                interior_pp = bm.get("interior_per_pyeong")
                if isinstance(interior_pp, int):
                    factors["interior_per_pyeong"] = int(interior_pp)
                    updated = True

                dep_mult = bm.get("deposit_to_rent_ratio")
                if isinstance(dep_mult, (int, float)) and dep_mult > 0:
                    factors["deposit_mult"] = float(dep_mult)
                    updated = True

            if updated:
                self._cost_data_source = (
                    f"KREI 외식업체경영실태조사 2023 (서울 {self.display_name}, n={n})"
                )
                logger.info("KREI 원가구조 반영 완료 (%s)", self.industry_code)
                return True

        except Exception as e:
            logger.warning("KREI 보강 실패: %s", e)

        return False

    async def _try_kosis_enrichment(self) -> None:
        """KOSIS API 폴백으로 원가율 보강."""
        try:
            from api.services.kosis_data_service import get_cost_structure

            cost = await get_cost_structure(self.industry_code)
            if cost is None:
                logger.info("KOSIS 데이터도 없음 — config 기본값 사용 (%s)", self.industry_code)
                return

            updated = False

            food_ratio = cost.get("food_cost_ratio")
            if isinstance(food_ratio, (int, float)):
                self._cogs_ratio = float(food_ratio)
                updated = True

            labor_ratio = cost.get("labor_cost_ratio")
            if isinstance(labor_ratio, (int, float)):
                kosis_labor = float(labor_ratio)
                for dt_name, factors in self._district_type_factors.items():
                    original = factors.get("labor_ratio", 0.25)
                    delta = original - 0.25
                    factors["labor_ratio"] = round(kosis_labor + delta, 4)
                updated = True

            kosis_rent_ratio = cost.get("rent_ratio")
            if isinstance(kosis_rent_ratio, (int, float)):
                self._rent_ratio = float(kosis_rent_ratio)
                updated = True

            kosis_profit = cost.get("profit_margin")
            if isinstance(kosis_profit, (int, float)):
                self._kosis_profit_margin = float(kosis_profit)
                updated = True

            if updated:
                year = cost.get("year", "2023")
                self._cost_data_source = f"KOSIS 외식업체경영실태조사 {year}"
                logger.info("KOSIS 원가구조 반영 완료 (폴백) (%s)", self.industry_code)

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
            "월": "mon_sales",
            "화": "tue_sales",
            "수": "wed_sales",
            "목": "thu_sales",
            "금": "fri_sales",
            "토": "sat_sales",
            "일": "sun_sales",
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
            district_type, self._district_type_factors.get("골목상권", _LEGACY_FALLBACK["골목상권"])
        )

        deposit_mult = float(factors.get("deposit_mult", 10))
        deposit = int(monthly_rent * deposit_mult)

        interior = int(factors["interior_per_pyeong"] * area_pyeong)

        try:
            from api.services.krei_data_service import get_cost_benchmarks

            bm = get_cost_benchmarks(
                self.industry_code, district_type=district_type, seoul_only=True
            )
        except Exception:
            bm = None

        # KREI 보증금 직접 사용
        dep = bm.get("deposit_median") if bm else None
        if isinstance(dep, int) and dep > 0:
            deposit = int(dep)

        # KREI 주방/설비 비용 우선 (없으면 legacy range)
        kitchen_total_val = bm.get("kitchen_total") if bm else None
        if isinstance(kitchen_total_val, int) and kitchen_total_val > 0:
            kitchen_total = int(kitchen_total_val)
            eq_min = kitchen_total
            eq_max = kitchen_total
        else:
            eq_min = sum(lo for lo, _ in self._equipment_cost.values())
            eq_max = sum(hi for _, hi in self._equipment_cost.values())

        # 인허가 + 기타 (업종별 permits + KREI 총투자 기반 잔여분)
        permits_min = self._permits_and_misc[0]
        permits_max = self._permits_and_misc[1]
        try:
            permits_path = Path(__file__).parent.parent / "data" / "industry_permits.json"
            with open(permits_path, encoding="utf-8") as f:
                permits_data = json.load(f)
            industry_permits = permits_data.get(self.industry_code, {}).get("permits", [])
            total_permit_cost = sum(int(p.get("cost", 0) or 0) for p in industry_permits)

            invest_total_val = bm.get("invest_total") if bm else None
            if isinstance(invest_total_val, int) and invest_total_val > 0:
                invest_total = int(invest_total_val)
                misc_overhead = max(0, invest_total - interior - eq_max - deposit)
                total_misc = total_permit_cost + misc_overhead
                permits_min = total_misc
                permits_max = total_misc
            else:
                permits_min = max(permits_min, total_permit_cost)
                permits_max = max(permits_max, total_permit_cost)
        except Exception:
            # Keep legacy fallback
            pass

        return StartupCost(
            deposit=deposit,
            interior=interior,
            equipment_min=eq_min,
            equipment_max=eq_max,
            initial_inventory_min=self._initial_inventory[0],
            initial_inventory_max=self._initial_inventory[1],
            permits_misc_min=permits_min,
            permits_misc_max=permits_max,
            total_min=int(deposit + interior + eq_min + self._initial_inventory[0] + permits_min),
            total_max=int(deposit + interior + eq_max + self._initial_inventory[1] + permits_max),
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
            district_type, self._district_type_factors.get("골목상권", _LEGACY_FALLBACK["골목상권"])
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
        self,
        result: SimulationResult,
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
                # 개별 소분류별 창업비용 상세 (프론트엔드 비교표용)
                if benchmark.get("startup_costs"):
                    franchise_info["startup_costs"] = benchmark["startup_costs"]
                # 브랜드 수, 가맹점 수 합산
                statuses = benchmark.get("industry_status", [])
                if statuses:
                    franchise_info["brand_count"] = sum(s.get("brand_count", 0) for s in statuses)
                    franchise_info["store_count"] = sum(s.get("store_count", 0) for s in statuses)
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
        estimated_rent = estimate_rent(
            district["district_type"], sps, pctile, industry_code=self.industry_code
        )

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
                "survival_rate": min(district.get("survival_rate", 0), 1.0),
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
