"""
서울 열린데이터광장에서 상권분석 데이터 다운로드
https://data.seoul.go.kr - 가입 없이 CSV 바로 다운로드 가능
"""

import os
import zipfile
from pathlib import Path

DATA_DIR = Path("data/seoul")
DATA_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = {
    "stores": {
        "name": "서울시 상권분석서비스(점포-상권)",
        "code": "OA-15577",
        "description": "상권별 점포 수, 개폐업 현황",
    },
    "sales": {
        "name": "서울시 상권분석서비스(추정매출-상권)",
        "code": "OA-15572",
        "description": "상권별 업종별 추정 매출",
    },
    "areas": {
        "name": "서울시 상권분석서비스(영역-상권)",
        "code": "OA-15560",
        "description": "상권 영역 정보",
    },
    "floating_pop": {
        "name": "서울시 상권분석서비스(길단위인구-상권)",
        "code": "OA-15568",
        "description": "상권별 유동인구",
    },
    "resident_pop": {
        "name": "서울시 상권분석서비스(상주인구-상권)",
        "code": "OA-15570",
        "description": "상권별 상주인구",
    },
    "income": {
        "name": "서울시 상권분석서비스(소득소비-상권)",
        "code": "OA-15566",
        "description": "상권별 소득/소비 정보",
    },
}


def print_download_instructions():
    print("=" * 70)
    print("Seoul Open Data - Commercial Area Analysis Data Download")
    print("=" * 70)
    print()
    print("No signup required! Direct CSV download available.")
    print()
    print("[Download Steps]")
    print("1. Click the URL below")
    print("2. Click 'Download File'")
    print("3. Save to data/seoul/ folder")
    print()

    for key, info in DATASETS.items():
        url = f"https://data.seoul.go.kr/dataList/{info['code']}/S/1/datasetView.do"
        print(f"[{key}] {info['name']}")
        print(f"   Description: {info['description']}")
        print(f"   URL: {url}")
        print(f"   Save as: data/seoul/{key}.csv")
        print()

    print("=" * 70)
    print()
    print("[Priority Downloads]")
    print("   1. stores - Coffee shop locations, open/close status")
    print("   2. sales - Estimated sales data")
    print("   3. floating_pop - Floating population")
    print()
    print("After download, run:")
    print("   python scripts/process_seoul_data.py")
    print()


def check_downloaded_files():
    print("\n[Download Status]")
    found = 0
    for key, info in DATASETS.items():
        csv_path = DATA_DIR / f"{key}.csv"
        zip_path = DATA_DIR / f"{key}.zip"

        if csv_path.exists():
            size = csv_path.stat().st_size / 1024 / 1024
            print(f"  [OK] {key}.csv ({size:.1f} MB)")
            found += 1
        elif zip_path.exists():
            print(f"  [ZIP] {key}.zip - extracting...")
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(DATA_DIR)
            print(f"        -> extracted")
            found += 1
        else:
            print(f"  [--] {key} - not downloaded")

    return found


if __name__ == "__main__":
    print_download_instructions()
    found = check_downloaded_files()

    if found == 0:
        print("\nNo data files found. Please download from URLs above.")
    elif found < len(DATASETS):
        print(f"\n{found}/{len(DATASETS)} files downloaded.")
    else:
        print(f"\nAll {found} files ready!")
