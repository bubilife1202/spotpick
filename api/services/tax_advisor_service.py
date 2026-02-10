"""Tax advisor service for startup planning."""

from __future__ import annotations

from typing import TypedDict, cast

from config.industry_config import DEFAULT_INDUSTRY, load_industry_config

from api.services.data_service import DataService, get_data_service
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


class RevenueBasis(TypedDict):
    monthly_revenue: int
    annual_revenue: int
    source: str


class TaxRegime(TypedDict):
    regime: str
    threshold_won: int
    reason: str


class VatEstimate(TypedDict):
    vat_rate: float
    annual_output_vat: int
    annual_input_vat_credit: int
    annual_estimated_payable_vat: int
    exempt: bool
    exempt_threshold_won: int


class TaxAdvice(TypedDict):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    revenue_basis: RevenueBasis
    tax_regime: TaxRegime
    vat: VatEstimate
    filing_calendar: list[dict[str, object]]
    actions: list[str]
    glossary: dict[str, str]
    legal_meta: dict[str, object]


class TaxAdvisorService:
    def __init__(
        self,
        industry_code: str = DEFAULT_INDUSTRY,
        data_service: DataService | None = None,
    ) -> None:
        self.industry_code: str = industry_code
        self.data_service: DataService = data_service or get_data_service(industry_code)

        cfg_raw = load_industry_config(industry_code)
        cfg: dict[str, object] = {
            str(k): v for k, v in cast(dict[object, object], cfg_raw).items() if isinstance(k, str)
        }
        name_val = cfg.get("display_name", cfg.get("name", "업종"))
        self.industry_name: str = str(name_val)
        self._cogs_ratio: float = _to_float(cfg.get("COGS_RATIO", 0.3), 0.3)

    def analyze(
        self,
        district_code: str,
        monthly_revenue_override: int | None = None,
    ) -> TaxAdvice | None:
        district = self.data_service.get_district(district_code)
        if district is None:
            district = self.data_service.get_district_by_name(district_code)
        if district is None:
            return None

        store_count = max(1, int(district.get("store_count", 1) or 1))
        district_monthly = int(district.get("monthly_sales", 0) or 0) // store_count
        if monthly_revenue_override is not None and monthly_revenue_override > 0:
            monthly_revenue = int(monthly_revenue_override)
            revenue_source = "user_input"
        else:
            monthly_revenue = district_monthly
            revenue_source = "district_per_store"
        annual_revenue = monthly_revenue * 12

        legal = get_legal_reference_service()
        tax_rules = legal.get_tax_rules()
        meta = legal.get_meta()

        simplified_threshold = _to_int(
            tax_rules.get("simplified_taxpayer_threshold_won", 104_000_000),
            104_000_000,
        )
        exemption_threshold = _to_int(
            tax_rules.get("vat_exemption_threshold_won", 48_000_000),
            48_000_000,
        )
        vat_rate = _to_float(tax_rules.get("vat_rate", 0.1), 0.1)

        regime = "simplified" if annual_revenue <= simplified_threshold else "general"
        regime_reason = (
            f"연매출 {annual_revenue:,}원 <= 간이과세 기준 {simplified_threshold:,}원"
            if regime == "simplified"
            else f"연매출 {annual_revenue:,}원 > 간이과세 기준 {simplified_threshold:,}원"
        )

        output_vat = int(annual_revenue * vat_rate)
        input_credit = int(annual_revenue * self._cogs_ratio * vat_rate)

        exempt = regime == "simplified" and annual_revenue <= exemption_threshold
        if exempt:
            payable = 0
        elif regime == "simplified":
            # 간이과세 추정: 업종별 실제 부가율은 상이하므로 보수적으로 2% 유효세율 사용
            payable = int(annual_revenue * 0.02)
        else:
            payable = max(0, output_vat - input_credit)

        filing_calendar_raw = tax_rules.get("filing_calendar", [])
        filing_calendar: list[dict[str, object]] = []
        if isinstance(filing_calendar_raw, list):
            for row_obj in cast(list[object], filing_calendar_raw):
                if not isinstance(row_obj, dict):
                    continue
                row: dict[str, object] = {
                    str(k): v
                    for k, v in cast(dict[object, object], row_obj).items()
                    if isinstance(k, str)
                }
                raw_months = row.get("typical_months", [])
                months: list[str] = []
                if isinstance(raw_months, list):
                    for m in cast(list[object], raw_months):
                        if isinstance(m, (str, int)):
                            months.append(str(m))
                filing_calendar.append(
                    {
                        "name": _to_str(row.get("name", "")),
                        "period": _to_str(row.get("period", "")),
                        "typical_months": months,
                    }
                )

        actions = [
            "사업 개시 전 사업자등록(업종/사업장 주소) 완료",
            "간이/일반 과세유형 확인 후 세금계산서/현금영수증 발행 정책 설정",
            "부가가치세/종합소득세 신고 캘린더를 캘린더 앱에 등록",
            "월별 매출-비용 장부를 분리 관리해 실제 세액과 추정세액 오차를 축소",
        ]

        district_code_value = cast(object, district.get("district_code", district_code))
        district_name_value = cast(object, district.get("district_name", ""))

        return {
            "district_code": _to_str(district_code_value, district_code),
            "district_name": _to_str(district_name_value),
            "industry_code": self.industry_code,
            "industry_name": self.industry_name,
            "revenue_basis": {
                "monthly_revenue": monthly_revenue,
                "annual_revenue": annual_revenue,
                "source": revenue_source,
            },
            "tax_regime": {
                "regime": regime,
                "threshold_won": simplified_threshold,
                "reason": regime_reason,
            },
            "vat": {
                "vat_rate": vat_rate,
                "annual_output_vat": output_vat,
                "annual_input_vat_credit": input_credit,
                "annual_estimated_payable_vat": payable,
                "exempt": exempt,
                "exempt_threshold_won": exemption_threshold,
            },
            "filing_calendar": filing_calendar,
            "actions": actions,
            "glossary": legal.get_glossary(),
            "legal_meta": meta,
        }


_registry: dict[str, TaxAdvisorService] = {}


def get_tax_advisor_service(industry_code: str = DEFAULT_INDUSTRY) -> TaxAdvisorService:
    if industry_code not in _registry:
        _registry[industry_code] = TaxAdvisorService(industry_code=industry_code)
    return _registry[industry_code]
