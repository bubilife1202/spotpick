"""Funding planner service.

Builds a financing plan (equity/loan/grants) based on startup cost estimates
and optional ECOS-based interest rate references.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import TypedDict

import httpx
from dotenv import load_dotenv

from config.industry_config import DEFAULT_INDUSTRY

from api.services.simulation_service import get_simulation_service
from api.services.support_program_service import SupportProgramService, get_support_program_service


_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")


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


class InterestReference(TypedDict, total=False):
    rate: float
    source: str
    as_of: str
    note: str


class FundingSplit(TypedDict):
    equity: int
    loan: int
    grants: int
    gap: int


class LoanPlan(TypedDict, total=False):
    principal: int
    annual_rate: float
    term_months: int
    monthly_payment: int
    interest_total_estimate: int


class FundingPlan(TypedDict):
    district_code: str
    industry_code: str
    area_pyeong: int
    startup_cost_total: int
    startup_cost_range: dict[str, int]
    interest_reference: InterestReference
    split: FundingSplit
    loan_plan: LoanPlan
    support_programs: list[dict[str, object]]
    actions: list[str]


def _annuity_monthly_payment(principal: int, annual_rate: float, term_months: int) -> int:
    if principal <= 0 or term_months <= 0:
        return 0

    r = annual_rate / 12.0
    if r <= 0:
        return int(principal / term_months)

    factor = (r * (1 + r) ** term_months) / ((1 + r) ** term_months - 1)
    return int(principal * factor)


def _fetch_ecos_base_rate() -> InterestReference:
    key = os.getenv("ECOS_API_KEY", "")
    if not key:
        return {"rate": 0.0, "source": "ECOS", "note": "ECOS_API_KEY 미설정"}

    try:
        now = datetime.now()
        start = f"{now.year - 1}01"
        end = f"{now.year}12"

        url = f"https://ecos.bok.or.kr/api/StatisticSearch/{key}/JSON/kr/1/5/722Y001/M/{start}/{end}/0101000"
        r = httpx.get(url, timeout=8)
        payload = r.json() if r.status_code == 200 else {}

        rows = (
            payload.get("StatisticSearch", {}).get("row", []) if isinstance(payload, dict) else []
        )
        if not isinstance(rows, list) or not rows:
            return {"rate": 0.0, "source": "ECOS", "note": "기준금리 조회 실패"}

        last = rows[-1] if isinstance(rows[-1], dict) else {}
        value = last.get("DATA_VALUE", 0)
        time = last.get("TIME", "")
        rate_percent = _to_float(value, 0.0)

        return {
            "rate": rate_percent / 100.0,
            "source": "ECOS 722Y001",
            "as_of": str(time),
            "note": "기준금리 (연)",
        }
    except Exception:
        return {"rate": 0.0, "source": "ECOS", "note": "기준금리 조회 예외"}


class FundingPlannerService:
    def __init__(self, industry_code: str = DEFAULT_INDUSTRY) -> None:
        self.industry_code: str = industry_code
        self.support_service: SupportProgramService = get_support_program_service(industry_code)

    async def plan(
        self,
        district_code: str,
        area_pyeong: int = 10,
        equity: int | None = None,
        loan: int | None = None,
        grants: int | None = None,
        annual_rate: float | None = None,
        term_months: int = 36,
        use_ecos: bool = True,
    ) -> FundingPlan | None:
        simulation_obj = await get_simulation_service(self.industry_code).simulate(
            district_code=district_code,
            area_pyeong=area_pyeong,
        )
        if simulation_obj is None or not isinstance(simulation_obj, dict):
            return None
        simulation = simulation_obj

        startup_cost_obj = simulation.get("startup_cost", {})
        startup_cost = startup_cost_obj if isinstance(startup_cost_obj, dict) else {}
        total_min = _to_int(startup_cost.get("total_min", 0), 0)
        total_max = _to_int(startup_cost.get("total_max", 0), 0)
        startup_total = total_max if total_max > 0 else total_min

        # Interest reference
        interest_reference: InterestReference
        if annual_rate is not None and annual_rate > 0:
            interest_reference = {
                "rate": float(annual_rate),
                "source": "user_input",
                "note": "연 이자율(사용자 입력)",
            }
        elif use_ecos:
            interest_reference = _fetch_ecos_base_rate()
        else:
            interest_reference = {"rate": 0.034, "source": "default", "note": "기본 금리"}

        rate = float(interest_reference.get("rate", 0.034) or 0.034)
        if rate <= 0:
            rate = 0.034

        # Funding split
        equity_val = equity if equity is not None and equity >= 0 else int(startup_total * 0.6)
        grants_val = grants if grants is not None and grants >= 0 else int(startup_total * 0.1)
        loan_val = (
            loan
            if loan is not None and loan >= 0
            else max(0, startup_total - equity_val - grants_val)
        )
        gap = startup_total - (equity_val + grants_val + loan_val)

        monthly_payment = _annuity_monthly_payment(loan_val, rate, term_months)
        interest_total = max(0, (monthly_payment * term_months) - loan_val)

        programs = self.support_service.get_matched_programs(
            district=None,
            budget_min=None,
            budget_max=None,
            target_age=None,
            program_type=None,
        )
        support_programs: list[dict[str, object]] = []
        for row in programs[:10]:
            if isinstance(row, dict):
                support_programs.append({str(k): v for k, v in row.items() if isinstance(k, str)})

        actions = [
            "총 창업비용(최대치 기준)을 먼저 확정하고, 부족분만 대출로 채우는 구조를 유지",
            "정책자금/지원사업은 접수 마감일 기준으로 2주 전부터 준비 (서류 누락 방지)",
            "월 상환액이 예상 순이익의 30%를 넘으면 임대료/인테리어/면적을 재조정",
        ]
        if gap != 0:
            actions.insert(
                0, "자금 분배 합계가 총 필요자금과 불일치: equity/loan/grants 입력값 점검"
            )

        return {
            "district_code": district_code,
            "industry_code": self.industry_code,
            "area_pyeong": area_pyeong,
            "startup_cost_total": startup_total,
            "startup_cost_range": {"total_min": total_min, "total_max": total_max},
            "interest_reference": interest_reference,
            "split": {
                "equity": int(equity_val),
                "loan": int(loan_val),
                "grants": int(grants_val),
                "gap": int(gap),
            },
            "loan_plan": {
                "principal": int(loan_val),
                "annual_rate": float(rate),
                "term_months": int(term_months),
                "monthly_payment": int(monthly_payment),
                "interest_total_estimate": int(interest_total),
            },
            "support_programs": support_programs,
            "actions": actions,
        }


_registry: dict[str, FundingPlannerService] = {}


def get_funding_planner_service(industry_code: str = DEFAULT_INDUSTRY) -> FundingPlannerService:
    if industry_code not in _registry:
        _registry[industry_code] = FundingPlannerService(industry_code=industry_code)
    return _registry[industry_code]
