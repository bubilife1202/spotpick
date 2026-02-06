"""
Data Service - 서울시 상권 데이터 기반 추천 서비스 (풀버전)
64개 필드 전체 활용
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional, Tuple, List


class DataService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_data()
        return cls._instance

    def _load_data(self):
        """데이터 로드"""
        data_dir = Path(__file__).parent.parent.parent / "data" / "processed"

        with open(data_dir / "coffee_districts.json", encoding="utf-8") as f:
            self.districts = json.load(f)

        with open(data_dir / "summary.json", encoding="utf-8") as f:
            self.summary = json.load(f)

        # 상권 인덱싱
        self._district_by_code = {d["district_code"]: d for d in self.districts}
        self._district_by_name = {d["district_name"]: d for d in self.districts}

        print(
            f"[DataService] 로드 완료: {len(self.districts)}개 상권, {len(self.districts[0].keys())}개 필드"
        )

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
    ) -> Tuple[List[dict], int]:
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

    def get_district(self, code: str) -> Optional[dict]:
        """상권 상세 조회"""
        return self._district_by_code.get(code)

    def get_district_by_name(self, name: str) -> Optional[dict]:
        """상권명으로 조회"""
        return self._district_by_name.get(name)

    def search_districts(self, query: str, limit: int = 10) -> list[dict]:
        """상권 검색"""
        results = []
        query_lower = query.lower()

        for d in self.districts:
            if query_lower in d["district_name"].lower():
                results.append(d)
                if len(results) >= limit:
                    break

        return results

    def get_recommendations(
        self,
        budget_min: int,
        budget_max: int,
        category: str = "coffee",
        preferred_district: Optional[str] = None,
        preferred_area_type: Optional[str] = None,
        min_survival_rate: float = 0.0,
        top_n: int = 10,
    ) -> list[dict]:
        """예산과 조건에 맞는 최적의 창업 위치 추천"""
        candidates = []

        for d in self.districts:
            # 예상 임대료 계산 (신규 점포 관점에서 "점포당 평균 매출"의 7% 추정)
            # - district.monthly_sales 는 상권 내 전체 점포 합산 매출이라 그대로 쓰면 월세가 과대 추정됨
            sales_per_store = int(d["monthly_sales"] / max(1, d.get("store_count", 1)))
            estimated_rent = int(sales_per_store * 0.07 / 10000) * 10000
            estimated_rent = max(1500000, min(estimated_rent, 15000000))

            # 예산 필터: "최대 예산"은 하드 필터, "최소 예산"은 소프트 선호로만 사용
            # - 실제 사용자는 보통 "OO만원 이하"처럼 상한을 기준으로 판단하는 경우가 많음
            if estimated_rent > budget_max:
                continue

            # 지역 필터
            if preferred_district and preferred_district not in d["district_name"]:
                continue

            # 상권 유형 필터
            if preferred_area_type and d["district_type"] != preferred_area_type:
                continue

            # 생존율 필터
            if d["survival_rate"] < min_survival_rate:
                continue

            # 성공 확률 계산
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

        # 성공 확률 + 예산 적합도(소프트) 순 정렬
        candidates.sort(key=lambda c: (c["score"], c["success_probability"]), reverse=True)

        # 결과 포맷팅
        results = []
        for rank, c in enumerate(candidates[:top_n], 1):
            d = c["district"]
            sales_per_store = int(d["monthly_sales"] / max(1, d.get("store_count", 1)))
            results.append(
                {
                    "rank": rank,
                    "district_code": d["district_code"],
                    "district_name": d["district_name"],
                    "district_type": d["district_type"],
                    "address": f"서울특별시 {d['district_name']}",
                    # 핵심 지표
                    "success_probability": c["success_probability"],
                    "estimated_monthly_rent": c["estimated_rent"],
                    # 점포당 평균 매출(신규 점포 기준)로 제공
                    "estimated_monthly_sales": sales_per_store,
                    "survival_rate_2y": d["survival_rate"],
                    # 시간대 분석
                    "time_analysis": {
                        "peak_time": d["peak_time"],
                        "time_00_06": round(
                            d["time_00_06_sales"] / max(1, d["monthly_sales"]) * 100, 1
                        ),
                        "time_06_11": round(
                            d["time_06_11_sales"] / max(1, d["monthly_sales"]) * 100, 1
                        ),
                        "time_11_14": round(
                            d["time_11_14_sales"] / max(1, d["monthly_sales"]) * 100, 1
                        ),
                        "time_14_17": round(
                            d["time_14_17_sales"] / max(1, d["monthly_sales"]) * 100, 1
                        ),
                        "time_17_21": round(
                            d["time_17_21_sales"] / max(1, d["monthly_sales"]) * 100, 1
                        ),
                        "time_21_24": round(
                            d["time_21_24_sales"] / max(1, d["monthly_sales"]) * 100, 1
                        ),
                    },
                    # 요일 분석
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
                    # 고객 분석
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
                    # 경쟁 현황
                    "competition": {
                        "store_count": d["store_count"],
                        "new_stores": d["new_stores"],
                        "closed_stores": d["closed_stores"],
                        "franchise_stores": d["franchise_stores"],
                        "franchise_ratio": round(
                            d["franchise_stores"] / max(1, d["store_count"]) * 100, 1
                        ),
                    },
                    # 리스크 및 추천
                    "risk_factors": c["risk_factors"],
                    "recommendations": c["recommendations"],
                    "key_success_factors": c["key_success_factors"],
                }
            )

        return results

    def _calculate_success_probability(self, d: dict) -> float:
        """성공 확률 계산"""
        base = d["survival_rate"]

        # 매출 보정
        avg_sales = self.summary["avg_monthly_sales"]
        if d["monthly_sales"] > avg_sales * 1.5:
            base += 0.05
        elif d["monthly_sales"] < avg_sales * 0.5:
            base -= 0.05

        # 경쟁 보정
        if d["store_count"] > 20:
            base -= 0.1
        elif d["store_count"] < 5:
            base += 0.05

        # 폐업 트렌드 보정
        if d["closed_stores"] > d["new_stores"]:
            base -= 0.05

        # 상권 유형 보정
        if d["district_type"] == "발달상권":
            base += 0.03
        elif d["district_type"] == "관광특구":
            base += 0.02

        return round(max(0.1, min(0.95, base)), 2)

    def _identify_risks(self, d: dict) -> list[str]:
        """리스크 식별"""
        risks = []

        if d["store_count"] > 20:
            risks.append(f"높은 경쟁 밀도 (커피숍 {d['store_count']}개)")

        if d["survival_rate"] < 0.7:
            risks.append(f"평균 이하 생존율 ({d['survival_rate'] * 100:.0f}%)")

        if d["closed_stores"] > d["new_stores"]:
            risks.append(f"폐업 증가 추세 (폐업 {d['closed_stores']}개 > 개업 {d['new_stores']}개)")

        franchise_ratio = d["franchise_stores"] / max(1, d["store_count"])
        if franchise_ratio > 0.6:
            risks.append(f"프랜차이즈 밀집 ({franchise_ratio * 100:.0f}%)")

        if d["weekend_ratio"] < 0.2:
            risks.append("주말 매출 부진 (주말 비중 20% 미만)")

        return risks

    def _generate_recommendations(self, d: dict) -> list[str]:
        """맞춤 추천 생성"""
        recs = []

        # 시간대 기반 추천
        peak = d["peak_time"]
        if peak == "11-14":
            recs.append("점심 피크 상권 → 오전 10시 오픈, 빠른 회전율 전략")
        elif peak == "14-17":
            recs.append("오후 피크 상권 → 디저트/음료 세트 메뉴 강화")
        elif peak == "17-21":
            recs.append("저녁 피크 상권 → 저녁 시간대 특화 (와인/맥주 등)")

        # 요일 기반 추천
        if d["weekday_ratio"] > 0.75:
            recs.append("주중 매출 집중 → 평일 런치 세트, 직장인 타겟")
        elif d["weekend_ratio"] > 0.35:
            recs.append("주말 매출 비중 높음 → 브런치 메뉴, 가족 고객 공략")

        # 고객층 기반 추천
        main_age = d["main_age_group"]
        if "20" in main_age:
            recs.append("20대 주요 고객 → SNS 마케팅, 트렌디한 인테리어")
        elif "30" in main_age:
            recs.append("30대 주요 고객 → 프리미엄 원두, 작업 공간 제공")
        elif "40" in main_age or "50" in main_age:
            recs.append("40-50대 주요 고객 → 편안한 분위기, 품질 중심")

        # 경쟁 기반 추천
        if d["store_count"] > 15:
            recs.append("경쟁 과다 → 시그니처 메뉴, 차별화 필수")

        # 상권 유형 기반 추천
        if d["district_type"] == "골목상권":
            recs.append("골목상권 특성 → 단골 확보, 지역 커뮤니티 연계")

        return recs[:5]

    def _extract_key_factors(self, d: dict) -> list[str]:
        """핵심 성공 요인 추출"""
        factors = []

        if d["survival_rate"] > 0.9:
            factors.append(f"높은 생존율 ({d['survival_rate'] * 100:.0f}%)")

        if d["monthly_sales"] > self.summary["avg_monthly_sales"]:
            factors.append("평균 이상 매출")

        if d["store_count"] < 10:
            factors.append("적정 경쟁 수준")

        if d["new_stores"] > d["closed_stores"]:
            factors.append("성장 중인 상권")

        if d["district_type"] == "발달상권":
            factors.append("핵심 상업지구")
        elif d["district_type"] == "골목상권":
            factors.append("감성 골목상권")

        # 고객층 특성
        if d["female_ratio"] > 0.55:
            factors.append("여성 고객 다수")

        return factors[:5]

    def get_district_detail(self, code: str) -> Optional[dict]:
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
                "새벽(0-6시)": {
                    "sales": d["time_00_06_sales"],
                    "transactions": d["time_00_06_transactions"],
                },
                "아침(6-11시)": {
                    "sales": d["time_06_11_sales"],
                    "transactions": d["time_06_11_transactions"],
                },
                "점심(11-14시)": {
                    "sales": d["time_11_14_sales"],
                    "transactions": d["time_11_14_transactions"],
                },
                "오후(14-17시)": {
                    "sales": d["time_14_17_sales"],
                    "transactions": d["time_14_17_transactions"],
                },
                "저녁(17-21시)": {
                    "sales": d["time_17_21_sales"],
                    "transactions": d["time_17_21_transactions"],
                },
                "밤(21-24시)": {
                    "sales": d["time_21_24_sales"],
                    "transactions": d["time_21_24_transactions"],
                },
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
                    "female": {
                        "sales": d["female_sales"],
                        "transactions": d["female_transactions"],
                    },
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

    def get_summary(self) -> dict:
        """전체 데이터 요약"""
        return self.summary

    def get_trends(self) -> list[dict]:
        """6년 트렌드"""
        return self.summary.get("yearly_trends", [])


def get_data_service() -> DataService:
    return DataService()
