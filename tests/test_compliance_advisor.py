from __future__ import annotations

from importlib import import_module
from typing import Callable, Protocol, cast

from fastapi.testclient import TestClient

from api.app import create_app


class _DataServiceProto(Protocol):
    districts: list[dict[str, object]]


class _ComplianceServiceProto(Protocol):
    data_service: _DataServiceProto

    def analyze(
        self,
        district_code: str,
        sigungu_cd: str | None = None,
        bjdong_cd: str | None = None,
    ) -> object: ...


def _get_service_factory() -> Callable[[str], _ComplianceServiceProto]:
    module = import_module("api.services.compliance_advisor_service")
    factory = getattr(module, "get_compliance_advisor_service", None)
    assert callable(factory)
    return cast(Callable[[str], _ComplianceServiceProto], factory)


def _pick_district_code() -> str:
    service = _get_service_factory()("CS100010")
    assert service.data_service.districts
    code = service.data_service.districts[0].get("district_code")
    assert isinstance(code, str) and code
    return code


def _as_dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_compliance_service_returns_permits() -> None:
    service = _get_service_factory()("CS100010")
    code = _pick_district_code()

    result_obj = service.analyze(code)
    assert result_obj is not None
    result = _as_dict(result_obj)

    assert result["district_code"] == code
    permits = result.get("permits")
    assert isinstance(permits, list) and len(permits) > 0
    assert isinstance(result.get("permit_cost_total"), int)


def test_compliance_service_pending_building_check_without_codes() -> None:
    service = _get_service_factory()("CS100010")
    code = _pick_district_code()

    result_obj = service.analyze(code)
    assert result_obj is not None
    result = _as_dict(result_obj)
    building = _as_dict(result["building_check"])
    assert building["status"] in ("pending", "ok", "error", "unknown", "unavailable")


def test_compliance_route_returns_200() -> None:
    app = create_app()
    client = TestClient(app)
    code = _pick_district_code()

    resp = client.get(
        "/api/v1/compliance/advice",
        params={"industry_code": "CS100010", "district_code": code},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["district_code"] == code
    assert "permits" in payload
