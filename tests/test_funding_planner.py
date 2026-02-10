from __future__ import annotations

import asyncio
from importlib import import_module
from typing import Callable, Protocol, cast

from fastapi.testclient import TestClient

from api.app import create_app
from api.services.data_service import get_data_service


class _FundingServiceProto(Protocol):
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
    ) -> object: ...


def _get_service_factory() -> Callable[[str], _FundingServiceProto]:
    module = import_module("api.services.funding_planner_service")
    factory = getattr(module, "get_funding_planner_service", None)
    assert callable(factory)
    return cast(Callable[[str], _FundingServiceProto], factory)


def _pick_district_code() -> str:
    ds = get_data_service("CS100010")
    assert ds.districts
    code = ds.districts[0].get("district_code")
    assert isinstance(code, str) and code
    return code


def _as_dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_funding_service_returns_payload_with_override_rate() -> None:
    service = _get_service_factory()("CS100010")
    code = _pick_district_code()

    result_obj = asyncio.run(
        service.plan(
            district_code=code,
            area_pyeong=10,
            equity=30_000_000,
            grants=5_000_000,
            annual_rate=0.034,
            term_months=36,
            use_ecos=False,
        )
    )
    assert result_obj is not None
    result = _as_dict(result_obj)
    assert result["district_code"] == code
    loan_plan = _as_dict(result["loan_plan"])
    assert isinstance(loan_plan.get("monthly_payment"), int)


def test_funding_route_returns_200_without_network() -> None:
    app = create_app()
    client = TestClient(app)
    code = _pick_district_code()

    resp = client.get(
        "/api/v1/funding/plan",
        params={
            "industry_code": "CS100010",
            "district_code": code,
            "area_pyeong": 10,
            "equity": 30_000_000,
            "grants": 5_000_000,
            "annual_rate": 0.034,
            "term_months": 36,
            "use_ecos": False,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["district_code"] == code
    assert "loan_plan" in payload
