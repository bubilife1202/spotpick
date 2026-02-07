"""
서울 열린데이터광장 상권분석 추가 API 수집 스크립트
- 직장인구, 상주인구, 유동인구(길단위인구), 집객시설, 상권변화지표, 점포(전업종)
- 상권코드 기준 (업종 필터 없음 — 상권 단위 데이터)
- 최신 분기만 수집 (시뮬레이션 보강용)
"""

from __future__ import annotations

import os
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

API_KEY = os.getenv("SEOUL_API_KEY")
BASE_URL = "http://openapi.seoul.go.kr:8088"

DATA_DIR = Path(__file__).parent.parent / "data" / "seoul"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 최신 분기 (상권분석 서비스는 보통 1~2분기 지연)
LATEST_QUARTER = "20253"
FALLBACK_QUARTERS = ["20252", "20251", "20244", "20243"]

# ---------------------------------------------------------------------------
# 수집 대상 서비스 목록
# ---------------------------------------------------------------------------
# 각 서비스마다 URL 패턴과 필터 키가 다를 수 있음.
# 서울 상권분석 API URL: {BASE}/{KEY}/json/{SERVICE}/{START}/{END}/{QUARTER}
#
# 직장인구/상주인구/유동인구 → 분기별, 상권코드 단위
# 집객시설 → 분기별, 상권코드 단위
# 상권변화지표 → 분기별, 상권코드 단위
# 점포(전업종) → 분기별, 상권코드 단위 (커피숍뿐 아니라 전체 업종 분포)
# ---------------------------------------------------------------------------

SERVICES = [
    {
        "service": "VwsmTrdarWrcPopltnQq",
        "file_prefix": "worker_population",
        "desc": "직장인구-상권",
        "filter_field": None,  # 상권 단위이므로 필터 불필요
    },
    {
        "service": "VwsmTrdarRepopQq",
        "file_prefix": "resident_population",
        "desc": "상주인구-상권",
        "filter_field": None,
    },
    {
        "service": "VwsmTrdarFlpopQq",
        "file_prefix": "foot_traffic",
        "desc": "유동인구(길단위인구)-상권",
        "filter_field": None,
    },
    {
        "service": "VwsmTrdarFcltyQq",
        "file_prefix": "facilities",
        "desc": "집객시설-상권",
        "filter_field": None,
    },
    {
        "service": "VwsmTrdarIxQq",
        "file_prefix": "change_indicator",
        "desc": "상권변화지표-상권",
        "filter_field": None,
    },
    {
        "service": "VwsmTrdarStorQq",
        "file_prefix": "stores_all",
        "desc": "점포-상권(전업종)",
        "filter_field": None,  # 전업종 — 필터 안 함
    },
]


def fetch_page(service_name: str, start: int, end: int, quarter: str) -> list:
    """한 페이지 데이터 조회"""
    url = f"{BASE_URL}/{API_KEY}/json/{service_name}/{start}/{end}/{quarter}"
    try:
        resp = requests.get(url, timeout=30)
        data = resp.json()
        if service_name in data:
            return data[service_name].get("row", [])
        # 에러 응답 체크
        result = data.get("RESULT", {})
        code = result.get("CODE", "")
        if code == "INFO-200":
            # 해당 데이터 없음
            return []
        if code.startswith("ERROR"):
            print(f"    API error: {result.get('MESSAGE', code)}")
            return []
    except Exception as e:
        print(f"    Error: {e}")
    return []


def get_total_count(service_name: str, quarter: str) -> int:
    """서비스의 해당 분기 전체 건수 확인"""
    url = f"{BASE_URL}/{API_KEY}/json/{service_name}/1/1/{quarter}"
    try:
        resp = requests.get(url, timeout=30)
        data = resp.json()
        if service_name in data:
            return data[service_name].get("list_total_count", 0)
        # INFO-200 = 데이터 없음
        result = data.get("RESULT", {})
        if result.get("CODE") == "INFO-200":
            return 0
    except Exception:
        pass
    return 0


def find_available_quarter(service_name: str) -> str | None:
    """최신 분기부터 순서대로 시도해서 데이터가 있는 분기 찾기"""
    for q in [LATEST_QUARTER] + FALLBACK_QUARTERS:
        total = get_total_count(service_name, q)
        if total > 0:
            print(f"  → {q[:4]}년 {q[4]}분기 데이터 확인 ({total:,}건)")
            return q
        time.sleep(0.3)
    return None


def collect_all(service_name: str, quarter: str) -> list:
    """한 서비스의 전체 데이터 수집 (페이지네이션)"""
    total = get_total_count(service_name, quarter)
    if total == 0:
        return []

    print(f"  전체 {total:,}건 수집 중...")
    all_rows: list = []
    page_size = 1000

    for start in range(1, total + 1, page_size):
        end = min(start + page_size - 1, total)
        rows = fetch_page(service_name, start, end, quarter)
        all_rows.extend(rows)

        if start % 5000 == 1 and start > 1:
            print(f"    {start:,}/{total:,} ({len(all_rows):,}건)")

        time.sleep(0.25)

    return all_rows


def main():
    if not API_KEY:
        print("ERROR: SEOUL_API_KEY not set in .env")
        return

    print("=" * 60)
    print("서울시 상권분석 추가 데이터 수집")
    print("직장인구 / 상주인구 / 유동인구 / 집객시설 / 상권변화지표 / 점포(전업종)")
    print("=" * 60)

    for svc in SERVICES:
        service_name = svc["service"]
        file_prefix = svc["file_prefix"]
        desc = svc["desc"]

        print(f"\n[{desc}] ({service_name})")

        # 캐시 체크
        cache_file = DATA_DIR / f"{file_prefix}.json"
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
            print(f"  캐시됨: {len(cached):,}건 ({cache_file.name})")
            continue

        # 사용 가능한 분기 찾기
        quarter = find_available_quarter(service_name)
        if quarter is None:
            print(f"  ⚠️ 데이터 없음 — 건너뜀")
            continue

        # 수집
        rows = collect_all(service_name, quarter)
        if not rows:
            print(f"  ⚠️ 수집 결과 0건")
            continue

        # 저장
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)

        print(f"  ✓ {len(rows):,}건 저장 → {cache_file.name} ({quarter[:4]}Q{quarter[4]})")

    print("\n" + "=" * 60)
    print("추가 데이터 수집 완료!")
    print("다음 단계: python scripts/analyze_seoul_data.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
