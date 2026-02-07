"""
KREI 외식업체경영실태조사 2023 원시자료 전처리 스크립트

입력: /tmp/krei_rawdata_2023.xlsx (3,077건, 511컬럼)
출력: data/krei/krei_2023_processed.json

업종별 · 상권유형별 · 지역별 집계 데이터를 생성한다.
"""

from __future__ import annotations

import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

import openpyxl

# ---------------------------------------------------------------------------
# 경로
# ---------------------------------------------------------------------------
INPUT_FILE = Path("/tmp/krei_rawdata_2023.xlsx")
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "krei"
OUTPUT_FILE = OUTPUT_DIR / "krei_2023_processed.json"

# ---------------------------------------------------------------------------
# 컬럼 인덱스 (0-based, row 1 = variable names)
# ---------------------------------------------------------------------------
COL = {
    "weight": 1,
    "sido": 4,
    "industry": 6,      # a3 — 업종 (string label)
    "hansik_sub": 7,     # a3a — 한식 세분류 (string label)
    "area_pyeong": 20,   # b3a2 — 영업면적(평)
    "district_type": 21, # b4 — 상권분류
    "deposit": 28,       # b7a1et — 보증금(만원)
    "monthly_rent": 30,  # b7a2et — 월세(만원)
    "invest_total": 54,  # b14et — 총투자(만원)
    "interior": 56,      # b14aet — 인테리어(만원)
    "kitchen": 58,       # b14bet — 주방기기(만원)
    "ticket": 172,       # b26 — 객단가(원)
    "sales": 181,        # c1a1 — 월매출(만원)
    "food_pct": 192,     # c1b3 — 식재료비(%)
    "labor_pct": 193,    # c1b4 — 인건비(%)
    "rent_pct": 194,     # c1b5 — 임차료(%)
    "profit_pct": 200,   # c1b11 — 영업이익(%)
}

# ---------------------------------------------------------------------------
# 매핑 테이블
# ---------------------------------------------------------------------------

# 업종 string → CS코드
INDUSTRY_MAP: dict[str, str] = {
    "한식 음식점업": "CS100001",
    "중식 음식점업": "CS100002",
    "일식 음식점업": "CS100003",
    "서양식 음식점업": "CS100004",
    "제과점업": "CS100005",
    "피자・햄버거・샌드위치 및 유사 음식점업": "CS100006",
    "치킨 전문점": "CS100007",
    "김밥 및 기타 간이 음식점업": "CS100008",
    "기타 주점업": "CS100009",
    "일반 유흥 주점업": "CS100009",
    "생맥주 전문점": "CS100009",
    "무도 유흥 주점업": "CS100009",
    "커피 전문점": "CS100010",
    "기타 비알코올 음료점업": "CS100010",
}

# 한식 세분류 string → sub_category key
HANSIK_SUB_MAP: dict[str, str] = {
    "한식 일반 음식점업": "한식일반",
    "한식 면 요리 전문점": "면요리",
    "한식 육류 요리 전문점": "육류",
    "한식 해산물 요리 전문점": "해산물",
}

# 상권유형 string → 우리 4유형
DISTRICT_TYPE_MAP: dict[str, str] = {
    "주거지": "골목상권",
    "역세권": "발달상권",
    "일반 상업지": "발달상권",
    "유흥 상업지": "발달상권",
    "오피스가": "발달상권",
    "대학 및 학원가": "골목상권",
    "교외/휴양지 등": "관광특구",
    "기타": "골목상권",
}

INDUSTRY_NAMES: dict[str, str] = {
    "CS100001": "한식",
    "CS100002": "중식",
    "CS100003": "일식",
    "CS100004": "서양식",
    "CS100005": "제과제빵",
    "CS100006": "패스트푸드",
    "CS100007": "치킨",
    "CS100008": "분식",
    "CS100009": "주점",
    "CS100010": "카페",
}


# ---------------------------------------------------------------------------
# 유틸리티
# ---------------------------------------------------------------------------

def safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        v = float(val)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except (ValueError, TypeError):
        return None


def weighted_mean(values: list[float], weights: list[float]) -> float | None:
    if not values or not weights or len(values) != len(weights):
        return None
    total_w = sum(weights)
    if total_w <= 0:
        return None
    return sum(v * w for v, w in zip(values, weights)) / total_w


def simple_mean(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


def percentiles(values: list[float]) -> dict[str, float] | None:
    if len(values) < 3:
        return None
    s = sorted(values)
    n = len(s)
    return {
        "p25": s[max(0, int(n * 0.25))],
        "median": s[max(0, int(n * 0.50))],
        "p75": s[max(0, int(n * 0.75))],
    }


# ---------------------------------------------------------------------------
# 레코드 파싱
# ---------------------------------------------------------------------------

def parse_row(vals: list) -> dict[str, Any] | None:
    """단일 행을 딕셔너리로 변환. 매핑 안 되면 None."""
    industry_label = vals[COL["industry"]]
    industry_code = INDUSTRY_MAP.get(str(industry_label or "").strip())
    if not industry_code:
        return None

    weight = safe_float(vals[COL["weight"]])
    if weight is None or weight <= 0:
        return None

    sido = vals[COL["sido"]]
    is_seoul = (sido == 1)

    hansik_label = vals[COL["hansik_sub"]]
    hansik_sub = HANSIK_SUB_MAP.get(str(hansik_label or "").strip()) if hansik_label else None

    dt_label = str(vals[COL["district_type"]] or "").strip()
    district_type = DISTRICT_TYPE_MAP.get(dt_label, "골목상권")

    return {
        "industry_code": industry_code,
        "hansik_sub": hansik_sub,
        "is_seoul": is_seoul,
        "district_type": district_type,
        "weight": weight,
        "area_pyeong": safe_float(vals[COL["area_pyeong"]]),
        "deposit": safe_float(vals[COL["deposit"]]),
        "monthly_rent": safe_float(vals[COL["monthly_rent"]]),
        "invest_total": safe_float(vals[COL["invest_total"]]),
        "interior": safe_float(vals[COL["interior"]]),
        "kitchen": safe_float(vals[COL["kitchen"]]),
        "ticket": safe_float(vals[COL["ticket"]]),
        "sales": safe_float(vals[COL["sales"]]),
        "food_pct": safe_float(vals[COL["food_pct"]]),
        "labor_pct": safe_float(vals[COL["labor_pct"]]),
        "rent_pct": safe_float(vals[COL["rent_pct"]]),
        "profit_pct": safe_float(vals[COL["profit_pct"]]),
    }


# ---------------------------------------------------------------------------
# 집계 함수
# ---------------------------------------------------------------------------

GroupKey = tuple  # (industry_code, sub_category_or_None, seoul_flag, district_type_or_None)


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """레코드 리스트에서 집계 통계를 생성."""

    # --- 비율 데이터: 단순 평균 ---
    food_pcts = [r["food_pct"] for r in records if r["food_pct"] is not None]
    labor_pcts = [r["labor_pct"] for r in records if r["labor_pct"] is not None]
    rent_pcts = [r["rent_pct"] for r in records if r["rent_pct"] is not None]
    profit_pcts = [r["profit_pct"] for r in records if r["profit_pct"] is not None]

    # --- 금액 데이터: 가중 평균 ---
    # 월세
    rent_vals = [(r["monthly_rent"], r["weight"]) for r in records if r["monthly_rent"] is not None]
    rent_values = [v for v, _ in rent_vals]
    rent_weights = [w for _, w in rent_vals]

    # 보증금
    dep_vals = [(r["deposit"], r["weight"]) for r in records if r["deposit"] is not None]

    # 총투자
    inv_vals = [(r["invest_total"], r["weight"]) for r in records if r["invest_total"] is not None]
    int_vals = [(r["interior"], r["weight"]) for r in records if r["interior"] is not None]
    kit_vals = [(r["kitchen"], r["weight"]) for r in records if r["kitchen"] is not None]

    # 객단가
    tkt_vals = [(r["ticket"], r["weight"]) for r in records if r["ticket"] is not None]

    # 면적
    area_vals = [(r["area_pyeong"], r["weight"]) for r in records if r["area_pyeong"] is not None]

    # 매출
    sales_vals = [(r["sales"], r["weight"]) for r in records if r["sales"] is not None]

    result: dict[str, Any] = {
        "n": len(records),
    }

    # 비율 (단순평균, %)
    if food_pcts:
        result["food_pct"] = round(simple_mean(food_pcts), 2)
    if labor_pcts:
        result["labor_pct"] = round(simple_mean(labor_pcts), 2)
    if rent_pcts:
        result["rent_pct"] = round(simple_mean(rent_pcts), 2)
    if profit_pcts:
        result["profit_pct"] = round(simple_mean(profit_pcts), 2)

    # 월세 분위수 (만원)
    if rent_values and len(rent_values) >= 3:
        pct = percentiles(rent_values)
        if pct:
            result["monthly_rent_p25"] = round(pct["p25"], 1)
            result["monthly_rent_median"] = round(pct["median"], 1)
            result["monthly_rent_p75"] = round(pct["p75"], 1)
        result["monthly_rent_mean"] = round(weighted_mean(
            [v for v, _ in rent_vals], [w for _, w in rent_vals]
        ), 1)
        result["monthly_rent_n"] = len(rent_values)

    # 보증금 분위수 (만원)
    if dep_vals and len(dep_vals) >= 3:
        dep_values = [v for v, _ in dep_vals]
        pct = percentiles(dep_values)
        if pct:
            result["deposit_p25"] = round(pct["p25"], 1)
            result["deposit_median"] = round(pct["median"], 1)
            result["deposit_p75"] = round(pct["p75"], 1)
        result["deposit_n"] = len(dep_values)

    # 투자비 (가중평균, 만원)
    if inv_vals:
        result["invest_total"] = round(weighted_mean([v for v, _ in inv_vals], [w for _, w in inv_vals]), 1)
        result["invest_n"] = len(inv_vals)
    if int_vals:
        result["interior"] = round(weighted_mean([v for v, _ in int_vals], [w for _, w in int_vals]), 1)
    if kit_vals:
        result["kitchen"] = round(weighted_mean([v for v, _ in kit_vals], [w for _, w in kit_vals]), 1)

    # 객단가 (가중평균, 원)
    if tkt_vals:
        result["avg_ticket"] = round(weighted_mean([v for v, _ in tkt_vals], [w for _, w in tkt_vals]), 0)
        result["ticket_n"] = len(tkt_vals)

    # 면적 (가중평균, 평)
    if area_vals:
        result["avg_area_pyeong"] = round(weighted_mean([v for v, _ in area_vals], [w for _, w in area_vals]), 1)

    # 매출 (가중평균, 만원)
    if sales_vals:
        result["avg_monthly_sales"] = round(weighted_mean([v for v, _ in sales_vals], [w for _, w in sales_vals]), 1)

    return result


# ---------------------------------------------------------------------------
# 메인 처리
# ---------------------------------------------------------------------------

def main():
    print(f"Loading {INPUT_FILE} ...")
    wb = openpyxl.load_workbook(str(INPUT_FILE), read_only=True)
    ws = wb.active

    # 파싱
    all_records: list[dict[str, Any]] = []
    skipped = 0
    for i, row in enumerate(ws.iter_rows(min_row=3, values_only=True)):  # skip 2 header rows
        rec = parse_row(list(row))
        if rec:
            all_records.append(rec)
        else:
            skipped += 1

    wb.close()
    print(f"Parsed {len(all_records)} records (skipped {skipped})")

    # ---------------------------------------------------------------------------
    # 다차원 집계
    # ---------------------------------------------------------------------------
    output: dict[str, Any] = {
        "source": "KREI 외식업체경영실태조사 2023 원시자료",
        "year": 2023,
        "total_records": len(all_records),
        "industries": {},
    }

    for ic in sorted(INDUSTRY_NAMES.keys()):
        ic_records = [r for r in all_records if r["industry_code"] == ic]
        if not ic_records:
            continue

        ic_seoul = [r for r in ic_records if r["is_seoul"]]
        ic_all = ic_records

        industry_data: dict[str, Any] = {
            "name": INDUSTRY_NAMES[ic],
            "total": aggregate(ic_all),
            "seoul": aggregate(ic_seoul) if ic_seoul else None,
        }

        # 상권유형별 집계 (서울 + 전국)
        by_district: dict[str, Any] = {}
        for dt in ["골목상권", "발달상권", "전통시장", "관광특구"]:
            dt_all = [r for r in ic_all if r["district_type"] == dt]
            dt_seoul = [r for r in ic_seoul if r["district_type"] == dt]
            if dt_all:
                entry: dict[str, Any] = {"total": aggregate(dt_all)}
                if dt_seoul:
                    entry["seoul"] = aggregate(dt_seoul)
                by_district[dt] = entry
        industry_data["by_district_type"] = by_district

        # 한식 세분류
        if ic == "CS100001":
            sub_data: dict[str, Any] = {}
            for sub_key in ["한식일반", "면요리", "육류", "해산물"]:
                sub_recs = [r for r in ic_all if r["hansik_sub"] == sub_key]
                sub_seoul = [r for r in sub_recs if r["is_seoul"]]
                if sub_recs:
                    sub_entry: dict[str, Any] = {"total": aggregate(sub_recs)}
                    if sub_seoul:
                        sub_entry["seoul"] = aggregate(sub_seoul)
                    # 세분류 × 상권유형
                    sub_by_dt: dict[str, Any] = {}
                    for dt in ["골목상권", "발달상권", "전통시장", "관광특구"]:
                        sub_dt = [r for r in sub_recs if r["district_type"] == dt]
                        if sub_dt:
                            sub_by_dt[dt] = {"total": aggregate(sub_dt)}
                            sub_dt_seoul = [r for r in sub_dt if r["is_seoul"]]
                            if sub_dt_seoul:
                                sub_by_dt[dt]["seoul"] = aggregate(sub_dt_seoul)
                    sub_entry["by_district_type"] = sub_by_dt
                    sub_data[sub_key] = sub_entry
            industry_data["sub_categories"] = sub_data

        output["industries"][ic] = industry_data

    # ---------------------------------------------------------------------------
    # 저장
    # ---------------------------------------------------------------------------
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nOutput: {OUTPUT_FILE}")
    print(f"Industries: {list(output['industries'].keys())}")

    # 요약 출력
    for ic, data in output["industries"].items():
        total = data["total"]
        print(f"  {ic} ({data['name']}): n={total['n']}, "
              f"food={total.get('food_pct', '?')}%, "
              f"labor={total.get('labor_pct', '?')}%, "
              f"profit={total.get('profit_pct', '?')}%")
        if "sub_categories" in data:
            for sub_key, sub_data in data["sub_categories"].items():
                st = sub_data["total"]
                print(f"    └ {sub_key}: n={st['n']}, food={st.get('food_pct', '?')}%")


if __name__ == "__main__":
    main()
