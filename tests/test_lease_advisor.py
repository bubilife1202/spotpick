from __future__ import annotations

from importlib import import_module
from typing import Callable, Protocol, cast

from fastapi.testclient import TestClient

from api.app import create_app


class _DataServiceProto(Protocol):
    districts: list[dict[str, object]]


class _LeaseServiceProto(Protocol):
    data_service: _DataServiceProto

    def analyze(
        self,
        district_code: str,
        region: str = "seoul",
        monthly_rent_override: int | None = None,
        deposit_override: int | None = None,
    ) -> object: ...


def _get_lease_service_factory() -> Callable[[str], _LeaseServiceProto]:
    module = import_module("api.services.lease_advisor_service")
    factory = getattr(module, "get_lease_advisor_service", None)
    assert callable(factory)
    return cast(Callable[[str], _LeaseServiceProto], factory)


def _pick_district_code() -> str:
    service = _get_lease_service_factory()("CS100010")
    assert service.data_service.districts
    code = service.data_service.districts[0].get("district_code")
    assert isinstance(code, str) and code
    return code


def _as_dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_lease_service_returns_structured_payload() -> None:
    service = _get_lease_service_factory()("CS100010")
    code = _pick_district_code()

    result_obj = service.analyze(code)
    assert result_obj is not None
    result = _as_dict(result_obj)

    assert result["district_code"] == code

    legal = _as_dict(result["legal_protection"])
    assert isinstance(legal.get("protected"), bool)
    converted = legal.get("converted_deposit")
    threshold = legal.get("threshold")
    assert isinstance(converted, int) and isinstance(threshold, int)


def test_lease_service_override_values_apply() -> None:
    service = _get_lease_service_factory()("CS100010")
    code = _pick_district_code()

    result_obj = service.analyze(code, monthly_rent_override=2_000_000, deposit_override=40_000_000)
    assert result_obj is not None
    result = _as_dict(result_obj)
    rent = _as_dict(result["rent_estimate"])
    assert rent["monthly_rent"] == 2_000_000
    assert rent["deposit"] == 40_000_000


def test_lease_route_returns_200() -> None:
    app = create_app()
    client = TestClient(app)
    code = _pick_district_code()

    resp = client.get(
        "/api/v1/lease/advice",
        params={"industry_code": "CS100010", "district_code": code, "region": "seoul"},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["district_code"] == code
    assert "legal_protection" in payload
