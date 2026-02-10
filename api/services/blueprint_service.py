"""Startup blueprint service aggregating strategy and advisor outputs."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TypedDict, cast

from config.industry_config import DEFAULT_INDUSTRY, load_industry_config

from api.services.compliance_advisor_service import get_compliance_advisor_service
from api.services.data_service import DataService, get_data_service
from api.services.labor_advisor_service import get_labor_advisor_service
from api.services.lease_advisor_service import get_lease_advisor_service
from api.services.simulation_service import get_simulation_service
from api.services.tax_advisor_service import get_tax_advisor_service


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


class BlueprintResult(TypedDict):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    concept_title: str
    recommended_business_type: str
    operation_model: dict[str, object]
    menu_strategy: dict[str, object]
    pricing_strategy: dict[str, object]
    launch_plan: list[dict[str, object]]
    financial_targets: dict[str, object]
    advisor_snapshots: dict[str, object]


def _select_business_type(
    business_types: list[dict[str, object]],
    district: dict[str, object],
    employee_count: str | None,
) -> dict[str, object] | None:
    if not business_types:
        return None

    if employee_count == "solo":
        for item in business_types:
            label = _to_str(item.get("label", "")).lower()
            if "테이크" in label or "take" in label:
                return item

    worker_total = _to_int(district.get("worker_total", 0), 0)
    if worker_total > 4000:
        for item in business_types:
            label = _to_str(item.get("label", "")).lower()
            if "브런치" in label or "take" in label:
                return item

    district_type = _to_str(district.get("district_type", ""))
    if district_type == "골목상권":
        for item in business_types:
            label = _to_str(item.get("label", "")).lower()
            if "감성" in label or "동네" in label:
                return item

    return business_types[0]


def _extract_menu_strategy(cfg: dict[str, object]) -> dict[str, object]:
    menu_raw = cfg.get("MENU_COSTS", {})
    if not isinstance(menu_raw, dict):
        return {
            "top_margin_items": [],
            "low_margin_items": [],
            "avg_margin_rate": 0.0,
            "recommended_bundle": "",
        }

    scored: list[dict[str, object]] = []
    for name_obj, row_obj in cast(dict[object, object], menu_raw).items():
        if not isinstance(name_obj, str) or not isinstance(row_obj, dict):
            continue
        row = cast(dict[object, object], row_obj)
        price = _to_int(row.get("selling_price", 0), 0)
        cost = _to_int(row.get("total_cost", 0), 0)
        if price <= 0:
            continue
        margin_rate = (price - cost) / price
        category = _to_str(row.get("category", "기타"), "기타")
        scored.append(
            {
                "name": name_obj,
                "category": category,
                "selling_price": price,
                "total_cost": cost,
                "margin_rate": round(margin_rate, 4),
            }
        )

    if not scored:
        return {
            "top_margin_items": [],
            "low_margin_items": [],
            "avg_margin_rate": 0.0,
            "recommended_bundle": "",
        }

    scored_sorted = sorted(
        scored, key=lambda x: _to_float(x.get("margin_rate", 0.0), 0.0), reverse=True
    )
    top_margin = scored_sorted[:3]
    low_margin = list(reversed(scored_sorted[-2:]))
    avg_margin = sum(_to_float(s.get("margin_rate", 0.0), 0.0) for s in scored_sorted) / len(
        scored_sorted
    )

    best_name = _to_str(top_margin[0].get("name", "")) if top_margin else ""
    low_name = _to_str(low_margin[0].get("name", "")) if low_margin else ""
    bundle = f"{best_name} + {low_name} 세트로 객단가 상승 유도" if best_name and low_name else ""

    return {
        "top_margin_items": top_margin,
        "low_margin_items": low_margin,
        "avg_margin_rate": round(avg_margin, 4),
        "recommended_bundle": bundle,
    }


def _build_launch_plan() -> list[dict[str, object]]:
    today = date.today()
    return [
        {
            "phase": "Phase 1",
            "name": "사업 설계",
            "target_date": str(today + timedelta(days=7)),
            "deliverables": ["운영형태 확정", "핵심 메뉴 확정", "목표 객단가 확정"],
        },
        {
            "phase": "Phase 2",
            "name": "자금 계획",
            "target_date": str(today + timedelta(days=14)),
            "deliverables": ["초기투자비 확정", "대출/지원금 구조 설계", "월 상환가능액 확인"],
        },
        {
            "phase": "Phase 3",
            "name": "세금·노무",
            "target_date": str(today + timedelta(days=21)),
            "deliverables": ["과세유형 확정", "인건비 체계 확정", "4대보험 준비"],
        },
        {
            "phase": "Phase 4",
            "name": "계약·인허가",
            "target_date": str(today + timedelta(days=28)),
            "deliverables": ["건축물대장 용도확인", "임대차 계약", "영업신고"],
        },
        {
            "phase": "Phase 5",
            "name": "오픈 준비",
            "target_date": str(today + timedelta(days=35)),
            "deliverables": ["인테리어/설비 완료", "마케팅 세팅", "프리오픈"],
        },
    ]


class BlueprintService:
    def __init__(
        self,
        industry_code: str = DEFAULT_INDUSTRY,
        data_service: DataService | None = None,
    ) -> None:
        self.industry_code: str = industry_code
        self.data_service: DataService = data_service or get_data_service(industry_code)
        cfg_raw = load_industry_config(industry_code)
        self.cfg: dict[str, object] = {
            str(k): v for k, v in cast(dict[object, object], cfg_raw).items() if isinstance(k, str)
        }
        self.industry_name: str = _to_str(
            self.cfg.get("display_name", self.cfg.get("name", "업종")),
            "업종",
        )

    async def generate(
        self,
        district_code: str,
        budget_man: int,
        experience_level: str | None = None,
        employee_count: str | None = None,
        area_pyeong: int = 10,
    ) -> BlueprintResult | None:
        district = self.data_service.get_district(district_code)
        if district is None:
            district = self.data_service.get_district_by_name(district_code)
        if district is None:
            return None

        simulation_obj = await get_simulation_service(self.industry_code).simulate(
            district_code=_to_str(district.get("district_code", district_code), district_code),
            area_pyeong=area_pyeong,
        )
        if simulation_obj is None:
            return None
        simulation = cast(dict[str, object], cast(object, simulation_obj))

        business_types_raw = self.cfg.get("BUSINESS_TYPES", [])
        business_types = (
            cast(list[object], business_types_raw) if isinstance(business_types_raw, list) else []
        )
        selected_type = _select_business_type(
            business_types=[
                cast(dict[str, object], v) for v in business_types if isinstance(v, dict)
            ],
            district=district,
            employee_count=employee_count,
        )

        menu_strategy = _extract_menu_strategy(self.cfg)

        tax = get_tax_advisor_service(self.industry_code).analyze(
            district_code=_to_str(district.get("district_code", district_code), district_code)
        )
        labor = get_labor_advisor_service(self.industry_code).analyze(
            district_code=_to_str(district.get("district_code", district_code), district_code),
            employee_plan=employee_count,
        )
        lease = get_lease_advisor_service(self.industry_code).analyze(
            district_code=_to_str(district.get("district_code", district_code), district_code)
        )
        compliance = get_compliance_advisor_service(self.industry_code).analyze(
            district_code=_to_str(district.get("district_code", district_code), district_code)
        )

        revenue_obj = simulation.get("revenue", {})
        revenue = cast(dict[str, object], revenue_obj if isinstance(revenue_obj, dict) else {})
        avg_ticket = _to_int(revenue.get("avg_ticket", 0), 0)
        suggested_ticket = int(avg_ticket * (1.05 if experience_level == "expert" else 1.0))

        operation_model: dict[str, object] = {
            "experience_level": experience_level or "unknown",
            "employee_count": employee_count or "unknown",
            "recommended_business_type": selected_type or {},
            "suggested_opening_hours": "08:00-22:00" if employee_count != "solo" else "09:00-21:00",
            "focus": "회전율 중심 운영"
            if employee_count == "solo"
            else "객단가+체류시간 복합 운영",
        }

        pricing_strategy: dict[str, object] = {
            "current_avg_ticket": avg_ticket,
            "target_avg_ticket": suggested_ticket,
            "suggestion": "고마진 음료+저마진 푸드 세트로 객단가를 5~10% 상향",
        }

        startup_cost_obj = simulation.get("startup_cost", {})
        startup_cost = cast(
            dict[str, object], startup_cost_obj if isinstance(startup_cost_obj, dict) else {}
        )
        break_even_obj = simulation.get("break_even", {})
        break_even = cast(
            dict[str, object], break_even_obj if isinstance(break_even_obj, dict) else {}
        )

        financial_targets: dict[str, object] = {
            "budget_man": budget_man,
            "startup_total_min": _to_int(startup_cost.get("total_min", 0), 0),
            "startup_total_max": _to_int(startup_cost.get("total_max", 0), 0),
            "monthly_sales_target": _to_int(revenue.get("monthly_sales_per_store", 0), 0),
            "monthly_net_profit_target": _to_int(break_even.get("monthly_net_profit", 0), 0),
            "break_even_months": _to_int(break_even.get("break_even_months_max", 0), 0),
        }

        advisor_snapshots: dict[str, object] = {
            "tax": tax or {},
            "labor": labor or {},
            "lease": lease or {},
            "compliance": compliance or {},
        }

        district_name = _to_str(district.get("district_name", ""))
        concept_title = f"{district_name} {self.industry_name} 실행 설계서"

        result: BlueprintResult = {
            "district_code": _to_str(district.get("district_code", district_code), district_code),
            "district_name": district_name,
            "industry_code": self.industry_code,
            "industry_name": self.industry_name,
            "concept_title": concept_title,
            "recommended_business_type": _to_str(
                (selected_type or {}).get("label", "기본형"), "기본형"
            ),
            "operation_model": operation_model,
            "menu_strategy": menu_strategy,
            "pricing_strategy": pricing_strategy,
            "launch_plan": _build_launch_plan(),
            "financial_targets": financial_targets,
            "advisor_snapshots": advisor_snapshots,
        }
        return result


_registry: dict[str, BlueprintService] = {}


def get_blueprint_service(industry_code: str = DEFAULT_INDUSTRY) -> BlueprintService:
    if industry_code not in _registry:
        _registry[industry_code] = BlueprintService(industry_code=industry_code)
    return _registry[industry_code]
