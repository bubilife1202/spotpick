"""
서울 열린데이터광장 API 데이터 수집 스크립트 (최적화 버전)
- 분기별로 저장하여 중단 시 재개 가능
- 커피숍(CS100010) 데이터만 수집
"""

import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# 프로젝트 루트에서 .env 로드
load_dotenv(Path(__file__).parent.parent / ".env")

API_KEY = os.getenv("SEOUL_API_KEY")
BASE_URL = "http://openapi.seoul.go.kr:8088"

# 데이터 저장 경로
DATA_DIR = Path(__file__).parent.parent / "data" / "seoul"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 수집할 분기 코드 (2019년 1분기 ~ 2025년 3분기)
QUARTERS = []
for year in range(2019, 2026):
    max_q = 3 if year == 2025 else 4
    for q in range(1, max_q + 1):
        QUARTERS.append(f"{year}{q}")

# 커피숍 업종 코드
COFFEE_SHOP_CODE = "CS100010"


def fetch_page(service_name: str, start: int, end: int, quarter: str) -> list:
    """한 페이지 데이터 조회"""
    url = f"{BASE_URL}/{API_KEY}/json/{service_name}/{start}/{end}/{quarter}"

    try:
        response = requests.get(url, timeout=30)
        data = response.json()

        if service_name in data:
            return data[service_name].get("row", [])
    except Exception as e:
        print(f"    Error: {e}")

    return []


def collect_quarter(service_name: str, quarter: str, filter_code: str) -> list:
    """한 분기의 커피숍 데이터 수집"""

    # 첫 요청으로 전체 건수 확인
    url = f"{BASE_URL}/{API_KEY}/json/{service_name}/1/1/{quarter}"
    try:
        response = requests.get(url, timeout=30)
        data = response.json()
        total = data[service_name].get("list_total_count", 0)
    except:
        return []

    print(f"  전체 {total:,}건 중 커피숍 필터링...")

    # 페이지네이션
    all_rows = []
    page_size = 1000

    for start in range(1, total + 1, page_size):
        end = min(start + page_size - 1, total)
        rows = fetch_page(service_name, start, end, quarter)

        # 커피숍만 필터
        coffee_rows = [r for r in rows if r.get("SVC_INDUTY_CD") == filter_code]
        all_rows.extend(coffee_rows)

        # 진행률 표시 (10000건마다)
        if start % 10000 == 1:
            print(f"    {start:,}/{total:,} 처리 중... (커피숍 {len(all_rows)}건)")

        time.sleep(0.2)  # rate limit

    return all_rows


def main():
    print("=" * 50)
    print("서울시 커피숍 상권 데이터 수집")
    print(f"기간: 2019Q1 ~ 2025Q3 ({len(QUARTERS)}개 분기)")
    print("=" * 50)

    services = [
        ("VwsmTrdarSelngQq", "sales", "추정매출"),
        ("VwsmTrdarStorQq", "stores", "점포현황"),
    ]

    for service_name, file_prefix, desc in services:
        print(f"\n\n[{desc}] 수집 시작")

        all_data = []

        for quarter in QUARTERS:
            year = quarter[:4]
            q = quarter[4]

            # 이미 수집된 분기 건너뛰기
            quarter_file = DATA_DIR / f"{file_prefix}_{quarter}.json"
            if quarter_file.exists():
                with open(quarter_file, "r", encoding="utf-8") as f:
                    quarter_data = json.load(f)
                print(f"  {year}년 {q}분기: 캐시됨 ({len(quarter_data)}건)")
                all_data.extend(quarter_data)
                continue

            print(f"  {year}년 {q}분기 수집 중...")
            quarter_data = collect_quarter(service_name, quarter, COFFEE_SHOP_CODE)

            # 분기별 저장
            with open(quarter_file, "w", encoding="utf-8") as f:
                json.dump(quarter_data, f, ensure_ascii=False)

            print(f"    → {len(quarter_data)}건 저장")
            all_data.extend(quarter_data)

        # 전체 통합 파일 저장
        combined_file = DATA_DIR / f"coffee_{file_prefix}.json"
        with open(combined_file, "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        print(f"\n  [완료] {combined_file.name}: 총 {len(all_data):,}건")

    print("\n" + "=" * 50)
    print("수집 완료!")
    print("=" * 50)


if __name__ == "__main__":
    main()
