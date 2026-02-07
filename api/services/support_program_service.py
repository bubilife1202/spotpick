"""
정부 창업 지원사업 매칭 서비스

기업마당(bizinfo.go.kr) API 또는 공공데이터포털 CSV를 활용하여
신청 가능한 창업 지원사업을 매칭합니다.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict
from dotenv import load_dotenv

from config.industry_config import DEFAULT_INDUSTRY, load_industry_config

logger = logging.getLogger(__name__)

# .env 로드
_ = load_dotenv(Path(__file__).parent.parent.parent / ".env")

BIZINFO_API_KEY = os.getenv("BIZINFO_API_KEY")


class SupportProgram(TypedDict):
    """지원사업 데이터 구조"""
    program_id: str
    program_name: str
    category: str  # 금융/기술/인력/수출/내수/창업/경영
    support_target: str
    support_amount: str
    application_start_date: str  # YYYY-MM-DD
    application_end_date: str  # YYYY-MM-DD
    managing_org: str  # 소관기관
    executing_org: str  # 수행기관
    detail_url: str
    days_until_deadline: int  # 마감 D-day


# 백업 데이터: 실제 운영 시에는 API/CSV에서 로드
# 2026년 예상 지원사업 샘플 (테스트용)
_MOCK_PROGRAMS: list[dict[str, Any]] = [
    {
        "program_id": "SP2026001",
        "program_name": "청년창업사관학교",
        "category": "창업",
        "support_target": "만 39세 이하 예비창업자",
        "support_amount": "최대 1억원 (사업화자금)",
        "application_start_date": "2026-03-01",
        "application_end_date": "2026-03-31",
        "managing_org": "중소벤처기업부",
        "executing_org": "창업진흥원",
        "detail_url": "https://www.k-startup.go.kr/",
    },
    {
        "program_id": "SP2026002",
        "program_name": "소상공인 희망리턴패키지",
        "category": "창업",
        "support_target": "재창업 소상공인",
        "support_amount": "최대 5,000만원",
        "application_start_date": "2026-02-01",
        "application_end_date": "2026-02-28",
        "managing_org": "중소벤처기업부",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
    },
    {
        "program_id": "SP2026003",
        "program_name": "서울시 청년 창업 지원",
        "category": "창업",
        "support_target": "서울시 거주 만 39세 이하",
        "support_amount": "최대 3,000만원",
        "application_start_date": "2026-02-10",
        "application_end_date": "2026-03-10",
        "managing_org": "서울시",
        "executing_org": "서울산업진흥원",
        "detail_url": "https://sba.seoul.kr/",
    },
    {
        "program_id": "SP2026004",
        "program_name": "예비창업패키지",
        "category": "창업",
        "support_target": "업력 3년 미만 예비/초기창업자",
        "support_amount": "최대 1억원",
        "application_start_date": "2026-04-01",
        "application_end_date": "2026-04-30",
        "managing_org": "중소벤처기업부",
        "executing_org": "창업진흥원",
        "detail_url": "https://www.k-startup.go.kr/",
    },
    {
        "program_id": "SP2026005",
        "program_name": "소상공인 정책자금 융자",
        "category": "금융",
        "support_target": "소상공인 (3년 이상 영업)",
        "support_amount": "최대 7,000만원 (융자)",
        "application_start_date": "2026-01-01",
        "application_end_date": "2026-12-31",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
    },
]


class SupportProgramService:
    """정부 창업 지원사업 매칭 서비스 — 업종별 인스턴스."""

    def __init__(self, industry_code: str = DEFAULT_INDUSTRY):
        self.industry_code = industry_code
        self.config = load_industry_config(industry_code)
        self.display_name = self.config.get("DISPLAY_NAME", "카페")

        # 업종별 지원사업 필터링 로직 (추후 확장 가능)
        self.target_keywords = self._get_target_keywords()

    def _get_target_keywords(self) -> list[str]:
        """업종별 타겟 키워드 추출 (지원대상 필터링용)"""
        keywords = ["예비창업자", "소상공인", "청년창업", "재창업"]

        # 업종별 추가 키워드
        industry_keywords = self.config.get("SUPPORT_KEYWORDS", [])
        if industry_keywords:
            keywords.extend(industry_keywords)

        return keywords

    def _calculate_days_until_deadline(self, end_date_str: str) -> int:
        """마감일까지 남은 일수 계산"""
        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            today = datetime.now()
            delta = end_date - today
            return delta.days
        except Exception:
            return 999  # 파싱 실패 시 큰 값 반환

    def _is_active_program(self, program: dict[str, Any]) -> bool:
        """신청 가능한 사업인지 확인 (마감일 >= 오늘)"""
        end_date_str = program.get("application_end_date", "")
        if not end_date_str:
            return False

        try:
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            today = datetime.now()
            return end_date >= today
        except Exception:
            return False

    def _load_programs_from_api(self) -> list[dict[str, Any]]:
        """기업마당 API에서 지원사업 데이터 조회 (미구현 — 추후 확장)"""
        # TODO: 실제 API 호출 구현
        # if BIZINFO_API_KEY:
        #     response = requests.get(BIZINFO_API_URL, params={...})
        #     return response.json()
        logger.warning("BIZINFO_API_KEY not configured. Using mock data.")
        return _MOCK_PROGRAMS

    def _load_programs_from_csv(self) -> list[dict[str, Any]]:
        """공공데이터포털 CSV 파싱 (미구현 — 추후 확장)"""
        # TODO: CSV 파싱 구현
        return _MOCK_PROGRAMS

    def get_active_programs(self) -> list[SupportProgram]:
        """현재 신청 가능한 전체 지원사업 목록 (마감 임박순)"""
        programs = self._load_programs_from_api()

        # 신청 마감일이 지나지 않은 것만 필터링
        active_programs = [p for p in programs if self._is_active_program(p)]

        # 마감일까지 남은 일수 계산
        for program in active_programs:
            program["days_until_deadline"] = self._calculate_days_until_deadline(
                program["application_end_date"]
            )

        # 마감 임박순 정렬 (D-day 작은 것 먼저)
        active_programs.sort(key=lambda x: x.get("days_until_deadline", 999))

        return [SupportProgram(**p) for p in active_programs]

    def get_matched_programs(
        self,
        district: str | None = None,
        budget_min: int | None = None,
        budget_max: int | None = None,
        target_age: str | None = None,
    ) -> list[SupportProgram]:
        """사용자 조건에 매칭되는 지원사업 목록 (마감 임박순)"""
        active_programs = self.get_active_programs()

        # 매칭 필터링
        matched = []
        for program in active_programs:
            # 창업 분야만 필터링
            if program.get("category") != "창업":
                continue

            # 지역 필터링 (서울시 사업만)
            if district and "서울" not in program.get("managing_org", ""):
                # 중앙정부 사업은 모두 포함
                if program.get("managing_org") not in ["중소벤처기업부", "소상공인시장진흥공단"]:
                    continue

            # 타겟 연령 필터링 (청년 = 39세 이하)
            if target_age:
                support_target = program.get("support_target", "")
                if "청년" in target_age.lower() and "39세" not in support_target:
                    continue

            matched.append(program)

        return matched


# ---------------------------------------------------------------------------
# Service Registry (멀티업종 패턴)
# ---------------------------------------------------------------------------

_registry: dict[str, SupportProgramService] = {}


def get_support_program_service(industry_code: str = DEFAULT_INDUSTRY) -> SupportProgramService:
    """Get or create SupportProgramService instance for the given industry."""
    if industry_code not in _registry:
        _registry[industry_code] = SupportProgramService(industry_code)
    return _registry[industry_code]
