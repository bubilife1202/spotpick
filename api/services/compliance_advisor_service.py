"""Compliance advisor service for permits and building suitability checks."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import TypedDict

import httpx
from dotenv import load_dotenv

from config.industry_config import DEFAULT_INDUSTRY, load_industry_config

from api.services.data_service import DataService, get_data_service
from api.services.legal_reference_service import get_legal_reference_service


_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")

DATA_GO_KR_API_KEY = os.getenv("DATA_GO_KR_API_KEY", "")
PERMITS_PATH = Path(__file__).parent.parent / "data" / "industry_permits.json"


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


def _to_str(value: object, default: str = "") -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def _parse_duration_days(duration_text: str) -> int:
    nums = [int(v) for v in re.findall(r"\d+", duration_text)]
    if not nums:
        return 0
    if len(nums) >= 2:
        return max(nums)
    return nums[0]


class PermitItem(TypedDict):
    order: int
    name: str
    agency: str
    duration: str
    cost: int
    required: bool


class BuildingCheck(TypedDict):
    status: str
    compatible: bool
    reason: str
    building_main_purpose: str
    usage: str
    source: str


class ComplianceAdvice(TypedDict):
    district_code: str
    district_name: str
    industry_code: str
    industry_name: str
    permits: list[PermitItem]
    permit_cost_total: int
    permit_duration_days: int
    building_check: BuildingCheck
    notes: list[str]
    actions: list[str]
    glossary: dict[str, str]
    legal_meta: dict[str, object]


def _load_permits() -> dict[str, object]:
    if not PERMITS_PATH.exists():
        return {}
    try:
        with open(PERMITS_PATH, encoding="utf-8") as f:
            payload = json.load(f)
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _fetch_building_check(sigungu_cd: str, bjdong_cd: str) -> BuildingCheck:
    if not DATA_GO_KR_API_KEY:
        return {
            "status": "unavailable",
            "compatible": False,
            "reason": "DATA_GO_KR_API_KEY 미설정",
            "building_main_purpose": "",
            "usage": "",
            "source": "건축물대장 API",
        }

    try:
        r = httpx.get(
            "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo",
            params={
                "serviceKey": DATA_GO_KR_API_KEY,
                "sigunguCd": sigungu_cd,
                "bjdongCd": bjdong_cd,
                "platGbCd": "0",
                "numOfRows": 1,
                "pageNo": 1,
                "_type": "json",
            },
            timeout=8,
        )
        payload = r.json()
        body = payload.get("response", {}).get("body", {}) if isinstance(payload, dict) else {}
        items = body.get("items", {}) if isinstance(body, dict) else {}
        item_list = items.get("item", []) if isinstance(items, dict) else []

        first = None
        if isinstance(item_list, list) and item_list:
            first = item_list[0]
        elif isinstance(item_list, dict):
            first = item_list

        if not isinstance(first, dict):
            return {
                "status": "unknown",
                "compatible": False,
                "reason": "건축물대장 데이터 없음",
                "building_main_purpose": "",
                "usage": "",
                "source": "건축물대장 API",
            }

        main_purpose = _to_str(first.get("mainPurpsCdNm", ""))
        usage = _to_str(first.get("etcPurps", ""))

        compatible_keywords = ["근린생활시설", "제1종", "제2종"]
        compatible = any(k in main_purpose for k in compatible_keywords)
        reason = (
            "근린생활시설 용도 확인됨"
            if compatible
            else "근린생활시설 용도 미확인 — 용도변경/행정확인 필요"
        )

        return {
            "status": "ok",
            "compatible": compatible,
            "reason": reason,
            "building_main_purpose": main_purpose,
            "usage": usage,
            "source": "건축물대장 API",
        }
    except Exception:
        return {
            "status": "error",
            "compatible": False,
            "reason": "건축물대장 API 조회 실패",
            "building_main_purpose": "",
            "usage": "",
            "source": "건축물대장 API",
        }


class ComplianceAdvisorService:
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
        sigungu_cd: str | None = None,
        bjdong_cd: str | None = None,
    ) -> ComplianceAdvice | None:
        district = self.data_service.get_district(district_code)
        if district is None:
            district = self.data_service.get_district_by_name(district_code)
        if district is None:
            return None

        permits_data = _load_permits()
        industry_data_obj = permits_data.get(self.industry_code, {})
        industry_data = industry_data_obj if isinstance(industry_data_obj, dict) else {}

        permits_obj = industry_data.get("permits", [])
        permits_list: list[PermitItem] = []
        permit_cost_total = 0
        permit_duration_days = 0

        if isinstance(permits_obj, list):
            for row_obj in permits_obj:
                if not isinstance(row_obj, dict):
                    continue
                permit: PermitItem = {
                    "order": _to_int(row_obj.get("order", 0), 0),
                    "name": _to_str(row_obj.get("name", "")),
                    "agency": _to_str(row_obj.get("agency", "")),
                    "duration": _to_str(row_obj.get("duration", "")),
                    "cost": _to_int(row_obj.get("cost", 0), 0),
                    "required": bool(row_obj.get("required", False)),
                }
                permits_list.append(permit)
                permit_cost_total += permit["cost"]
                permit_duration_days += _parse_duration_days(permit["duration"])

        notes_obj = industry_data.get("notes", [])
        notes: list[str] = [str(v) for v in notes_obj] if isinstance(notes_obj, list) else []

        building_check: BuildingCheck
        if sigungu_cd and bjdong_cd:
            building_check = _fetch_building_check(sigungu_cd, bjdong_cd)
        else:
            building_check = {
                "status": "pending",
                "compatible": False,
                "reason": "건물 코드 미입력 — sigungu_cd, bjdong_cd 입력 시 자동 판정",
                "building_main_purpose": "",
                "usage": "",
                "source": "건축물대장 API",
            }

        legal = get_legal_reference_service()
        compliance_rules = legal.get_compliance_rules()
        hygiene_obj = compliance_rules.get("food_sanitation", {})
        hygiene = hygiene_obj if isinstance(hygiene_obj, dict) else {}

        actions: list[str] = [
            "사업자등록, 위생교육, 영업신고 순서로 인허가 일정을 고정",
            "구청 위생과/소방서 사전 방문으로 서류 누락 방지",
            "오픈 2주 전까지 필수 허가를 완료해 공사 지연 리스크 차단",
        ]
        if bool(hygiene.get("pre_opening_education_required", True)):
            actions.append("영업 전 위생교육 수료증을 영업신고 서류와 함께 보관")
        if building_check["status"] != "ok" or not building_check["compatible"]:
            actions.insert(0, "건축물대장 용도확인 완료 전 임대차 계약 확정 금지")

        district_code_resolved = _to_str(
            district.get("district_code", district_code), district_code
        )
        district_name = _to_str(district.get("district_name", ""))

        advice: ComplianceAdvice = {
            "district_code": district_code_resolved,
            "district_name": district_name,
            "industry_code": self.industry_code,
            "industry_name": self.industry_name,
            "permits": sorted(permits_list, key=lambda x: x["order"]),
            "permit_cost_total": permit_cost_total,
            "permit_duration_days": permit_duration_days,
            "building_check": building_check,
            "notes": notes,
            "actions": actions,
            "glossary": legal.get_glossary(),
            "legal_meta": legal.get_meta(),
        }
        return advice


_registry: dict[str, ComplianceAdvisorService] = {}


def get_compliance_advisor_service(
    industry_code: str = DEFAULT_INDUSTRY,
) -> ComplianceAdvisorService:
    if industry_code not in _registry:
        _registry[industry_code] = ComplianceAdvisorService(industry_code=industry_code)
    return _registry[industry_code]
