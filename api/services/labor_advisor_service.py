"""Labor advisor service for wage and social insurance planning."""

from __future__ import annotations

from typing import TypedDict

from config.industry_config import DEFAULT_INDUSTRY, load_industry_config

from api.services.data_service import DataService, get_data_service
from api.services.krei_data_service import get_cost_benchmarks
from api.services.legal_reference_service import get_legal_reference_service


def _to_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except Exception:
            return default
    return default


def _to_float(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except Exception:
            return default
    return default


def _to_str(value: object, default: str = "") -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


class WageReference(TypedDict):
    effective_year: int
    hourly_won: int
    monthly_won_209h: int


class InsuranceRateBreakdown(TypedDict):
    national_pension_rate: float
    health_insurance_rate: float
    long_term_care_rate: float
    employment_insurance_rate: float
    industrial_accident_rate: float
    total_employer_rate: float


class LaborPlan(TypedDict):
    employee_count: int
    monthly_gross_wage: int
    monthly_employer_insurance: int
    monthly_total_labor_cost: int


class LaborBenchmark(TypedDict):
    recommended_labor_ratio: float
    labor_budget_from_sales: int
    benchmark_source: str


class LaborAdvice(TypedDict):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    monthly_revenue: int
    wage_reference: WageReference
    insurance_rates: InsuranceRateBreakdown
    labor_plan: LaborPlan
    labor_benchmark: LaborBenchmark
    affordable: bool
    budget_gap: int
    actions: list[str]
    glossary: dict[str, str]
    legal_meta: dict[str, object]


class LaborAdvisorService:
    def __init__(
        self,
        industry_code: str = DEFAULT_INDUSTRY,
        data_service: DataService | None = None,
    ) -> None:
        self.industry_code: str = industry_code
        self.data_service: DataService = data_service or get_data_service(industry_code)

        cfg = load_industry_config(industry_code)
        self.industry_name: str = _to_str(cfg.get("display_name", cfg.get("name", "업종")), "업종")
        self._fallback_labor_ratio: float = _to_float(cfg.get("LABOR_RATIO", 0.27), 0.27)

    def analyze(
        self,
        district_code: str,
        employee_plan: str | None = None,
        custom_headcount: int | None = None,
        monthly_revenue_override: int | None = None,
    ) -> LaborAdvice | None:
        district = self.data_service.get_district(district_code)
        if district is None:
            district = self.data_service.get_district_by_name(district_code)
        if district is None:
            return None

        store_count = max(1, _to_int(district.get("store_count", 1), 1))
        district_monthly = _to_int(district.get("monthly_sales", 0), 0) // store_count
        monthly_revenue = (
            _to_int(monthly_revenue_override, district_monthly)
            if monthly_revenue_override is not None and monthly_revenue_override > 0
            else district_monthly
        )

        district_type = _to_str(district.get("district_type", "골목상권"), "골목상권")
        benchmark = get_cost_benchmarks(
            self.industry_code,
            district_type=district_type,
            seoul_only=True,
        )
        if benchmark and "labor_pct" in benchmark:
            labor_ratio = _to_float(benchmark.get("labor_pct", 0.27), self._fallback_labor_ratio)
            benchmark_source = _to_str(benchmark.get("source", "KREI"), "KREI")
        else:
            labor_ratio = self._fallback_labor_ratio
            benchmark_source = "industry config fallback"

        legal = get_legal_reference_service()
        labor_rules = legal.get_labor_rules()
        wage_raw = labor_rules.get("minimum_wage", {})
        wage = wage_raw if isinstance(wage_raw, dict) else {}

        social_raw = labor_rules.get("social_insurance", {})
        social = social_raw if isinstance(social_raw, dict) else {}

        min_wage_monthly = _to_int(wage.get("monthly_won_209h", 2_096_270), 2_096_270)

        if custom_headcount is not None and custom_headcount > 0:
            employee_count = custom_headcount
        else:
            if employee_plan == "solo":
                employee_count = 1
            elif employee_plan == "1-2":
                employee_count = 2
            elif employee_plan == "3+":
                employee_count = 3
            else:
                if monthly_revenue < 30_000_000:
                    employee_count = 1
                elif monthly_revenue < 80_000_000:
                    employee_count = 2
                else:
                    employee_count = 3

        pension_rate = _to_float(social.get("national_pension_employer_rate", 0.045), 0.045)
        health_rate = _to_float(social.get("health_insurance_employer_rate", 0.03545), 0.03545)
        ltc_multiplier = _to_float(social.get("long_term_care_rate_on_health", 0.1295), 0.1295)
        employment_rate = _to_float(social.get("employment_insurance_employer_rate", 0.009), 0.009)
        industrial_rate = _to_float(social.get("industrial_accident_default_rate", 0.01), 0.01)

        ltc_rate = health_rate * ltc_multiplier
        total_rate = pension_rate + health_rate + ltc_rate + employment_rate + industrial_rate

        gross_wage = min_wage_monthly * employee_count
        employer_insurance = int(gross_wage * total_rate)
        total_labor_cost = gross_wage + employer_insurance

        labor_budget = int(monthly_revenue * labor_ratio)
        budget_gap = labor_budget - total_labor_cost
        affordable = budget_gap >= 0

        actions = [
            "근로계약서(근무시간/휴게시간/수습 여부) 표준 양식으로 계약",
            "4대보험 취득 신고를 입사일 기준으로 즉시 처리",
            "피크 타임(점심/저녁)에 집중 배치하고 비피크 교대는 최소화",
        ]
        if not affordable:
            actions.insert(0, "초기 3개월은 파트타임/사장 실근무 비중을 높여 인건비를 조정")

        district_code_value = _to_str(district.get("district_code", district_code), district_code)
        district_name_value = _to_str(district.get("district_name", ""))

        return {
            "district_code": district_code_value,
            "district_name": district_name_value,
            "industry_code": self.industry_code,
            "industry_name": self.industry_name,
            "monthly_revenue": monthly_revenue,
            "wage_reference": {
                "effective_year": _to_int(wage.get("effective_year", 2025), 2025),
                "hourly_won": _to_int(wage.get("hourly_won", 10_030), 10_030),
                "monthly_won_209h": min_wage_monthly,
            },
            "insurance_rates": {
                "national_pension_rate": round(pension_rate, 6),
                "health_insurance_rate": round(health_rate, 6),
                "long_term_care_rate": round(ltc_rate, 6),
                "employment_insurance_rate": round(employment_rate, 6),
                "industrial_accident_rate": round(industrial_rate, 6),
                "total_employer_rate": round(total_rate, 6),
            },
            "labor_plan": {
                "employee_count": employee_count,
                "monthly_gross_wage": gross_wage,
                "monthly_employer_insurance": employer_insurance,
                "monthly_total_labor_cost": total_labor_cost,
            },
            "labor_benchmark": {
                "recommended_labor_ratio": round(labor_ratio, 4),
                "labor_budget_from_sales": labor_budget,
                "benchmark_source": benchmark_source,
            },
            "affordable": affordable,
            "budget_gap": budget_gap,
            "actions": actions,
            "glossary": legal.get_glossary(),
            "legal_meta": legal.get_meta(),
        }


_registry: dict[str, LaborAdvisorService] = {}


def get_labor_advisor_service(industry_code: str = DEFAULT_INDUSTRY) -> LaborAdvisorService:
    if industry_code not in _registry:
        _registry[industry_code] = LaborAdvisorService(industry_code=industry_code)
    return _registry[industry_code]
