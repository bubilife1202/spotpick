"""
서울 열린데이터광장 API 데이터 수집 스크립트
- 분기별로 저장하여 중단 시 재개 가능
- 요식업 10개 업종 전체 수집
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

API_KEY = os.getenv("SEOUL_API_KEY")
BASE_URL = "http://openapi.seoul.go.kr:8088"

DATA_DIR = Path(__file__).parent.parent / "data" / "seoul"
DATA_DIR.mkdir(parents=True, exist_ok=True)

QUARTERS = []
for year in range(2019, 2026):
    max_q = 3 if year == 2025 else 4
    for q in range(1, max_q + 1):
        QUARTERS.append(f"{year}{q}")

FOOD_INDUSTRY_CODES = {
    "CS100001": "한식음식점",
    "CS100002": "중식음식점",
    "CS100003": "일식음식점",
    "CS100004": "양식음식점",
    "CS100005": "제과점",
    "CS100006": "패스트푸드점",
    "CS100007": "치킨전문점",
    "CS100008": "분식전문점",
    "CS100009": "호프-간이주점",
    "CS100010": "커피-음료",
}


def fetch_page(service_name: str, start: int, end: int, quarter: str) -> list:
    url = f"{BASE_URL}/{API_KEY}/json/{service_name}/{start}/{end}/{quarter}"
    try:
        response = requests.get(url, timeout=30)
        data = response.json()
        if service_name in data:
            return data[service_name].get("row", [])
    except Exception as e:
        print(f"    Error: {e}")
    return []


def collect_quarter_all(service_name: str, quarter: str) -> dict:
    """한 분기의 요식업 전체 업종 데이터 수집. 업종코드별로 분리하여 반환."""
    url = f"{BASE_URL}/{API_KEY}/json/{service_name}/1/1/{quarter}"
    try:
        response = requests.get(url, timeout=30)
        data = response.json()
        total = data[service_name].get("list_total_count", 0)
    except Exception:
        return {}

    print(f"  전체 {total:,}건 중 요식업 필터링...")

    by_industry: dict = {code: [] for code in FOOD_INDUSTRY_CODES}
    page_size = 1000

    for start in range(1, total + 1, page_size):
        end = min(start + page_size - 1, total)
        rows = fetch_page(service_name, start, end, quarter)

        for r in rows:
            code = r.get("SVC_INDUTY_CD", "")
            if code in FOOD_INDUSTRY_CODES:
                by_industry[code].append(r)

        if start % 10000 == 1:
            food_total = sum(len(v) for v in by_industry.values())
            print(f"    {start:,}/{total:,} 처리 중... (요식업 {food_total}건)")

        time.sleep(0.2)

    return by_industry


def main():
    print("=" * 60)
    print("서울시 요식업 상권 데이터 수집 (10개 업종)")
    print(f"기간: 2019Q1 ~ 2025Q3 ({len(QUARTERS)}개 분기)")
    print("=" * 60)

    services = [
        ("VwsmTrdarSelngQq", "sales", "추정매출"),
        ("VwsmTrdarStorQq", "stores", "점포현황"),
    ]

    for service_name, file_prefix, desc in services:
        print(f"\n\n[{desc}] 수집 시작")

        for quarter in QUARTERS:
            year = quarter[:4]
            q = quarter[4]

            # 이미 모든 업종이 수집되었는지 확인
            all_cached = True
            for code in FOOD_INDUSTRY_CODES:
                industry_dir = DATA_DIR / code
                industry_dir.mkdir(parents=True, exist_ok=True)
                quarter_file = industry_dir / f"{file_prefix}_{quarter}.json"
                if not quarter_file.exists():
                    all_cached = False
                    break

            # 기존 단일 업종(커피) 캐시 파일도 확인 — 마이그레이션
            old_single_file = DATA_DIR / f"{file_prefix}_{quarter}.json"

            if all_cached:
                cached_count = 0
                for code in FOOD_INDUSTRY_CODES:
                    qf = DATA_DIR / code / f"{file_prefix}_{quarter}.json"
                    with open(qf, "r", encoding="utf-8") as f:
                        cached_count += len(json.load(f))
                print(f"  {year}년 {q}분기: 캐시됨 (요식업 {cached_count}건)")
                continue

            # 기존 커피 캐시만 있는 경우 — 새로 수집 필요
            print(f"  {year}년 {q}분기 수집 중...")
            by_industry = collect_quarter_all(service_name, quarter)

            for code, rows in by_industry.items():
                industry_dir = DATA_DIR / code
                industry_dir.mkdir(parents=True, exist_ok=True)
                quarter_file = industry_dir / f"{file_prefix}_{quarter}.json"
                with open(quarter_file, "w", encoding="utf-8") as f:
                    json.dump(rows, f, ensure_ascii=False)

            total_rows = sum(len(v) for v in by_industry.values())
            summary = ", ".join(
                f"{FOOD_INDUSTRY_CODES[c][:2]}:{len(by_industry[c])}"
                for c in sorted(by_industry.keys())
                if by_industry[c]
            )
            print(f"    → 요식업 {total_rows}건 저장 ({summary})")

        # 업종별 통합 파일 생성
        print(f"\n  업종별 통합 파일 생성...")
        for code, name in FOOD_INDUSTRY_CODES.items():
            industry_dir = DATA_DIR / code
            all_data = []
            for quarter in QUARTERS:
                qf = industry_dir / f"{file_prefix}_{quarter}.json"
                if qf.exists():
                    with open(qf, "r", encoding="utf-8") as f:
                        all_data.extend(json.load(f))
            combined = industry_dir / f"all_{file_prefix}.json"
            with open(combined, "w", encoding="utf-8") as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            print(f"    {name} ({code}): {len(all_data):,}건")

    print("\n" + "=" * 60)
    print("수집 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
