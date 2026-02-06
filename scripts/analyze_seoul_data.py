"""
서울시 커피숍 상권 데이터 분석 스크립트 (풀버전)
- 55개 필드 전체 반영
- 시간대별, 요일별, 연령대별 상세 분석
- 6년 트렌드 분석
"""

import json
import pandas as pd
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path(__file__).parent.parent / "data" / "seoul"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_all_data():
    """전체 데이터 로드"""
    # 매출 데이터
    all_sales = []
    for f in sorted(DATA_DIR.glob("sales_*.json")):
        with open(f, "r", encoding="utf-8") as file:
            all_sales.extend(json.load(file))

    # 점포 데이터
    all_stores = []
    for f in sorted(DATA_DIR.glob("stores_*.json")):
        with open(f, "r", encoding="utf-8") as file:
            all_stores.extend(json.load(file))

    sales_df = pd.DataFrame(all_sales)
    stores_df = pd.DataFrame(all_stores)

    print(f"매출 데이터: {len(sales_df):,}건")
    print(f"점포 데이터: {len(stores_df):,}건")

    return sales_df, stores_df


def process_latest_quarter(sales_df, stores_df):
    """최신 분기 데이터 가공 (풀버전)"""
    latest_quarter = "20253"

    latest_sales = sales_df[sales_df["STDR_YYQU_CD"] == latest_quarter].copy()
    latest_stores = stores_df[stores_df["STDR_YYQU_CD"] == latest_quarter].copy()

    # 상권별 데이터 병합
    merged = latest_sales.merge(
        latest_stores[["TRDAR_CD", "STOR_CO", "OPBIZ_STOR_CO", "CLSBIZ_STOR_CO", "FRC_STOR_CO"]],
        on="TRDAR_CD",
        how="left",
    )

    # 생존율 계산 (2년 전 대비)
    q_2023 = stores_df[stores_df["STDR_YYQU_CD"] == "20233"][["TRDAR_CD", "STOR_CO"]].copy()
    q_2023.columns = ["TRDAR_CD", "STOR_CO_2023"]
    merged = merged.merge(q_2023, on="TRDAR_CD", how="left")
    merged["survival_rate"] = merged["STOR_CO"] / merged["STOR_CO_2023"].replace(0, 1)
    merged["survival_rate"] = merged["survival_rate"].fillna(1.0)

    # 결과 데이터 구성 (55개 필드 풀버전)
    result = []
    for _, row in merged.iterrows():
        monthly_sales = row.get("THSMON_SELNG_AMT", 0) or 0

        district = {
            # 기본 정보
            "district_code": row["TRDAR_CD"],
            "district_name": row["TRDAR_CD_NM"],
            "district_type_code": row["TRDAR_SE_CD"],
            "district_type": row["TRDAR_SE_CD_NM"],
            # 매출 기본
            "monthly_sales": int(monthly_sales),
            "monthly_transactions": int(row.get("THSMON_SELNG_CO", 0) or 0),
            # 주중/주말
            "weekday_sales": int(row.get("MDWK_SELNG_AMT", 0) or 0),
            "weekend_sales": int(row.get("WKEND_SELNG_AMT", 0) or 0),
            "weekday_transactions": int(row.get("MDWK_SELNG_CO", 0) or 0),
            "weekend_transactions": int(row.get("WKEND_SELNG_CO", 0) or 0),
            # 요일별 매출
            "mon_sales": int(row.get("MON_SELNG_AMT", 0) or 0),
            "tue_sales": int(row.get("TUES_SELNG_AMT", 0) or 0),
            "wed_sales": int(row.get("WED_SELNG_AMT", 0) or 0),
            "thu_sales": int(row.get("THUR_SELNG_AMT", 0) or 0),
            "fri_sales": int(row.get("FRI_SELNG_AMT", 0) or 0),
            "sat_sales": int(row.get("SAT_SELNG_AMT", 0) or 0),
            "sun_sales": int(row.get("SUN_SELNG_AMT", 0) or 0),
            # 요일별 거래건수
            "mon_transactions": int(row.get("MON_SELNG_CO", 0) or 0),
            "tue_transactions": int(row.get("TUES_SELNG_CO", 0) or 0),
            "wed_transactions": int(row.get("WED_SELNG_CO", 0) or 0),
            "thu_transactions": int(row.get("THUR_SELNG_CO", 0) or 0),
            "fri_transactions": int(row.get("FRI_SELNG_CO", 0) or 0),
            "sat_transactions": int(row.get("SAT_SELNG_CO", 0) or 0),
            "sun_transactions": int(row.get("SUN_SELNG_CO", 0) or 0),
            # 시간대별 매출
            "time_00_06_sales": int(row.get("TMZON_00_06_SELNG_AMT", 0) or 0),
            "time_06_11_sales": int(row.get("TMZON_06_11_SELNG_AMT", 0) or 0),
            "time_11_14_sales": int(row.get("TMZON_11_14_SELNG_AMT", 0) or 0),
            "time_14_17_sales": int(row.get("TMZON_14_17_SELNG_AMT", 0) or 0),
            "time_17_21_sales": int(row.get("TMZON_17_21_SELNG_AMT", 0) or 0),
            "time_21_24_sales": int(row.get("TMZON_21_24_SELNG_AMT", 0) or 0),
            # 시간대별 거래건수
            "time_00_06_transactions": int(row.get("TMZON_00_06_SELNG_CO", 0) or 0),
            "time_06_11_transactions": int(row.get("TMZON_06_11_SELNG_CO", 0) or 0),
            "time_11_14_transactions": int(row.get("TMZON_11_14_SELNG_CO", 0) or 0),
            "time_14_17_transactions": int(row.get("TMZON_14_17_SELNG_CO", 0) or 0),
            "time_17_21_transactions": int(row.get("TMZON_17_21_SELNG_CO", 0) or 0),
            "time_21_24_transactions": int(row.get("TMZON_21_24_SELNG_CO", 0) or 0),
            # 성별
            "male_sales": int(row.get("ML_SELNG_AMT", 0) or 0),
            "female_sales": int(row.get("FML_SELNG_AMT", 0) or 0),
            "male_transactions": int(row.get("ML_SELNG_CO", 0) or 0),
            "female_transactions": int(row.get("FML_SELNG_CO", 0) or 0),
            # 연령대별 매출
            "age_10_sales": int(row.get("AGRDE_10_SELNG_AMT", 0) or 0),
            "age_20_sales": int(row.get("AGRDE_20_SELNG_AMT", 0) or 0),
            "age_30_sales": int(row.get("AGRDE_30_SELNG_AMT", 0) or 0),
            "age_40_sales": int(row.get("AGRDE_40_SELNG_AMT", 0) or 0),
            "age_50_sales": int(row.get("AGRDE_50_SELNG_AMT", 0) or 0),
            "age_60_sales": int(row.get("AGRDE_60_ABOVE_SELNG_AMT", 0) or 0),
            # 연령대별 거래건수
            "age_10_transactions": int(row.get("AGRDE_10_SELNG_CO", 0) or 0),
            "age_20_transactions": int(row.get("AGRDE_20_SELNG_CO", 0) or 0),
            "age_30_transactions": int(row.get("AGRDE_30_SELNG_CO", 0) or 0),
            "age_40_transactions": int(row.get("AGRDE_40_SELNG_CO", 0) or 0),
            "age_50_transactions": int(row.get("AGRDE_50_SELNG_CO", 0) or 0),
            "age_60_transactions": int(row.get("AGRDE_60_ABOVE_SELNG_CO", 0) or 0),
            # 점포 현황
            "store_count": int(row.get("STOR_CO", 0) or 0),
            "new_stores": int(row.get("OPBIZ_STOR_CO", 0) or 0),
            "closed_stores": int(row.get("CLSBIZ_STOR_CO", 0) or 0),
            "franchise_stores": int(row.get("FRC_STOR_CO", 0) or 0),
            # 생존율
            "survival_rate": round(row.get("survival_rate", 1.0), 4),
        }

        # 비율 계산 (0으로 나누기 방지)
        if monthly_sales > 0:
            district["weekday_ratio"] = round(district["weekday_sales"] / monthly_sales, 4)
            district["weekend_ratio"] = round(district["weekend_sales"] / monthly_sales, 4)
            district["male_ratio"] = round(district["male_sales"] / monthly_sales, 4)
            district["female_ratio"] = round(district["female_sales"] / monthly_sales, 4)
            district["peak_time"] = get_peak_time(district)
            district["peak_day"] = get_peak_day(district)
            district["main_age_group"] = get_main_age_group(district)
        else:
            district["weekday_ratio"] = 0
            district["weekend_ratio"] = 0
            district["male_ratio"] = 0
            district["female_ratio"] = 0
            district["peak_time"] = "11-14"
            district["peak_day"] = "금"
            district["main_age_group"] = "30대"

        result.append(district)

    return result


def get_peak_time(d):
    """피크 시간대 계산"""
    times = {
        "00-06": d["time_00_06_sales"],
        "06-11": d["time_06_11_sales"],
        "11-14": d["time_11_14_sales"],
        "14-17": d["time_14_17_sales"],
        "17-21": d["time_17_21_sales"],
        "21-24": d["time_21_24_sales"],
    }
    return max(times, key=times.get)


def get_peak_day(d):
    """피크 요일 계산"""
    days = {
        "월": d["mon_sales"],
        "화": d["tue_sales"],
        "수": d["wed_sales"],
        "목": d["thu_sales"],
        "금": d["fri_sales"],
        "토": d["sat_sales"],
        "일": d["sun_sales"],
    }
    return max(days, key=days.get)


def get_main_age_group(d):
    """주요 고객층 계산"""
    ages = {
        "10대": d["age_10_sales"],
        "20대": d["age_20_sales"],
        "30대": d["age_30_sales"],
        "40대": d["age_40_sales"],
        "50대": d["age_50_sales"],
        "60대+": d["age_60_sales"],
    }
    return max(ages, key=ages.get)


def calculate_trends(sales_df, stores_df):
    """6년 트렌드 계산"""
    # 연도별 매출 트렌드
    sales_df["year"] = sales_df["STDR_YYQU_CD"].str[:4]
    yearly_sales = (
        sales_df.groupby("year")
        .agg({"THSMON_SELNG_AMT": "sum", "TRDAR_CD": "nunique"})
        .reset_index()
    )
    yearly_sales.columns = ["year", "total_sales", "district_count"]

    # 연도별 점포 트렌드
    stores_df["year"] = stores_df["STDR_YYQU_CD"].str[:4]
    yearly_stores = (
        stores_df.groupby("year")
        .agg(
            {
                "STOR_CO": "sum",
                "OPBIZ_STOR_CO": "sum",
                "CLSBIZ_STOR_CO": "sum",
                "FRC_STOR_CO": "sum",
            }
        )
        .reset_index()
    )
    yearly_stores.columns = [
        "year",
        "total_stores",
        "new_stores",
        "closed_stores",
        "franchise_stores",
    ]

    trends = yearly_sales.merge(yearly_stores, on="year")

    # 기준년도 대비 변화율
    base_sales = trends[trends["year"] == "2019"]["total_sales"].values[0]
    base_stores = trends[trends["year"] == "2019"]["total_stores"].values[0]

    result = []
    for _, row in trends.iterrows():
        result.append(
            {
                "year": row["year"],
                "total_sales": int(row["total_sales"]),
                "sales_growth": round((row["total_sales"] / base_sales - 1) * 100, 1),
                "total_stores": int(row["total_stores"]),
                "stores_growth": round((row["total_stores"] / base_stores - 1) * 100, 1),
                "new_stores": int(row["new_stores"]),
                "closed_stores": int(row["closed_stores"]),
                "net_change": int(row["new_stores"] - row["closed_stores"]),
                "franchise_stores": int(row["franchise_stores"]),
            }
        )

    return result


def create_summary(districts, trends):
    """요약 통계 생성"""
    total_sales = sum(d["monthly_sales"] for d in districts)
    total_stores = sum(d["store_count"] for d in districts)

    # 시간대별 전체 통계
    time_totals = {
        "00-06": sum(d["time_00_06_sales"] for d in districts),
        "06-11": sum(d["time_06_11_sales"] for d in districts),
        "11-14": sum(d["time_11_14_sales"] for d in districts),
        "14-17": sum(d["time_14_17_sales"] for d in districts),
        "17-21": sum(d["time_17_21_sales"] for d in districts),
        "21-24": sum(d["time_21_24_sales"] for d in districts),
    }
    time_total = sum(time_totals.values())

    # 요일별 전체 통계
    day_totals = {
        "월": sum(d["mon_sales"] for d in districts),
        "화": sum(d["tue_sales"] for d in districts),
        "수": sum(d["wed_sales"] for d in districts),
        "목": sum(d["thu_sales"] for d in districts),
        "금": sum(d["fri_sales"] for d in districts),
        "토": sum(d["sat_sales"] for d in districts),
        "일": sum(d["sun_sales"] for d in districts),
    }
    day_total = sum(day_totals.values())

    # 연령대별 전체 통계
    age_totals = {
        "10대": sum(d["age_10_sales"] for d in districts),
        "20대": sum(d["age_20_sales"] for d in districts),
        "30대": sum(d["age_30_sales"] for d in districts),
        "40대": sum(d["age_40_sales"] for d in districts),
        "50대": sum(d["age_50_sales"] for d in districts),
        "60대+": sum(d["age_60_sales"] for d in districts),
    }
    age_total = sum(age_totals.values())

    # 성별 통계
    male_total = sum(d["male_sales"] for d in districts)
    female_total = sum(d["female_sales"] for d in districts)
    gender_total = male_total + female_total

    # 상권 유형별 통계
    type_stats = defaultdict(lambda: {"count": 0, "sales": 0, "stores": 0})
    for d in districts:
        t = d["district_type"]
        type_stats[t]["count"] += 1
        type_stats[t]["sales"] += d["monthly_sales"]
        type_stats[t]["stores"] += d["store_count"]

    return {
        "data_quarter": "2025Q3",
        "total_districts": len(districts),
        "total_stores": total_stores,
        "total_monthly_sales": total_sales,
        "avg_monthly_sales": int(total_sales / len(districts)) if districts else 0,
        "avg_survival_rate": round(sum(d["survival_rate"] for d in districts) / len(districts), 4)
        if districts
        else 0,
        # 시간대별 비율
        "time_distribution": {
            k: round(v / time_total * 100, 1) if time_total > 0 else 0
            for k, v in time_totals.items()
        },
        # 요일별 비율
        "day_distribution": {
            k: round(v / day_total * 100, 1) if day_total > 0 else 0 for k, v in day_totals.items()
        },
        # 연령대별 비율
        "age_distribution": {
            k: round(v / age_total * 100, 1) if age_total > 0 else 0 for k, v in age_totals.items()
        },
        # 성별 비율
        "gender_distribution": {
            "male": round(male_total / gender_total * 100, 1) if gender_total > 0 else 0,
            "female": round(female_total / gender_total * 100, 1) if gender_total > 0 else 0,
        },
        # 상권 유형별
        "district_types": {k: v["count"] for k, v in type_stats.items()},
        "district_type_stats": dict(type_stats),
        # 6년 트렌드
        "yearly_trends": trends,
    }


def main():
    print("=" * 60)
    print("서울시 커피숍 상권 데이터 분석 (풀버전)")
    print("=" * 60)

    # 1. 데이터 로드
    sales_df, stores_df = load_all_data()

    # 2. 최신 분기 가공
    print("\n최신 분기 데이터 가공 중...")
    districts = process_latest_quarter(sales_df, stores_df)
    print(f"  → {len(districts)}개 상권 처리 완료")

    # 3. 트렌드 계산
    print("\n6년 트렌드 분석 중...")
    trends = calculate_trends(sales_df, stores_df)
    print(f"  → {len(trends)}개 연도 처리 완료")

    # 4. 요약 통계
    print("\n요약 통계 생성 중...")
    summary = create_summary(districts, trends)

    # 5. 저장
    with open(OUTPUT_DIR / "coffee_districts.json", "w", encoding="utf-8") as f:
        json.dump(districts, f, ensure_ascii=False, indent=2)
    print(f"\n저장: coffee_districts.json ({len(districts)}개 상권)")

    with open(OUTPUT_DIR / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"저장: summary.json")

    # 결과 출력
    print("\n" + "=" * 60)
    print("처리 완료!")
    print(f"  - 상권 수: {summary['total_districts']}개")
    print(f"  - 점포 수: {summary['total_stores']}개")
    print(f"  - 평균 월매출: {summary['avg_monthly_sales']:,}원")
    print(f"  - 평균 생존율: {summary['avg_survival_rate'] * 100:.1f}%")
    print(f"  - 필드 수: {len(districts[0].keys())}개")
    print("=" * 60)


if __name__ == "__main__":
    main()
