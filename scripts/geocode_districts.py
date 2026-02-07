"""카카오 키워드 검색으로 1,077개 상권 좌표 일괄 수집"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

KAKAO_KEY = os.getenv("KAKAO_REST_API_KEY")
DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
COORDS_FILE = DATA_DIR / "district_coords.json"

HEADERS = {"Authorization": f"KakaoAK {KAKAO_KEY}"}
SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


def parse_args():
    parser = argparse.ArgumentParser(description="상권 좌표 수집")
    parser.add_argument("--industry", default="CS100010",
                        help="업종코드 (default: CS100010)")
    return parser.parse_args()


def geocode_one(name: str) -> dict:
    query = f"서울 {name}"
    try:
        resp = requests.get(
            SEARCH_URL,
            headers=HEADERS,
            params={"query": query, "size": 1},
            timeout=5,
        )
        docs = resp.json().get("documents", [])
        if docs:
            return {"lat": float(docs[0]["y"]), "lng": float(docs[0]["x"])}
    except Exception:
        pass

    for suffix in ["역", " 상권", " 거리"]:
        trimmed = name.replace(suffix, "").strip()
        if trimmed != name:
            try:
                resp = requests.get(
                    SEARCH_URL,
                    headers=HEADERS,
                    params={"query": f"서울 {trimmed}", "size": 1},
                    timeout=5,
                )
                docs = resp.json().get("documents", [])
                if docs:
                    return {"lat": float(docs[0]["y"]), "lng": float(docs[0]["x"])}
            except Exception:
                pass
    return {}


def main() -> None:
    args = parse_args()
    industry_code = args.industry
    
    districts_file = DATA_DIR / f"{industry_code}_districts.json"
    
    # Backward compat: if {code}_districts.json doesn't exist but coffee_districts.json does
    if not districts_file.exists() and industry_code == "CS100010":
        districts_file = DATA_DIR / "coffee_districts.json"
    
    if not KAKAO_KEY:
        print("ERROR: KAKAO_REST_API_KEY not set in .env")
        return

    with open(districts_file, encoding="utf-8") as f:
        districts = json.load(f)

    existing: dict = {}
    if COORDS_FILE.exists():
        with open(COORDS_FILE, encoding="utf-8") as f:
            existing = json.load(f)
        print(f"기존 캐시: {len(existing)}개")

    total = len(districts)
    success = 0
    skipped = 0

    print(f"총 {total}개 상권 좌표 수집 시작...")

    for i, d in enumerate(districts):
        code = d["district_code"]
        name = d["district_name"]

        if code in existing and existing[code].get("lat"):
            skipped += 1
            continue

        coords = geocode_one(name)
        if coords:
            existing[code] = coords
            success += 1
        else:
            existing[code] = {}

        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{total} (성공: {success}, 스킵: {skipped})")
            with open(COORDS_FILE, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)

        time.sleep(0.12)

    with open(COORDS_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    has_coords = sum(1 for v in existing.values() if v.get("lat"))
    print(f"\n좌표 수집 완료: {has_coords}/{total}")

    print(f"{districts_file.name}에 좌표 병합 중...")
    coords_map = existing
    for d in districts:
        c = coords_map.get(d["district_code"], {})
        d["lat"] = c.get("lat", 0.0)
        d["lng"] = c.get("lng", 0.0)

    with open(districts_file, "w", encoding="utf-8") as f:
        json.dump(districts, f, ensure_ascii=False, indent=2)

    merged = sum(1 for d in districts if d.get("lat", 0) > 0)
    print(f"병합 완료: {merged}/{total}개 상권에 좌표 추가됨")


if __name__ == "__main__":
    main()
