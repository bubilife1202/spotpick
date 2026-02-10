from __future__ import annotations

import asyncio
from importlib import import_module
from typing import Callable, Protocol, cast

from fastapi.testclient import TestClient

from api.app import create_app


class _DataServiceProto(Protocol):
    districts: list[dict[str, object]]


class _BlueprintServiceProto(Protocol):
    data_service: _DataServiceProto

    async def generate(
        self,
        district_code: str,
        budget_man: int,
        experience_level: str | None = None,
        employee_count: str | None = None,
        area_pyeong: int = 10,
    ) -> object: ...


def _get_blueprint_service_factory() -> Callable[[str], _BlueprintServiceProto]:
    module = import_module("api.services.blueprint_service")
    factory = getattr(module, "get_blueprint_service", None)
    assert callable(factory)
    return cast(Callable[[str], _BlueprintServiceProto], factory)


def _pick_district_code() -> str:
    service = _get_blueprint_service_factory()("CS100010")
    assert service.data_service.districts
    code = service.data_service.districts[0].get("district_code")
    assert isinstance(code, str) and code
    return code


def _as_dict(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return cast(dict[str, object], value)


def test_blueprint_service_returns_structured_payload() -> None:
    service = _get_blueprint_service_factory()("CS100010")
    code = _pick_district_code()

    result_obj = asyncio.run(
        service.generate(
            district_code=code,
            budget_man=5000,
            experience_level="beginner",
            employee_count="solo",
            area_pyeong=10,
        )
    )
    assert result_obj is not None
    result = _as_dict(result_obj)

    assert result["district_code"] == code
    assert isinstance(result.get("launch_plan"), list)
    snapshots = _as_dict(result["advisor_snapshots"])
    assert (
        "tax" in snapshots
        and "labor" in snapshots
        and "lease" in snapshots
        and "compliance" in snapshots
    )


def test_blueprint_route_returns_200() -> None:
    app = create_app()
    client = TestClient(app)
    code = _pick_district_code()

    resp = client.get(
        "/api/v1/blueprint/generate",
        params={
            "industry_code": "CS100010",
            "district_code": code,
            "budget_man": 5000,
            "experience_level": "beginner",
            "employee_count": "solo",
            "area_pyeong": 10,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["district_code"] == code
    assert "advisor_snapshots" in payload
