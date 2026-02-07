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
    program_type: str  # 대출/보조금/컨설팅/기술지원
    max_amount_man: int  # 최대 지원금액 (만원, 0=미정)
    industry_filter: list[str]  # 적용 업종 코드 목록, ["all"]이면 전 업종


# 백업 데이터: 실제 운영 시에는 API/CSV에서 로드
# 2026년 예상 지원사업 샘플 — 실제 한국 정부/지자체 지원사업 기반
_MOCK_PROGRAMS: list[dict[str, Any]] = [
    {
        "program_id": "SP2026001",
        "program_name": "소상공인 정책자금 (직접대출)",
        "category": "금융",
        "support_target": "소상공인 (업력 무관)",
        "support_amount": "최대 7,000만원 (연 2~3.5%)",
        "application_start_date": "2026-01-02",
        "application_end_date": "2026-11-28",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/sup/policy/fund/direct.do",
        "program_type": "대출",
        "max_amount_man": 7000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026002",
        "program_name": "소상공인 정책자금 (대리대출)",
        "category": "금융",
        "support_target": "소상공인 (업력 무관)",
        "support_amount": "최대 7,000만원 (시중은행 경유)",
        "application_start_date": "2026-01-02",
        "application_end_date": "2026-11-28",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "시중은행",
        "detail_url": "https://www.sbiz.or.kr/sup/policy/fund/agent.do",
        "program_type": "대출",
        "max_amount_man": 7000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026003",
        "program_name": "청년창업사관학교",
        "category": "창업",
        "support_target": "만 39세 이하 예비창업자",
        "support_amount": "최대 1억원 (사업화자금+교육)",
        "application_start_date": "2026-03-01",
        "application_end_date": "2026-03-31",
        "managing_org": "중소벤처기업부",
        "executing_org": "창업진흥원",
        "detail_url": "https://www.k-startup.go.kr/",
        "program_type": "보조금",
        "max_amount_man": 10000,
        "industry_filter": ["all"],
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
        "program_type": "보조금",
        "max_amount_man": 10000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026005",
        "program_name": "초기창업패키지",
        "category": "창업",
        "support_target": "업력 3년 이내 초기창업자",
        "support_amount": "최대 1억원",
        "application_start_date": "2026-04-15",
        "application_end_date": "2026-05-15",
        "managing_org": "중소벤처기업부",
        "executing_org": "창업진흥원",
        "detail_url": "https://www.k-startup.go.kr/",
        "program_type": "보조금",
        "max_amount_man": 10000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026006",
        "program_name": "창업도약패키지",
        "category": "창업",
        "support_target": "업력 3~7년 성장기 창업자",
        "support_amount": "최대 3억원",
        "application_start_date": "2026-05-01",
        "application_end_date": "2026-05-31",
        "managing_org": "중소벤처기업부",
        "executing_org": "창업진흥원",
        "detail_url": "https://www.k-startup.go.kr/",
        "program_type": "보조금",
        "max_amount_man": 30000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026007",
        "program_name": "서울시 소상공인 임차보증금 지원",
        "category": "금융",
        "support_target": "서울시 소재 소상공인",
        "support_amount": "최대 5,000만원 (보증금 대출)",
        "application_start_date": "2026-02-01",
        "application_end_date": "2026-06-30",
        "managing_org": "서울시",
        "executing_org": "서울신용보증재단",
        "detail_url": "https://www.seoulshinbo.co.kr/",
        "program_type": "대출",
        "max_amount_man": 5000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026008",
        "program_name": "서울시 청년 창업 지원금",
        "category": "창업",
        "support_target": "서울시 거주 만 39세 이하 예비/초기 창업자",
        "support_amount": "최대 3,000만원",
        "application_start_date": "2026-02-10",
        "application_end_date": "2026-03-10",
        "managing_org": "서울시",
        "executing_org": "서울산업진흥원",
        "detail_url": "https://sba.seoul.kr/",
        "program_type": "보조금",
        "max_amount_man": 3000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026009",
        "program_name": "소상공인 폐업희망리턴패키지",
        "category": "창업",
        "support_target": "폐업 예정 또는 재창업 희망 소상공인",
        "support_amount": "재창업 교육·컨설팅+사업정리비",
        "application_start_date": "2026-02-01",
        "application_end_date": "2026-09-30",
        "managing_org": "중소벤처기업부",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
        "program_type": "컨설팅",
        "max_amount_man": 0,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026010",
        "program_name": "신사업창업사관학교",
        "category": "창업",
        "support_target": "업종 전환·신사업 진출 예비창업자",
        "support_amount": "최대 1억원 (사업화자금+교육)",
        "application_start_date": "2026-03-15",
        "application_end_date": "2026-04-15",
        "managing_org": "중소벤처기업부",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
        "program_type": "보조금",
        "max_amount_man": 10000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026011",
        "program_name": "소상공인 디지털전환 지원",
        "category": "기술",
        "support_target": "소상공인 (업력 1년 이상)",
        "support_amount": "키오스크·POS·배달앱 등 최대 400만원",
        "application_start_date": "2026-03-01",
        "application_end_date": "2026-08-31",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
        "program_type": "기술지원",
        "max_amount_man": 400,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026012",
        "program_name": "소상공인 스마트상점 기술보급",
        "category": "기술",
        "support_target": "소상공인 (외식·소매업 우선)",
        "support_amount": "스마트오더·무인결제 등 기술도입 (현물지원)",
        "application_start_date": "2026-04-01",
        "application_end_date": "2026-07-31",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
        "program_type": "기술지원",
        "max_amount_man": 500,
        "industry_filter": [
            "CS100001", "CS100002", "CS100003", "CS100004", "CS100005",
            "CS100006", "CS100007", "CS100008", "CS100009", "CS100010",
        ],
    },
    {
        "program_id": "SP2026013",
        "program_name": "전통시장 경영혁신 지원",
        "category": "경영",
        "support_target": "전통시장 내 점포 소상공인",
        "support_amount": "시설현대화·공동마케팅 (현물지원)",
        "application_start_date": "2026-03-01",
        "application_end_date": "2026-06-30",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
        "program_type": "기술지원",
        "max_amount_man": 0,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026014",
        "program_name": "소상공인 컨설팅 지원",
        "category": "경영",
        "support_target": "소상공인 (업력 무관)",
        "support_amount": "무료 경영 컨설팅 (최대 5회)",
        "application_start_date": "2026-01-02",
        "application_end_date": "2026-10-31",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
        "program_type": "컨설팅",
        "max_amount_man": 0,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026015",
        "program_name": "골목형상점가 지원사업",
        "category": "경영",
        "support_target": "골목형상점가 조직화 소상공인",
        "support_amount": "공동마케팅·환경개선 (최대 2억원/상점가)",
        "application_start_date": "2026-02-15",
        "application_end_date": "2026-04-30",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
        "program_type": "보조금",
        "max_amount_man": 20000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026016",
        "program_name": "백년가게/백년소공인",
        "category": "경영",
        "support_target": "업력 30년 이상 우수 소상공인/소공인",
        "support_amount": "브랜드 마케팅·시설개선 (선정형)",
        "application_start_date": "2026-04-01",
        "application_end_date": "2026-05-31",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
        "program_type": "컨설팅",
        "max_amount_man": 0,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026017",
        "program_name": "소상공인 재기지원",
        "category": "금융",
        "support_target": "폐업 후 재창업 소상공인",
        "support_amount": "최대 2,000만원 (재기지원금)",
        "application_start_date": "2026-01-02",
        "application_end_date": "2026-12-31",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
        "program_type": "보조금",
        "max_amount_man": 2000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026018",
        "program_name": "서울시 자영업자 이자지원",
        "category": "금융",
        "support_target": "서울시 소재 자영업자 (소상공인 대출 보유)",
        "support_amount": "대출 이자 1~2%p 지원 (최대 300만원/년)",
        "application_start_date": "2026-03-01",
        "application_end_date": "2026-12-31",
        "managing_org": "서울시",
        "executing_org": "서울신용보증재단",
        "detail_url": "https://www.seoulshinbo.co.kr/",
        "program_type": "보조금",
        "max_amount_man": 300,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026019",
        "program_name": "여성기업 창업지원",
        "category": "창업",
        "support_target": "여성 예비창업자 및 초기창업자",
        "support_amount": "최대 1억원 (사업화+멘토링)",
        "application_start_date": "2026-04-01",
        "application_end_date": "2026-05-15",
        "managing_org": "여성기업종합지원센터",
        "executing_org": "여성기업종합지원센터",
        "detail_url": "https://www.wbiz.or.kr/",
        "program_type": "보조금",
        "max_amount_man": 10000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026020",
        "program_name": "장애인 창업지원",
        "category": "창업",
        "support_target": "장애인 예비/초기 창업자",
        "support_amount": "최대 7,000만원 (창업자금+교육)",
        "application_start_date": "2026-03-01",
        "application_end_date": "2026-04-30",
        "managing_org": "장애인기업종합지원센터",
        "executing_org": "장애인기업종합지원센터",
        "detail_url": "https://www.debc.or.kr/",
        "program_type": "보조금",
        "max_amount_man": 7000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026021",
        "program_name": "시니어 창업지원",
        "category": "창업",
        "support_target": "만 40세 이상 예비/초기 창업자",
        "support_amount": "최대 1억원",
        "application_start_date": "2026-04-01",
        "application_end_date": "2026-04-30",
        "managing_org": "중소벤처기업부",
        "executing_org": "창업진흥원",
        "detail_url": "https://www.k-startup.go.kr/",
        "program_type": "보조금",
        "max_amount_man": 10000,
        "industry_filter": ["all"],
    },
    {
        "program_id": "SP2026022",
        "program_name": "소상공인 방역비 지원",
        "category": "경영",
        "support_target": "외식업·다중이용시설 소상공인",
        "support_amount": "최대 100만원 (방역물품·위생장비)",
        "application_start_date": "2026-02-01",
        "application_end_date": "2026-06-30",
        "managing_org": "소상공인시장진흥공단",
        "executing_org": "소상공인시장진흥공단",
        "detail_url": "https://www.sbiz.or.kr/",
        "program_type": "보조금",
        "max_amount_man": 100,
        "industry_filter": [
            "CS100001", "CS100002", "CS100003", "CS100004", "CS100005",
            "CS100006", "CS100007", "CS100008", "CS100009", "CS100010",
        ],
    },
    {
        "program_id": "SP2026023",
        "program_name": "서울신용보증재단 보증지원",
        "category": "금융",
        "support_target": "서울시 소재 소상공인·자영업자",
        "support_amount": "최대 1억원 (보증서 발급)",
        "application_start_date": "2026-01-02",
        "application_end_date": "2026-12-31",
        "managing_org": "서울신용보증재단",
        "executing_org": "서울신용보증재단",
        "detail_url": "https://www.seoulshinbo.co.kr/",
        "program_type": "대출",
        "max_amount_man": 10000,
        "industry_filter": ["all"],
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

    def _matches_industry(self, program: dict[str, Any]) -> bool:
        """업종 필터에 매칭되는지 확인"""
        industry_filter = program.get("industry_filter", ["all"])
        if "all" in industry_filter:
            return True
        return self.industry_code in industry_filter

    def get_active_programs(self) -> list[SupportProgram]:
        """현재 신청 가능한 전체 지원사업 목록 (마감 임박순)"""
        programs = self._load_programs_from_api()

        # 신청 마감일이 지나지 않은 것만 필터링
        active_programs = [p for p in programs if self._is_active_program(p)]

        # 업종 필터링
        active_programs = [p for p in active_programs if self._matches_industry(p)]

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
        program_type: str | None = None,
    ) -> list[SupportProgram]:
        """사용자 조건에 매칭되는 지원사업 목록 (마감 임박순)"""
        active_programs = self.get_active_programs()

        matched = []
        for program in active_programs:
            # 지역 필터링 — 서울 지정 시 서울 관련 + 중앙정부 사업 포함
            if district and "서울" in district:
                managing_org = program.get("managing_org", "")
                # 서울 이외 지자체 사업 제외
                if managing_org not in [
                    "중소벤처기업부", "소상공인시장진흥공단", "창업진흥원",
                    "서울시", "서울신용보증재단", "서울산업진흥원",
                    "여성기업종합지원센터", "장애인기업종합지원센터",
                ]:
                    continue

            # 예산 매칭: 프로그램 최대 지원금이 사용자 예산 범위 내인지
            max_amt = program.get("max_amount_man", 0)
            if budget_max and max_amt > 0 and max_amt > budget_max * 3:
                # 사용자 예산의 3배 초과 프로그램 — 현실적이지 않으므로 제외하지 않음 (대출은 예외)
                pass
            if budget_min and max_amt > 0 and max_amt < budget_min * 0.1:
                # 너무 소액인 프로그램 제외
                continue

            # 프로그램 유형 필터링
            if program_type and program.get("program_type") != program_type:
                continue

            # 타겟 연령 필터링 (청년 = 39세 이하)
            if target_age:
                support_target = program.get("support_target", "")
                if "청년" in target_age.lower() and "39세" not in support_target and "청년" not in support_target:
                    pass  # 청년 타겟이지만 비청년 프로그램도 포함 (정보 제공)

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
