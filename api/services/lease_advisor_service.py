"""Lease advisor service for rent/deposit and legal protection checks."""

from __future__ import annotations

from typing import TypedDict

from config.industry_config import DEFAULT_INDUSTRY, load_industry_config

from api.services.data_service import DataService, estimate_rent, get_data_service
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


class RentEstimate(TypedDict):
    monthly_rent: int
    deposit: int
    source: str


class LegalProtection(TypedDict):
    converted_deposit: int
    threshold: int
    protected: bool
    region: str
    monthly_multiplier: int
    renewal_request_years: int
    rent_increase_cap_rate: float


class LeaseAdvice(TypedDict):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    rent_estimate: RentEstimate
    legal_protection: LegalProtection
    contract_checklist: list[str]
    actions: list[str]
    glossary: dict[str, str]
    legal_meta: dict[str, object]


class LeaseAdvisorService:
    def __init__(
        self,
        industry_code: str = DEFAULT_INDUSTRY,
        data_service: DataService | None = None,
    ) -> None:
        self.industry_code: str = industry_code
        self.data_service: DataService = data_service or get_data_service(industry_code)
        cfg = load_industry_config(industry_code)
        self.industry_name: str = _to_str(cfg.get("display_name", cfg.get("name", "업종")), "업종")

    def analyze(
        self,
        district_code: str,
        region: str = "seoul",
        monthly_rent_override: int | None = None,
        deposit_override: int | None = None,
    ) -> LeaseAdvice | None:
        district = self.data_service.get_district(district_code)
        if district is None:
            district = self.data_service.get_district_by_name(district_code)
        if district is None:
            return None

        store_count = max(1, _to_int(district.get("store_count", 1), 1))
        sales_per_store = _to_int(district.get("monthly_sales", 0), 0) // store_count
        district_type = _to_str(district.get("district_type", "골목상권"), "골목상권")
        district_code_resolved = _to_str(
            district.get("district_code", district_code), district_code
        )
        percentile = _to_float(
            self.data_service._sales_percentile.get(district_code_resolved, 0.5), 0.5
        )

        estimated_monthly_rent = estimate_rent(
            district_type=district_type,
            sales_per_store=sales_per_store,
            percentile_rank=percentile,
            rent_ranges=getattr(self.data_service, "_rent_ranges", None),
            industry_code=self.industry_code,
        )

        benchmark = get_cost_benchmarks(
            self.industry_code, district_type=district_type, seoul_only=True
        )
        benchmark_deposit = _to_int(benchmark.get("deposit_median", 0), 0) if benchmark else 0

        monthly_rent = (
            _to_int(monthly_rent_override, estimated_monthly_rent)
            if monthly_rent_override is not None and monthly_rent_override > 0
            else estimated_monthly_rent
        )
        if deposit_override is not None and deposit_override > 0:
            deposit = _to_int(deposit_override, benchmark_deposit)
            deposit_source = "user_input"
        elif benchmark_deposit > 0:
            deposit = benchmark_deposit
            deposit_source = "krei_benchmark"
        else:
            deposit = monthly_rent * 10
            deposit_source = "fallback_10x_rent"

        legal = get_legal_reference_service()
        lease_rules = legal.get_lease_rules()
        thresholds_raw = lease_rules.get("protected_deposit_thresholds_won", {})
        thresholds = thresholds_raw if isinstance(thresholds_raw, dict) else {}

        normalized_region = region.strip().lower() if isinstance(region, str) else "seoul"
        if normalized_region not in (
            "seoul",
            "metropolitan_overconcentration",
            "metropolitan_city",
            "etc",
        ):
            normalized_region = "seoul"

        threshold = _to_int(thresholds.get(normalized_region, 900_000_000), 900_000_000)
        monthly_multiplier = _to_int(
            lease_rules.get("monthly_rent_to_deposit_multiplier", 100), 100
        )
        converted_deposit = deposit + (monthly_rent * monthly_multiplier)
        protected = converted_deposit <= threshold

        renewal_years = _to_int(lease_rules.get("contract_renewal_request_years", 10), 10)
        increase_cap = _to_float(lease_rules.get("rent_increase_cap_rate", 0.05), 0.05)

        contract_checklist = [
            "등기부등본 확인: 근저당/가압류/신탁 여부 확인",
            "건축물대장 확인: 업종 영업 가능 용도인지 확인",
            "임대차계약서 특약: 권리금 회수기회 방해 금지 조항 반영",
            "사업자등록 + 점유 + 확정일자 확보로 대항력 요건 충족",
            "보증금 반환보증 및 원상복구 조건(범위/단가) 명시",
        ]

        actions = [
            "계약 전 3개 이상 유사 매물의 보증금/월세 비교",
            "권리금은 거래내역·시설 목록·감가상각을 근거로 협상",
            "임대료 인상 조항은 연 5% 이내로 캡 설정",
        ]
        if not protected:
            actions.insert(0, "환산보증금이 보호 기준 초과: 보증금 조정 또는 다른 매물 검토")

        source = "district_estimate + " + deposit_source

        return {
            "district_code": district_code_resolved,
            "district_name": _to_str(district.get("district_name", "")),
            "industry_code": self.industry_code,
            "industry_name": self.industry_name,
            "rent_estimate": {
                "monthly_rent": monthly_rent,
                "deposit": deposit,
                "source": source,
            },
            "legal_protection": {
                "converted_deposit": converted_deposit,
                "threshold": threshold,
                "protected": protected,
                "region": normalized_region,
                "monthly_multiplier": monthly_multiplier,
                "renewal_request_years": renewal_years,
                "rent_increase_cap_rate": increase_cap,
            },
            "contract_checklist": contract_checklist,
            "actions": actions,
            "glossary": legal.get_glossary(),
            "legal_meta": legal.get_meta(),
        }


_registry: dict[str, LeaseAdvisorService] = {}


def get_lease_advisor_service(industry_code: str = DEFAULT_INDUSTRY) -> LeaseAdvisorService:
    if industry_code not in _registry:
        _registry[industry_code] = LeaseAdvisorService(industry_code=industry_code)
    return _registry[industry_code]
