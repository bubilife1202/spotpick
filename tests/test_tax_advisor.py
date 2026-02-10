from __future__ import annotations

from importlib import import_module
from typing import Callable, Protocol, cast

from fastapi.testclient import TestClient

from api.app import create_app


class _DataServiceProto(Protocol):
    districts: list[dict[str, object]]


class _TaxServiceProto(Protocol):
    data_service: _DataServiceProto

    def analyze(
        self, district_code: str, monthly_revenue_override: int | None = None
    ) -> object: ...


def _get_tax_service_factory() -> Callable[[str], _TaxServiceProto]:
    module = import_module("api.services.tax_advisor_service")
    factory = getattr(module, "get_tax_advisor_service", None)
    assert callable(factory)
    return cast(Callable[[str], _TaxServiceProto], factory)


def _pick_district_code() -> str:
    service = _get_tax_service_factory()("CS100010")
    assert service.data_service.districts
    code = service.data_service.districts[0].get("district_code")
    assert isinstance(code, str) and code
    return code


def _as_dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_tax_advisor_service_returns_structured_payload() -> None:
    service = _get_tax_service_factory()("CS100010")
    code = _pick_district_code()

    result_obj = service.analyze(code)
    assert result_obj is not None
    result = _as_dict(result_obj)

    assert result["district_code"] == code

    tax_regime = _as_dict(result["tax_regime"])
    assert tax_regime["regime"] in ("simplified", "general")

    vat = _as_dict(result["vat"])
    vat_payable = vat.get("annual_estimated_payable_vat")
    assert isinstance(vat_payable, int) and vat_payable >= 0

    revenue_basis = _as_dict(result["revenue_basis"])
    annual = revenue_basis.get("annual_revenue")
    monthly = revenue_basis.get("monthly_revenue")
    assert isinstance(annual, int) and isinstance(monthly, int)
    assert annual == monthly * 12


def test_tax_advisor_service_uses_override_revenue() -> None:
    service = _get_tax_service_factory()("CS100010")
    code = _pick_district_code()

    result_obj = service.analyze(code, monthly_revenue_override=8_000_000)
    assert result_obj is not None
    result = _as_dict(result_obj)
    revenue_basis = _as_dict(result["revenue_basis"])
    assert revenue_basis["monthly_revenue"] == 8_000_000
    assert revenue_basis["source"] == "user_input"


def test_tax_route_returns_200() -> None:
    app = create_app()
    client = TestClient(app)
    code = _pick_district_code()

    resp = client.get(
        "/api/v1/tax/advice",
        params={"industry_code": "CS100010", "district_code": code},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["district_code"] == code
    assert "tax_regime" in payload
