"""
Data Service - 서울시 상권 데이터 기반 추천 서비스 (멀티업종 지원)
64개 필드 전체 활용, 업종별 레지스트리 패턴
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Optional, Tuple, List, cast

from config.industry_config import load_industry_config, DEFAULT_INDUSTRY

VALID_INDUSTRY_CODES = {f"CS10000{i}" for i in range(1, 10)} | {"CS100010"}


def _validate_industry_code(code: str) -> str:
    """Validate industry code against whitelist."""
    if code not in VALID_INDUSTRY_CODES:
        raise ValueError(f"Invalid industry code: {code}")
    return code


_DEFAULT_RENT_RANGES: dict[str, tuple[int, int, int, int, int]] = {
    "골목상권": (800_000, 1_200_000, 1_800_000, 2_800_000, 4_500_000),
    "발달상권": (2_500_000, 4_000_000, 5_500_000, 7_500_000, 12_000_000),
    "전통시장": (500_000, 1_000_000, 1_800_000, 2_800_000, 4_500_000),
    "관광특구": (4_000_000, 6_500_000, 9_000_000, 12_000_000, 18_000_000),
}


def _parse_rent_ranges(config: dict[str, Any]) -> dict[str, tuple[int, int, int, int, int]]:
    """Parse RENT_RANGES from config (list format) to tuple format."""
    raw = config.get("RENT_RANGES")
    if not raw or not isinstance(raw, dict):
        return _DEFAULT_RENT_RANGES
    result: dict[str, tuple[int, int, int, int, int]] = {}
    for key, vals in raw.items():
        if isinstance(vals, (list, tuple)) and len(vals) == 5:
            result[key] = tuple(vals)  # type: ignore[arg-type]
    return result or _DEFAULT_RENT_RANGES


def _get_krei_rent_ranges(
    industry_code: str,
) -> dict[str, tuple[int, int, int, int, int]] | None:
    """KREI 원시자료에서 업종별 · 상권유형별 임대료 분위수를 5구간 튜플로 변환."""
    try:
        from api.services.krei_data_service import get_rent_benchmark

        result: dict[str, tuple[int, int, int, int, int]] = {}
        for dt in ("골목상권", "발달상권", "전통시장", "관광특구"):
            bm = get_rent_benchmark(industry_code, district_type=dt, seoul_only=True)
            if bm and bm.get("n", 0) >= 10:
                # 만원 → 원 변환
                p25 = int(bm.get("monthly_rent_p25", 0) * 10_000)
                med = int(bm.get("monthly_rent_median", 0) * 10_000)
                p75 = int(bm.get("monthly_rent_p75", 0) * 10_000)
                # p5 ≈ p25*0.5, p95 ≈ p75*1.5 (외삽)
                p5 = max(int(p25 * 0.5), 300_000)
                p95 = int(p75 * 1.5)
                result[dt] = (p5, p25, med, p75, p95)

        return result if result else None
    except Exception:
        return None


# KREI 기반 임대료 범위 캐시 (업종별)
_krei_rent_cache: dict[str, dict[str, tuple[int, int, int, int, int]] | None] = {}


def estimate_rent(
    district_type: str,
    sales_per_store: int,
    percentile_rank: float,
    rent_ranges: dict[str, tuple[int, int, int, int, int]] | None = None,
    industry_code: str | None = None,
) -> int:
    """Estimate monthly rent based on district type and sales percentile rank (0.0-1.0).

    KREI 원시자료 → config RENT_RANGES → 기본값 순 폴백.
    """
    # KREI 데이터 우선 시도 (industry_code 있을 때)
    if rent_ranges is None and industry_code:
        if industry_code not in _krei_rent_cache:
            _krei_rent_cache[industry_code] = _get_krei_rent_ranges(industry_code)
        krei = _krei_rent_cache[industry_code]
        if krei and district_type in krei:
            rent_ranges = krei

    ranges = rent_ranges or _DEFAULT_RENT_RANGES
    r = ranges.get(district_type, ranges.get("골목상권", _DEFAULT_RENT_RANGES["골목상권"]))
    if percentile_rank <= 0.25:
        t = percentile_rank / 0.25
        rent = r[0] + t * (r[1] - r[0])
    elif percentile_rank <= 0.50:
        t = (percentile_rank - 0.25) / 0.25
        rent = r[1] + t * (r[2] - r[1])
    elif percentile_rank <= 0.75:
        t = (percentile_rank - 0.50) / 0.25
        rent = r[2] + t * (r[3] - r[2])
    else:
        t = (percentile_rank - 0.75) / 0.25
        rent = r[3] + t * (r[4] - r[3])
    return int(rent / 10_000) * 10_000


class DataService:
    """서울시 상권 데이터 서비스 — 업종별 인스턴스."""

    def __init__(self, industry_code: str = DEFAULT_INDUSTRY):
        self.industry_code = _validate_industry_code(industry_code)
        self.config: dict[str, Any] = {}
        self.display_name: str = "카페"
        self._rent_ranges = _DEFAULT_RENT_RANGES

        # Data
        self.districts: list[dict[str, Any]] = []
        self.summary: dict[str, Any] = {}
        self._district_by_code: dict[str, dict[str, Any]] = {}
        self._district_by_name: dict[str, dict[str, Any]] = {}
        self._sales_percentile: dict[str, float] = {}
        self._avg_foot_traffic: float = 0.0
        self._avg_facility_score: float = 0.0
        self._transit_percentiles: dict[str, float] = {}

        self._load_config()
        self._load_data()

    def _load_config(self):
        """Load industry config."""
        try:
            self.config = load_industry_config(self.industry_code)
            self.display_name = self.config.get("display_name", self.config.get("name", "카페"))
            self._rent_ranges = _parse_rent_ranges(self.config)
        except FileNotFoundError:
            # Fallback for industries without config
            self.config = {}
            self.display_name = "카페" if self.industry_code == DEFAULT_INDUSTRY else self.industry_code

    def _load_data(self):
        """데이터 로드"""
        data_dir = Path(__file__).parent.parent.parent / "data" / "processed"

        # Try industry-specific file, then fallback
        districts_file = data_dir / f"{self.industry_code}_districts.json"
        if not districts_file.exists():
            districts_file = data_dir / "coffee_districts.json"

        if not districts_file.exists():
            print(f"[DataService:{self.industry_code}] 데이터 파일 없음: {districts_file}")
            self.districts = []
            self.summary = {"total_districts": 0, "total_stores": 0, "avg_monthly_sales": 0, "avg_survival_rate": 0, "district_types": {}}
            return

        with open(districts_file, encoding="utf-8") as f:
            self.districts = cast(list[dict[str, Any]], json.load(f))

        # Normalize survival_rate: raw data is 0-5.0 scale → convert to 0-1.0
        for d in self.districts:
            sr = d.get("survival_rate")
            if isinstance(sr, (int, float)):
                normalized = float(sr) / 5.0  # raw 0-5 scale → 0-1
                d["survival_rate"] = max(0.0, min(normalized, 1.0))

        # Try industry-specific summary, then fallback
        summary_file = data_dir / f"{self.industry_code}_summary.json"
        if not summary_file.exists():
            summary_file = data_dir / "summary.json"
        if summary_file.exists():
            with open(summary_file, encoding="utf-8") as f:
                self.summary = cast(dict[str, Any], json.load(f))
        else:
            # Auto-generate summary from districts
            self.summary = self._generate_summary()

        # 상권 인덱싱
        self._district_by_code = {
            str(d.get("district_code")): d
            for d in self.districts
            if isinstance(d, dict) and d.get("district_code") is not None
        }
        self._district_by_name = {
            str(d.get("district_name")): d
            for d in self.districts
            if isinstance(d, dict) and d.get("district_name") is not None
        }

        self._sales_percentile = {}
        type_sales: dict[str, list[tuple[str, int]]] = {}
        for d in self.districts:
            sc = max(1, d.get("store_count", 1))
            sps = int(d["monthly_sales"] / sc)
            dt = d["district_type"]
            type_sales.setdefault(dt, []).append((d["district_code"], sps))
        for dt, entries in type_sales.items():
            entries.sort(key=lambda x: x[1])
            n = len(entries)
            for i, (code, _) in enumerate(entries):
                self._sales_percentile[code] = i / max(1, n - 1)

        ft_values = [d.get("foot_traffic_total", 0) for d in self.districts if d.get("foot_traffic_total", 0) > 0]
        self._avg_foot_traffic = sum(ft_values) / max(1, len(ft_values)) if ft_values else 0

        fac_values = [d.get("facility_score", 0) for d in self.districts if d.get("facility_score", 0) > 0]
        self._avg_facility_score = sum(fac_values) / max(1, len(fac_values)) if fac_values else 0

        transit_values = sorted(d.get("transit_raw", 0) for d in self.districts)
        self._transit_percentiles = {}
        n = max(1, len(transit_values))
        for d in self.districts:
            raw = d.get("transit_raw", 0)
            rank = sum(1 for v in transit_values if v <= raw)
            self._transit_percentiles[d["district_code"]] = round(rank / n, 4)

        print(
            f"[DataService:{self.industry_code}] 로드 완료: {len(self.districts)}개 상권"
            + (f", {len(self.districts[0].keys())}개 필드" if self.districts else "")
        )

    def _generate_summary(self) -> dict[str, Any]:
        """Generate summary from district data."""
        if not self.districts:
            return {"total_districts": 0, "total_stores": 0, "avg_monthly_sales": 0, "avg_survival_rate": 0, "district_types": {}}

        total_stores = sum(d.get("store_count", 0) for d in self.districts)
        total_sales = sum(d.get("monthly_sales", 0) for d in self.districts)
        total_survival = sum(d.get("survival_rate", 0) for d in self.districts)
        n = len(self.districts)

        district_types: dict[str, int] = {}
        for d in self.districts:
            dt = d.get("district_type", "기타")
            district_types[dt] = district_types.get(dt, 0) + 1

        return {
            "total_districts": n,
            "total_stores": total_stores,
            "avg_monthly_sales": total_sales / max(1, n),
            "avg_survival_rate": total_survival / max(1, n),
            "district_types": district_types,
        }

    def get_districts(
        self,
        district_type: Optional[str] = None,
        min_sales: Optional[int] = None,
        max_sales: Optional[int] = None,
        min_survival_rate: Optional[float] = None,
        sort_by: str = "monthly_sales",
        ascending: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[dict[str, Any]], int]:
        """상권 목록 조회"""
        filtered = self.districts.copy()

        if district_type:
            filtered = [d for d in filtered if d["district_type"] == district_type]

        if min_sales:
            filtered = [d for d in filtered if d["monthly_sales"] >= min_sales]

        if max_sales:
            filtered = [d for d in filtered if d["monthly_sales"] <= max_sales]

        if min_survival_rate:
            filtered = [d for d in filtered if d["survival_rate"] >= min_survival_rate]

        # 정렬
        if sort_by in filtered[0] if filtered else {}:
            filtered.sort(key=lambda d: d.get(sort_by, 0) or 0, reverse=not ascending)

        total = len(filtered)
        start = (page - 1) * page_size
        end = start + page_size

        return filtered[start:end], total

    def get_district(self, code: str) -> Optional[dict[str, Any]]:
        """상권 상세 조회"""
        return self._district_by_code.get(code)

    def get_district_by_name(self, name: str) -> Optional[dict[str, Any]]:
        """상권명으로 조회"""
        return self._district_by_name.get(name)

    def search_districts(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """상권 검색"""
        q = (query or "").strip().lower()
        if not q:
            return []

        q_compact = re.sub(r"\s+", "", q)
        matches: list[dict[str, Any]] = []

        for d in self.districts:
            name = str(d.get("district_name", ""))
            dtype = str(d.get("district_type", ""))
            name_lower = name.lower()
            dtype_lower = dtype.lower()

            if (
                q in name_lower
                or q in dtype_lower
                or (q_compact and q_compact in re.sub(r"\s+", "", name_lower))
            ):
                matches.append(d)

        def as_int(v: object) -> int:
            try:
                return int(v) if isinstance(v, int) else 0
            except Exception:
                return 0

        def rank(d: dict[str, Any]) -> tuple[int, int, int, int, int, int, int]:
            name = str(d.get("district_name", ""))
            name_lower = name.lower()
            dtype_lower = str(d.get("district_type", "")).lower()

            exact = 1 if name_lower == q else 0
            prefer_station = 1 if name == f"{query.strip()}역" else 0
            prefix = 1 if name_lower.startswith(q) else 0
            contains = 1 if q in name_lower else 0
            dtype_contains = 1 if q in dtype_lower else 0
            sales = as_int(d.get("monthly_sales"))
            shortness = -len(name)
            return (exact, prefer_station, prefix, contains, dtype_contains, sales, shortness)

        matches.sort(key=rank, reverse=True)
        return matches[: max(1, int(limit or 10))]

    def get_recommendations(
        self,
        budget_min: int,
        budget_max: int,
        category: str = "coffee",
        preferred_district: Optional[str] = None,
        preferred_area_type: Optional[str] = None,
        min_survival_rate: float = 0.0,
        top_n: int = 10,
    ) -> list[dict[str, Any]]:
        """예산과 조건에 맞는 최적의 창업 위치 추천"""
        candidates = []

        for d in self.districts:
            sales_per_store = int(d["monthly_sales"] / max(1, d.get("store_count", 1)))
            pctile = self._sales_percentile.get(d["district_code"], 0.5)
            estimated_rent = estimate_rent(d["district_type"], sales_per_store, pctile, self._rent_ranges, industry_code=self.industry_code)

            if estimated_rent > budget_max:
                continue

            if preferred_district and preferred_district not in d["district_name"]:
                continue

            if preferred_area_type and d["district_type"] != preferred_area_type:
                continue

            if d["survival_rate"] < min_survival_rate:
                continue

            success_prob = self._calculate_success_probability(d)
            risk_factors = self._identify_risks(d)
            recommendations = self._generate_recommendations(d)
            key_factors = self._extract_key_factors(d)

            if budget_min > 0:
                rent_fit = 1.0 if estimated_rent >= budget_min else (estimated_rent / budget_min)
            else:
                rent_fit = min(1.0, estimated_rent / max(1, budget_max))

            score = (success_prob * 0.85) + (rent_fit * 0.15)

            candidates.append(
                {
                    "district": d,
                    "estimated_rent": estimated_rent,
                    "success_probability": success_prob,
                    "score": score,
                    "risk_factors": risk_factors,
                    "recommendations": recommendations,
                    "key_success_factors": key_factors,
                }
            )

        candidates.sort(key=lambda c: (c["score"], c["success_probability"]), reverse=True)

        results = []
        for rank, c in enumerate(candidates[:top_n], 1):
            d = c["district"]
            sales_per_store = int(d["monthly_sales"] / max(1, d.get("store_count", 1)))
            positioning_name, positioning_detail, _ = self._determine_positioning(d)
            purchasing_power_score = self._calculate_purchasing_power(d)
            results.append(
                {
                    "rank": rank,
                    "district_code": d["district_code"],
                    "district_name": d["district_name"],
                    "district_type": d["district_type"],
                    "address": f"서울특별시 {d['district_name']}",
                    "success_probability": c["success_probability"],
                    "estimated_monthly_rent": c["estimated_rent"],
                    "estimated_monthly_sales": sales_per_store,
                    "survival_rate_2y": d["survival_rate"],
                    "time_analysis": {
                        "peak_time": d["peak_time"],
                        "time_00_06": round(d["time_00_06_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "time_06_11": round(d["time_06_11_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "time_11_14": round(d["time_11_14_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "time_14_17": round(d["time_14_17_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "time_17_21": round(d["time_17_21_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "time_21_24": round(d["time_21_24_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                    },
                    "day_analysis": {
                        "peak_day": d["peak_day"],
                        "weekday_ratio": round(d["weekday_ratio"] * 100, 1),
                        "weekend_ratio": round(d["weekend_ratio"] * 100, 1),
                        "mon": round(d["mon_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "tue": round(d["tue_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "wed": round(d["wed_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "thu": round(d["thu_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "fri": round(d["fri_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "sat": round(d["sat_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "sun": round(d["sun_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                    },
                    "customer_analysis": {
                        "main_age_group": d["main_age_group"],
                        "male_ratio": round(d["male_ratio"] * 100, 1),
                        "female_ratio": round(d["female_ratio"] * 100, 1),
                        "age_10": round(d["age_10_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "age_20": round(d["age_20_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "age_30": round(d["age_30_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "age_40": round(d["age_40_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "age_50": round(d["age_50_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                        "age_60": round(d["age_60_sales"] / max(1, d["monthly_sales"]) * 100, 1),
                    },
                    "competition": {
                        "store_count": d["store_count"],
                        "new_stores": d["new_stores"],
                        "closed_stores": d["closed_stores"],
                        "franchise_stores": d["franchise_stores"],
                        "franchise_ratio": round(
                            d["franchise_stores"] / max(1, d["store_count"]) * 100, 1
                        ),
                    },
                    "risk_factors": c["risk_factors"],
                    "recommendations": c["recommendations"],
                    "key_success_factors": c["key_success_factors"],
                    "foot_traffic_total": d.get("foot_traffic_total", 0),
                    "worker_total": d.get("worker_total", 0),
                    "resident_total": d.get("resident_total", 0),
                    "facility_score": d.get("facility_score", 0),
                    "facility_subway": d.get("facility_subway", 0),
                    "change_indicator": d.get("change_indicator", ""),
                    "avg_operation_months": d.get("avg_operation_months", 0),
                    "transit_raw": d.get("transit_raw", 0),
                    "transit_percentile": self._transit_percentiles.get(d["district_code"], 0.5),
                    "positioning": positioning_name,
                    "positioning_detail": positioning_detail,
                    "purchasing_power": purchasing_power_score,
                    "lat": d.get("lat", 0.0),
                    "lng": d.get("lng", 0.0),
                }
            )

        return results

    def _calculate_success_probability(self, d: dict[str, Any]) -> float:
        # Use scorecard if available, otherwise rule-based fallback
        try:
            from api.services.scorecard_service import get_scorecard_service
            svc = get_scorecard_service(self.industry_code)
            if not svc._districts:
                svc.set_districts(self.districts)
            score = svc._quick_score(d)
            # Convert 0-100 score to 0-1 probability
            return round(max(0.1, min(0.95, score / 100)), 2)
        except Exception:
            pass

        # Fallback: rule-based
        base = d["survival_rate"]

        avg_sales = self.summary.get("avg_monthly_sales", 0)
        if avg_sales > 0:
            if d["monthly_sales"] > avg_sales * 1.5:
                base += 0.05
            elif d["monthly_sales"] < avg_sales * 0.5:
                base -= 0.05

        if d["store_count"] > 20:
            base -= 0.1
        elif d["store_count"] < 5:
            base += 0.05

        if d["closed_stores"] > d["new_stores"]:
            base -= 0.05

        if d["district_type"] == "발달상권":
            base += 0.03
        elif d["district_type"] == "관광특구":
            base += 0.02

        foot_traffic = d.get("foot_traffic_total", 0)
        if foot_traffic > 0 and self._avg_foot_traffic > 0:
            if foot_traffic > self._avg_foot_traffic * 1.5:
                base += 0.04
            elif foot_traffic < self._avg_foot_traffic * 0.3:
                base -= 0.03

        facility_score = d.get("facility_score", 0)
        if facility_score > 0 and self._avg_facility_score > 0:
            if facility_score > self._avg_facility_score * 2:
                base += 0.03
            elif facility_score < self._avg_facility_score * 0.3:
                base -= 0.02

        change_code = d.get("change_indicator_code", "")
        if change_code == "HH":
            base += 0.04
        elif change_code == "HL":
            base += 0.02
        elif change_code == "LL":
            base -= 0.04
        elif change_code == "LH":
            base -= 0.01

        worker_pop = d.get("worker_total", 0)
        if worker_pop > 5000:
            base += 0.02

        transit_pctile = self._transit_percentiles.get(d["district_code"], 0.5)
        if transit_pctile > 0.8:
            base += 0.02
        elif transit_pctile < 0.2:
            base -= 0.02

        return round(max(0.1, min(0.95, base)), 2)

    def _identify_risks(self, d: dict[str, Any]) -> list[str]:
        risks = []
        display = self.display_name

        if d["store_count"] > 20:
            risks.append(f"높은 경쟁 밀도 ({display} {d['store_count']}개)")

        if d["survival_rate"] < 0.7:
            risks.append(f"평균 이하 생존율 ({d['survival_rate'] * 100:.0f}%)")

        if d["closed_stores"] > d["new_stores"]:
            risks.append(f"폐업 증가 추세 (폐업 {d['closed_stores']}개 > 개업 {d['new_stores']}개)")

        franchise_ratio = d["franchise_stores"] / max(1, d["store_count"])
        if franchise_ratio > 0.6:
            risks.append(f"프랜차이즈 밀집 ({franchise_ratio * 100:.0f}%)")

        if d["weekend_ratio"] < 0.2:
            risks.append("주말 매출 부진 (주말 비중 20% 미만)")

        change_code = d.get("change_indicator_code", "")
        if change_code == "LL":
            risks.append("쇠퇴 상권 (매출↓ 점포↓)")
        elif change_code == "LH":
            risks.append("과포화 위험 상권 (매출↓ 점포↑)")

        ft = d.get("foot_traffic_total", 0)
        if ft > 0 and self._avg_foot_traffic > 0 and ft < self._avg_foot_traffic * 0.3:
            risks.append("유동인구 매우 적음")

        transit_pctile = self._transit_percentiles.get(d["district_code"], 0.5)
        if transit_pctile < 0.2:
            risks.append("대중교통 접근성 낮음 (주차 확보 필요)")

        return risks

    def _generate_recommendations(self, d: dict[str, Any]) -> list[str]:
        """맞춤 추천 생성 — config의 RECOMMENDATION_TEXT 활용"""
        recs = []
        rec_text = self.config.get("RECOMMENDATION_TEXT", {})

        # 시간대 기반
        peak = d["peak_time"]
        by_peak = rec_text.get("by_peak_time") or rec_text.get("time_based", {})
        if peak in by_peak:
            recs.append(by_peak[peak])
        elif peak == "11-14":
            recs.append("점심 피크 상권 → 오전 10시 오픈, 빠른 회전율 전략")
        elif peak == "14-17":
            recs.append("오후 피크 상권 → 디저트/음료 세트 메뉴 강화")
        elif peak == "17-21":
            recs.append("저녁 피크 상권 → 저녁 시간대 특화")

        # 요일 기반
        by_day = rec_text.get("by_sales_ratio") or rec_text.get("day_based", {})
        if d["weekday_ratio"] > 0.75:
            recs.append(by_day.get("weekday_ratio_gt_0.75", by_day.get("weekday", "주중 매출 집중 → 평일 전략 강화")))
        elif d["weekend_ratio"] > 0.35:
            recs.append(by_day.get("weekend_ratio_gt_0.35", by_day.get("weekend", "주말 매출 비중 높음 → 주말 집중 전략")))

        # 고객층 기반
        main_age = d["main_age_group"]
        by_age = rec_text.get("by_main_age_group") or rec_text.get("age_based", {})
        if "20" in main_age:
            recs.append(by_age.get("contains_20", by_age.get("20s", "20대 주요 고객 → SNS 마케팅")))
        elif "30" in main_age:
            recs.append(by_age.get("contains_30", by_age.get("30s", "30대 주요 고객 → 품질 중심")))
        elif "40" in main_age or "50" in main_age:
            recs.append(by_age.get("contains_40_or_50", by_age.get("40s_plus", "40-50대 주요 고객 → 편안한 분위기")))

        # 경쟁 기반
        by_comp = rec_text.get("by_competition") or rec_text.get("competition", {})
        if d["store_count"] > 15:
            recs.append(by_comp.get("store_count_gt_15", by_comp.get("high", "경쟁 과다 → 차별화 필수")))

        # 상권 유형 기반
        by_area = rec_text.get("by_district_type") or rec_text.get("area", {})
        dt = d["district_type"]
        if dt in by_area:
            recs.append(by_area[dt])

        return recs[:5]

    def _calculate_purchasing_power(self, d: dict[str, Any]) -> float:
        """Purchasing power score 0-100."""
        sc = max(1, d.get("store_count", 1))
        sales_per_store = d["monthly_sales"] / sc
        tx_per_store = d.get("monthly_transactions", 0) / sc
        avg_ticket = sales_per_store / max(1, tx_per_store) if tx_per_store > 0 else 0

        sps_pctile = self._sales_percentile.get(d["district_code"], 0.5)
        ticket_score = min(1.0, max(0.0, (avg_ticket - 3000) / 5000))

        worker_total = d.get("worker_total", 0)
        w30 = d.get("worker_age_30", 0)
        w40 = d.get("worker_age_40", 0)
        worker_prime_ratio = (w30 + w40) / max(1, worker_total) if worker_total > 0 else 0

        resident_total = d.get("resident_total", 0)
        resident_score = min(1.0, resident_total / 2000)

        score = (
            sps_pctile * 30
            + ticket_score * 35
            + worker_prime_ratio * 20
            + resident_score * 15
        )
        return round(score, 1)

    def _determine_positioning(self, d: dict[str, Any]) -> tuple[str, str, float]:
        """Returns (positioning_name, positioning_detail, score)."""
        worker_total = d.get("worker_total", 0)
        ft_total = d.get("foot_traffic_total", 0)
        resident_total = d.get("resident_total", 0)

        sc = max(1, d.get("store_count", 1))
        tx_per_store = d.get("monthly_transactions", 0) / sc
        avg_ticket = (d["monthly_sales"] / sc) / max(1, tx_per_store) if tx_per_store > 0 else 0

        ft_20 = d.get("foot_traffic_age_20", 0)
        ft_30 = d.get("foot_traffic_age_30", 0)
        ft_40 = d.get("foot_traffic_age_40", 0)
        ft_denom = max(1, ft_total)
        ratio_20 = ft_20 / ft_denom
        ratio_30_40 = (ft_30 + ft_40) / ft_denom

        university = d.get("facility_university", 0)
        total_households = d.get("total_households", 0)

        purchasing_power = self._calculate_purchasing_power(d)

        # Use config positioning if available
        config_pos = self.config.get("POSITIONING_TYPES", {})
        if config_pos and isinstance(config_pos, dict):
            # Simple scoring for config-defined positioning types
            scores: dict[str, float] = {}
            for pos_name, pos_info in config_pos.items():
                if isinstance(pos_info, dict) and "weights" in pos_info:
                    score = 0.0
                    for feat, w in pos_info["weights"].items():
                        val = d.get(feat, 0)
                        if isinstance(val, (int, float)):
                            score += float(val) * float(w)
                    scores[pos_name] = score
            if scores:
                best, best_score = max(scores.items(), key=lambda item: item[1])
                desc = ""
                if isinstance(config_pos.get(best), dict):
                    desc = config_pos[best].get("desc", "")
                return (best, desc, round(best_score, 1))

        # Default positioning (카페 전용)
        scores_default: dict[str, float] = {}
        scores_default["프리미엄/감성"] = (
            (1.0 if purchasing_power > 60 else purchasing_power / 60) * 40
            + (1.0 if avg_ticket > 6000 else avg_ticket / 6000) * 35
            + ratio_30_40 * 25
        )
        peak_time = d.get("peak_time", "")
        scores_default["직장인 효율"] = (
            min(1.0, worker_total / 8000) * 45
            + (1.0 if peak_time in ("11-14", "06-11") else 0.3) * 30
            + ratio_30_40 * 25
        )
        scores_default["테이크아웃/저가"] = (
            min(1.0, ft_total / 800000) * 40
            + (1.0 if purchasing_power < 40 else max(0, (70 - purchasing_power) / 30)) * 35
            + (1.0 if d.get("facility_subway", 0) >= 1 else 0.3) * 25
        )
        scores_default["동네 커뮤니티"] = (
            min(1.0, resident_total / 1500) * 35
            + min(1.0, total_households / 800) * 30
            + ratio_30_40 * 20
            + (0.3 if d.get("district_type") == "골목상권" else 0.0) * 15
        )
        scores_default["학생/스터디"] = (
            ratio_20 * 40
            + min(1.0, university) * 35
            + (1.0 if purchasing_power < 50 else max(0, (70 - purchasing_power) / 20)) * 25
        )

        best, best_score = max(scores_default.items(), key=lambda item: item[1])

        details = {
            "프리미엄/감성": f"구매력 상위, 객단가 {avg_ticket:,.0f}원 → 시그니처 메뉴 차별화 유리",
            "직장인 효율": f"직장인 {worker_total:,}명, 피크 {peak_time} → 빠른 회전, 런치세트 추천",
            "테이크아웃/저가": f"유동인구 {ft_total:,}명, 교통 요지 → 속도·가격 경쟁력 필요",
            "동네 커뮤니티": f"상주인구 {resident_total:,}명, 가구 {total_households}세대 → 단골 전략, 편안한 분위기",
            "학생/스터디": f"20대 비율 {ratio_20*100:.0f}%, 대학 인접 → 공간 제공, 합리적 가격",
        }

        return (best, details.get(best, ""), round(best_score, 1))

    def _extract_key_factors(self, d: dict[str, Any]) -> list[str]:
        factors = []

        if d["survival_rate"] > 0.9:
            factors.append(f"높은 생존율 ({d['survival_rate'] * 100:.0f}%)")

        if d["monthly_sales"] > self.summary.get("avg_monthly_sales", 0):
            factors.append("평균 이상 매출")

        if d["store_count"] < 10:
            factors.append("적정 경쟁 수준")

        if d["new_stores"] > d["closed_stores"]:
            factors.append("성장 중인 상권")

        if d["district_type"] == "발달상권":
            factors.append("핵심 상업지구")
        elif d["district_type"] == "골목상권":
            factors.append("감성 골목상권")

        if d["female_ratio"] > 0.55:
            factors.append("여성 고객 다수")

        change_code = d.get("change_indicator_code", "")
        if change_code == "HH":
            factors.append("성장 상권 (매출↑ 점포↑)")
        elif change_code == "HL":
            factors.append("안정 상권 (매출↑ 점포↓)")

        ft = d.get("foot_traffic_total", 0)
        if ft > 0 and self._avg_foot_traffic > 0 and ft > self._avg_foot_traffic * 1.5:
            factors.append("유동인구 풍부")

        subway = d.get("facility_subway", 0)
        if subway >= 2:
            factors.append(f"지하철역 {subway}개 인접")
        elif subway == 1:
            factors.append("지하철역 인접")

        worker = d.get("worker_total", 0)
        if worker > 5000:
            factors.append("직장인구 밀집")

        transit_pctile = self._transit_percentiles.get(d["district_code"], 0.5)
        if transit_pctile > 0.8:
            subway = d.get("facility_subway", 0)
            bus = d.get("facility_bus_stop", 0)
            factors.append(f"교통 우수 (지하철 {subway}개역, 버스 {bus}개)")

        positioning, _, _ = self._determine_positioning(d)
        factors.append(f"포지셔닝: {positioning}")

        return factors[:6]

    def get_district_detail(self, code: str) -> Optional[dict[str, Any]]:
        """상권 상세 분석"""
        d = self._district_by_code.get(code)
        if not d:
            return None

        return {
            "basic": {
                "code": d["district_code"],
                "name": d["district_name"],
                "type": d["district_type"],
            },
            "sales": {
                "monthly": d["monthly_sales"],
                "transactions": d["monthly_transactions"],
                "avg_ticket": int(d["monthly_sales"] / max(1, d["monthly_transactions"])),
            },
            "time_breakdown": {
                "새벽(0-6시)": {"sales": d["time_00_06_sales"], "transactions": d["time_00_06_transactions"]},
                "아침(6-11시)": {"sales": d["time_06_11_sales"], "transactions": d["time_06_11_transactions"]},
                "점심(11-14시)": {"sales": d["time_11_14_sales"], "transactions": d["time_11_14_transactions"]},
                "오후(14-17시)": {"sales": d["time_14_17_sales"], "transactions": d["time_14_17_transactions"]},
                "저녁(17-21시)": {"sales": d["time_17_21_sales"], "transactions": d["time_17_21_transactions"]},
                "밤(21-24시)": {"sales": d["time_21_24_sales"], "transactions": d["time_21_24_transactions"]},
            },
            "day_breakdown": {
                "월": {"sales": d["mon_sales"], "transactions": d["mon_transactions"]},
                "화": {"sales": d["tue_sales"], "transactions": d["tue_transactions"]},
                "수": {"sales": d["wed_sales"], "transactions": d["wed_transactions"]},
                "목": {"sales": d["thu_sales"], "transactions": d["thu_transactions"]},
                "금": {"sales": d["fri_sales"], "transactions": d["fri_transactions"]},
                "토": {"sales": d["sat_sales"], "transactions": d["sat_transactions"]},
                "일": {"sales": d["sun_sales"], "transactions": d["sun_transactions"]},
            },
            "customer_breakdown": {
                "gender": {
                    "male": {"sales": d["male_sales"], "transactions": d["male_transactions"]},
                    "female": {"sales": d["female_sales"], "transactions": d["female_transactions"]},
                },
                "age": {
                    "10대": {"sales": d["age_10_sales"], "transactions": d["age_10_transactions"]},
                    "20대": {"sales": d["age_20_sales"], "transactions": d["age_20_transactions"]},
                    "30대": {"sales": d["age_30_sales"], "transactions": d["age_30_transactions"]},
                    "40대": {"sales": d["age_40_sales"], "transactions": d["age_40_transactions"]},
                    "50대": {"sales": d["age_50_sales"], "transactions": d["age_50_transactions"]},
                    "60대+": {"sales": d["age_60_sales"], "transactions": d["age_60_transactions"]},
                },
            },
            "competition": {
                "total_stores": d["store_count"],
                "new_stores": d["new_stores"],
                "closed_stores": d["closed_stores"],
                "franchise_stores": d["franchise_stores"],
                "survival_rate": d["survival_rate"],
            },
            "insights": {
                "peak_time": d["peak_time"],
                "peak_day": d["peak_day"],
                "main_age_group": d["main_age_group"],
                "weekday_ratio": d["weekday_ratio"],
                "weekend_ratio": d["weekend_ratio"],
            },
        }

    def get_summary(self) -> dict[str, Any]:
        """전체 데이터 요약"""
        return self.summary

    def get_trends(self) -> list[dict[str, Any]]:
        """6년 트렌드"""
        return self.summary.get("yearly_trends", [])

    def get_districts_for_comparison(self, district_codes: list[str]) -> list[dict[str, Any]]:
        """
        복수 상권 비교용 데이터 조회

        Args:
            district_codes: 비교할 상권 코드 리스트 (최대 3개 권장)

        Returns:
            각 상권의 상세 데이터 리스트
        """
        results = []
        for code in district_codes[:3]:  # 최대 3개까지만
            district = self._district_by_code.get(code)
            if district:
                results.append(district)
        return results


# ─── Registry Pattern ──────────────────────────────────────────────────────
_registry: dict[str, DataService] = {}


def get_data_service(industry_code: str = DEFAULT_INDUSTRY) -> DataService:
    """Get or create a DataService for the given industry code."""
    if industry_code not in _registry:
        _registry[industry_code] = DataService(industry_code)
    return _registry[industry_code]
