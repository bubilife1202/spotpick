from __future__ import annotations

import math
from typing import Any, TypedDict

from config.industry_config import DEFAULT_INDUSTRY, load_industry_config

WEEKS_PER_MONTH = 4.3


class TimelineStage(TypedDict):
    name: str
    duration_weeks: int
    start_week: int
    end_week: int
    can_overlap: bool
    description: str


class TimelineResult(TypedDict):
    stages: list[TimelineStage]
    total_weeks: int
    total_months: float
    fast_estimate_months: float
    slow_estimate_months: float
    summary: str
    disclaimer: str


def _clamp(value: int, min_value: int, max_value: int) -> int:
    return max(min_value, min(max_value, value))


def _days_to_weeks(days: int | float) -> int:
    """Convert days to weeks, rounding up (ceiling)."""
    return math.ceil(days / 7)


def _resolve_duration_days(raw: int | float | list[int | float]) -> int:
    """Resolve a duration_days value which may be a single number or [min, max] range.

    For a range, returns the *max* value as a conservative base estimate.
    """
    if isinstance(raw, list):
        return int(max(raw))
    return int(raw)


class TimelineService:
    """업종별 창업 일정을 계산하는 서비스.

    Config-driven: ``TIMELINE_CONFIG`` 이 업종 JSON 에 존재하면
    그 설정에 따라 단계를 구성하고, 없으면 카페 기본 6단계 로직으로
    폴백합니다.
    """

    def __init__(self, industry_code: str = DEFAULT_INDUSTRY) -> None:
        self.industry_code = industry_code
        try:
            self._config: dict[str, Any] = load_industry_config(industry_code)
        except FileNotFoundError:
            self._config = {}
        self._timeline_cfg: dict[str, Any] = self._config.get("TIMELINE_CONFIG", {})

    # ------------------------------------------------------------------
    # Config-stage helpers
    # ------------------------------------------------------------------

    def _has_config_stages_with_durations(self) -> bool:
        """Return True if the loaded config has stages with explicit durations."""
        stages = self._timeline_cfg.get("stages")
        if not stages:
            return False
        first = stages[0]
        return "base_duration_weeks" in first or "duration_days" in first

    def _build_stages_from_config(
        self,
        business_type: str,
    ) -> list[TimelineStage]:
        """Build a sequential timeline from config-defined stages.

        Respects ``can_overlap`` flags: when a stage allows overlap, its
        start is pulled back by 1 week from the previous stage's end.
        Otherwise, stages chain end-to-end.

        Durations are read from ``base_duration_weeks`` or converted from
        ``duration_days``.  Adjustments in ``TIMELINE_CONFIG.adjustments``
        are applied when the *business_type* matches a key.
        """
        raw_stages: list[dict[str, Any]] = self._timeline_cfg["stages"]
        adjustments: dict[str, dict[str, int]] = self._timeline_cfg.get("adjustments", {})
        biz_adj: dict[str, int] = adjustments.get(business_type, {})

        stages: list[TimelineStage] = []
        cursor = 0  # current week pointer

        for idx, cfg in enumerate(raw_stages):
            # --- resolve duration ---
            if "base_duration_weeks" in cfg:
                duration = int(cfg["base_duration_weeks"])
            elif "duration_days" in cfg:
                duration = _days_to_weeks(_resolve_duration_days(cfg["duration_days"]))
            else:
                duration = 2  # safe fallback

            # --- apply per-stage adjustment (keyed by stage id or index) ---
            stage_id = cfg.get("id", cfg.get("name", str(idx)))
            adj_val = biz_adj.get(stage_id, 0)
            duration = max(1, duration + adj_val)

            # --- resolve name / description ---
            name: str = cfg.get("label", cfg.get("name", f"Stage {idx + 1}"))
            description: str = cfg.get("description", "")
            if not description:
                key_tasks = cfg.get("key_tasks")
                if key_tasks:
                    description = ", ".join(key_tasks)

            can_overlap: bool = cfg.get("can_overlap", False)

            # --- compute start_week ---
            if idx == 0:
                start_week = 0
            elif can_overlap:
                start_week = max(0, cursor - 1)
            else:
                start_week = cursor

            end_week = start_week + duration
            cursor = end_week

            stages.append(
                TimelineStage(
                    name=name,
                    duration_weeks=duration,
                    start_week=start_week,
                    end_week=end_week,
                    can_overlap=can_overlap,
                    description=description,
                )
            )

        return stages

    # ------------------------------------------------------------------
    # Hardcoded café fallback (original 6-stage logic)
    # ------------------------------------------------------------------

    def _build_cafe_stages(
        self,
        business_type: str,
        budget_range: str,
        area_pyeong: int,
        is_franchise: bool,
        district_type: str,
    ) -> list[TimelineStage]:
        """Original café 6-stage timeline logic (CS100010 fallback)."""
        safe_area = max(1, area_pyeong)

        # 1. 물건 탐색·계약
        property_duration = 4
        if district_type == "발달상권":
            property_duration += 2
        property_duration = _clamp(property_duration, 3, 6)

        # 2. 행정 절차
        admin_duration = 2
        if business_type == "테이크아웃":
            admin_duration = 1
        admin_duration = _clamp(admin_duration, 1, 2)

        # 3. 인테리어
        interior_base = math.ceil(safe_area * 0.25)
        interior_base = _clamp(interior_base, 3, 10)
        interior_adjust = 0
        if business_type == "테이크아웃":
            interior_adjust -= 1
        elif business_type == "브런치":
            interior_adjust += 1
        if budget_range == "3천만원 이하":
            interior_adjust -= 1
        elif budget_range == "1억+":
            interior_adjust += 2
        if is_franchise:
            interior_adjust -= 1
        interior_duration = _clamp(interior_base + interior_adjust, 3, 10)

        # 4. 장비·원재료
        equipment_duration = 2
        if business_type == "브런치" or budget_range == "1억+":
            equipment_duration = 3
        equipment_duration = _clamp(equipment_duration, 2, 3)

        # 5. 인력·교육
        staffing_duration = 2
        if is_franchise:
            staffing_duration -= 1
        if business_type == "브런치":
            staffing_duration += 1
        staffing_duration = max(1, staffing_duration)

        # 6. 시운전·오픈
        open_duration = 1
        if business_type == "브런치":
            open_duration = 2
        open_duration = _clamp(open_duration, 1, 2)

        stages: list[TimelineStage] = []

        property_start = 0
        property_end = property_start + property_duration
        stages.append(
            TimelineStage(
                name="물건 탐색·계약",
                duration_weeks=property_duration,
                start_week=property_start,
                end_week=property_end,
                can_overlap=False,
                description="상권 조사, 후보지 방문, 임대차 조건 협의",
            )
        )

        admin_start = max(0, property_end - 1)
        admin_end = admin_start + admin_duration
        stages.append(
            TimelineStage(
                name="행정 절차",
                duration_weeks=admin_duration,
                start_week=admin_start,
                end_week=admin_end,
                can_overlap=True,
                description="사업자등록·위생교육·건강검진·영업신고를 병행 처리",
            )
        )

        interior_start = max(property_end, admin_end)
        interior_end = interior_start + interior_duration
        stages.append(
            TimelineStage(
                name="인테리어",
                duration_weeks=interior_duration,
                start_week=interior_start,
                end_week=interior_end,
                can_overlap=False,
                description="평수와 공사 범위에 따른 설계·시공",
            )
        )

        equipment_start = interior_start + math.ceil(interior_duration * 0.7)
        equipment_end = equipment_start + equipment_duration
        stages.append(
            TimelineStage(
                name="장비·원재료",
                duration_weeks=equipment_duration,
                start_week=equipment_start,
                end_week=equipment_end,
                can_overlap=True,
                description="장비 발주와 초기 원재료 확보",
            )
        )

        staffing_start = max(interior_end, equipment_end)
        staffing_end = staffing_start + staffing_duration
        stages.append(
            TimelineStage(
                name="인력·교육",
                duration_weeks=staffing_duration,
                start_week=staffing_start,
                end_week=staffing_end,
                can_overlap=False,
                description="채용, 메뉴·서비스 교육 및 운영 매뉴얼 정비",
            )
        )

        open_start = staffing_end
        open_end = open_start + open_duration
        stages.append(
            TimelineStage(
                name="시운전·오픈",
                duration_weeks=open_duration,
                start_week=open_start,
                end_week=open_end,
                can_overlap=False,
                description="동선 점검, 시운전, 그랜드오픈 준비",
            )
        )

        return stages

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_timeline(
        self,
        *,
        business_type: str = "일반",
        budget_range: str = "3천~1억",
        area_pyeong: int = 15,
        is_franchise: bool = False,
        district_type: str = "골목상권",
        # backward-compat alias
        cafe_type: str | None = None,
    ) -> TimelineResult:
        """입력 조건을 기반으로 창업 일정과 간트 정보를 생성한다.

        ``cafe_type`` is accepted as a backward-compatible alias for
        ``business_type``.  If both are supplied, ``cafe_type`` wins
        to preserve existing callers.
        """
        # Resolve backward-compat alias
        if cafe_type is not None:
            business_type = cafe_type
        business_type = business_type.strip() if business_type else "일반"
        budget_range = budget_range.strip() if budget_range else "3천~1억"
        district_type = district_type.strip() if district_type else "골목상권"

        # ----- Build stages -----
        if self._has_config_stages_with_durations():
            stages = self._build_stages_from_config(business_type)
        else:
            stages = self._build_cafe_stages(
                business_type=business_type,
                budget_range=budget_range,
                area_pyeong=area_pyeong,
                is_franchise=is_franchise,
                district_type=district_type,
            )

        # ----- Aggregate totals -----
        total_weeks = max(stage["end_week"] for stage in stages)

        weeks_per_month = self._timeline_cfg.get("WEEKS_PER_MONTH", WEEKS_PER_MONTH)
        estimates = self._timeline_cfg.get("estimates", {})
        fast_mult = estimates.get("fast_multiplier", 0.7)
        slow_mult = estimates.get("slow_multiplier", 1.4)
        round_digits = estimates.get("total_months_round_digits", 1)

        total_months = round(total_weeks / weeks_per_month, round_digits)
        fast_estimate_months = round((total_weeks * fast_mult) / weeks_per_month, round_digits)
        slow_estimate_months = round((total_weeks * slow_mult) / weeks_per_month, round_digits)

        # ----- Summary -----
        safe_area = max(1, area_pyeong)
        budget_label_map = self._timeline_cfg.get("budget_label_map", {
            "3천만원 이하": "셀프 인테리어",
            "3천~1억": "일반 인테리어",
            "1억+": "풀 인테리어",
        })
        budget_label = budget_label_map.get(budget_range, "일반 인테리어")

        sp = self._timeline_cfg.get("summary_parts", {})
        skip_type = sp.get("include_cafe_type_if_not", "일반")
        franchise_label = sp.get("is_franchise_label", "프랜차이즈")
        independent_label = sp.get("independent_label", "개인")
        area_suffix = sp.get("area_suffix", "평 기준")

        summary_parts = [f"{safe_area}{area_suffix}"]
        if business_type != skip_type:
            summary_parts.append(business_type)
        summary_parts.append(franchise_label if is_franchise else independent_label)
        summary_parts.append(budget_label)

        display_name = self._config.get("display_name", self._config.get("name", ""))
        if display_name:
            summary = f"{display_name} 창업 약 {total_months}개월 ({', '.join(summary_parts)})"
        else:
            summary = f"약 {total_months}개월 ({', '.join(summary_parts)})"

        disclaimer = self._timeline_cfg.get(
            "disclaimer",
            "추정 일정이며 인허가 지연, 공사 범위에 따라 실제 일정은 달라질 수 있습니다.",
        )

        return TimelineResult(
            stages=stages,
            total_weeks=total_weeks,
            total_months=total_months,
            fast_estimate_months=fast_estimate_months,
            slow_estimate_months=slow_estimate_months,
            summary=summary,
            disclaimer=disclaimer,
        )


# ======================================================================
# Registry / singleton management
# ======================================================================

_registry: dict[str, TimelineService] = {}


def get_timeline_service(industry_code: str = DEFAULT_INDUSTRY) -> TimelineService:
    """Return a cached ``TimelineService`` instance for the given industry.

    Instances are stored in a module-level registry so each industry code
    is constructed at most once.
    """
    if industry_code not in _registry:
        _registry[industry_code] = TimelineService(industry_code=industry_code)
    return _registry[industry_code]
