from __future__ import annotations

from importlib import import_module
from typing import Callable, Protocol, cast

from fastapi.testclient import TestClient

from api.app import create_app


class _DataServiceProto(Protocol):
    districts: list[dict[str, object]]


class _LaborServiceProto(Protocol):
    data_service: _DataServiceProto

    def analyze(
        self,
        district_code: str,
        employee_plan: str | None = None,
        custom_headcount: int | None = None,
        monthly_revenue_override: int | None = None,
    ) -> object: ...


def _get_labor_service_factory() -> Callable[[str], _LaborServiceProto]:
    module = import_module("api.services.labor_advisor_service")
    factory = getattr(module, "get_labor_advisor_service", None)
    assert callable(factory)
    return cast(Callable[[str], _LaborServiceProto], factory)


def _pick_district_code() -> str:
    service = _get_labor_service_factory()("CS100010")
    assert service.data_service.districts
    code = service.data_service.districts[0].get("district_code")
    assert isinstance(code, str) and code
    return code


def _as_dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_labor_service_returns_structured_payload() -> None:
    service = _get_labor_service_factory()("CS100010")
    code = _pick_district_code()

    result_obj = service.analyze(code, employee_plan="1-2")
    assert result_obj is not None
    result = _as_dict(result_obj)

    assert result["district_code"] == code

    labor_plan = _as_dict(result["labor_plan"])
    assert labor_plan["employee_count"] == 2

    benchmark = _as_dict(result["labor_benchmark"])
    ratio = benchmark.get("recommended_labor_ratio")
    assert isinstance(ratio, float) and ratio > 0


def test_labor_service_custom_headcount_applies() -> None:
    service = _get_labor_service_factory()("CS100010")
    code = _pick_district_code()

    result_obj = service.analyze(code, custom_headcount=4)
    assert result_obj is not None
    result = _as_dict(result_obj)
    labor_plan = _as_dict(result["labor_plan"])
    assert labor_plan["employee_count"] == 4


def test_labor_route_returns_200() -> None:
    app = create_app()
    client = TestClient(app)
    code = _pick_district_code()

    resp = client.get(
        "/api/v1/labor/advice",
        params={"industry_code": "CS100010", "district_code": code, "employee_plan": "solo"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["district_code"] == code
    assert "labor_plan" in payload
