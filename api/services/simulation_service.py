"""
매출 시뮬레이션 · 초기 투자비용 · 손익분기점 분석 서비스

모든 금액 단위: 원(KRW)
"""

from __future__ import annotations

import math
from typing import Any, Optional, TypedDict

from api.services.data_service import DataService, get_data_service


# ---------------------------------------------------------------------------
# 업계 벤치마크 상수
# ---------------------------------------------------------------------------

INTERIOR_COST_PER_PYEONG = {
    "basic": 1_600_000,
    "mid": 2_150_000,
    "premium": 2_750_000,
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

DEPOSIT_MULTIPLIER = {
    "골목상권": 10,
    "발달상권": 15,
    "전통시장": 8,
    "관광특구": 15,
}

OPERATING_RATIOS = {
    "cogs": 0.32,
    "labor": 0.25,
    "utilities": 0.035,
    "other": 0.075,
}

OPERATING_MARGIN_RANGE = (0.08, 0.15)


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


class SimulationResult(TypedDict):
    district_name: str
    district_type: str
    district_code: str
    revenue: RevenueEstimate
    startup_cost: StartupCost
    operating_cost: OperatingCost
    break_even: BreakEvenResult
    competition: dict[str, Any]
    risk_summary: list[str]


# ---------------------------------------------------------------------------
# 서비스
# ---------------------------------------------------------------------------

class SimulationService:
    def __init__(self, data_service: DataService | None = None) -> None:
        self.data_service = data_service or get_data_service()
        self._build_percentile_cache()

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
        interior_grade: str = "mid",
    ) -> StartupCost:
        deposit_mult = DEPOSIT_MULTIPLIER.get(district_type, 10)
        deposit = monthly_rent * deposit_mult

        cost_per_pyeong = INTERIOR_COST_PER_PYEONG.get(interior_grade, INTERIOR_COST_PER_PYEONG["mid"])
        interior = cost_per_pyeong * area_pyeong

        eq_min = sum(lo for lo, _ in EQUIPMENT_COST.values())
        eq_max = sum(hi for _, hi in EQUIPMENT_COST.values())

        return StartupCost(
            deposit=deposit,
            interior=interior,
            equipment_min=eq_min,
            equipment_max=eq_max,
            initial_inventory_min=INITIAL_INVENTORY[0],
            initial_inventory_max=INITIAL_INVENTORY[1],
            permits_misc_min=PERMITS_AND_MISC[0],
            permits_misc_max=PERMITS_AND_MISC[1],
            total_min=deposit + interior + eq_min + INITIAL_INVENTORY[0] + PERMITS_AND_MISC[0],
            total_max=deposit + interior + eq_max + INITIAL_INVENTORY[1] + PERMITS_AND_MISC[1],
            interior_grade=interior_grade,
            area_pyeong=area_pyeong,
        )

    # -----------------------------------------------------------------------
    # 3. 운영비
    # -----------------------------------------------------------------------

    def estimate_operating_cost(self, monthly_revenue: int, monthly_rent: int) -> OperatingCost:
        cogs = int(monthly_revenue * OPERATING_RATIOS["cogs"])
        labor = int(monthly_revenue * OPERATING_RATIOS["labor"])
        utilities = int(monthly_revenue * OPERATING_RATIOS["utilities"])
        other = int(monthly_revenue * OPERATING_RATIOS["other"])
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
    # 통합 시뮬레이션
    # -----------------------------------------------------------------------

    def simulate(
        self,
        district_code: str,
        area_pyeong: int = 10,
        interior_grade: str = "mid",
    ) -> SimulationResult | None:
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
        estimated_rent = int(sps * 0.07 / 10_000) * 10_000
        estimated_rent = max(1_500_000, min(estimated_rent, 15_000_000))

        revenue = self.estimate_revenue(district)
        startup = self.estimate_startup_cost(
            monthly_rent=estimated_rent,
            district_type=district["district_type"],
            area_pyeong=area_pyeong,
            interior_grade=interior_grade,
        )
        operating = self.estimate_operating_cost(
            monthly_revenue=revenue["monthly_sales_per_store"],
            monthly_rent=estimated_rent,
        )
        break_even = self.calculate_break_even(
            monthly_revenue=revenue["monthly_sales_per_store"],
            operating_cost=operating,
            startup_cost=startup,
        )

        risks: list[str] = []
        if district.get("store_count", 0) > 20:
            risks.append(f"높은 경쟁 밀도 (커피숍 {district['store_count']}개)")
        if district.get("survival_rate", 1) < 0.7:
            risks.append(f"낮은 생존율 ({district['survival_rate'] * 100:.0f}%)")
        if district.get("closed_stores", 0) > district.get("new_stores", 0):
            risks.append("폐업이 개업보다 많은 상권")
        if break_even["break_even_months_max"] > 36:
            risks.append("투자 회수 3년 이상 소요 예상")

        return SimulationResult(
            district_name=district["district_name"],
            district_type=district["district_type"],
            district_code=district_code,
            revenue=revenue,
            startup_cost=startup,
            operating_cost=operating,
            break_even=break_even,
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
        )


# ---------------------------------------------------------------------------
# 싱글톤
# ---------------------------------------------------------------------------

_instance: SimulationService | None = None


def get_simulation_service() -> SimulationService:
    global _instance
    if _instance is None:
        _instance = SimulationService()
    return _instance
