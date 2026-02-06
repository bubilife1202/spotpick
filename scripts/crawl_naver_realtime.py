"""
네이버 플레이스 실시간 크롤링
- 가입 불필요
- 공개 정보만 수집 (매장명, 리뷰수, 별점, 위치)
"""

import json
import time
import random
from pathlib import Path
from datetime import datetime
import urllib.request
import urllib.parse

DATA_DIR = Path("data/realtime")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def search_naver_places(query: str, display: int = 50) -> list[dict]:
    """네이버 지도 검색 API (비공식, 공개 엔드포인트)"""

    encoded_query = urllib.parse.quote(query)
    url = f"https://map.naver.com/p/api/search/allSearch?query={encoded_query}&type=all&searchCoord=&boundary="

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://map.naver.com/",
    }

    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))

            places = []
            if "result" in data and "place" in data["result"]:
                place_data = data["result"]["place"]
                if "list" in place_data:
                    for item in place_data["list"][:display]:
                        place = parse_place(item)
                        if place:
                            places.append(place)

            return places
    except Exception as e:
        print(f"Error: {e}")
        return []


def parse_place(item: dict) -> dict | None:
    """네이버 플레이스 응답 파싱"""
    try:
        return {
            "id": item.get("id", ""),
            "name": item.get("name", ""),
            "category": item.get("category", [""]),
            "address": item.get("address", ""),
            "road_address": item.get("roadAddress", ""),
            "lat": float(item.get("y", 0)),
            "lng": float(item.get("x", 0)),
            "phone": item.get("tel", ""),
            "review_count": int(item.get("reviewCount", 0) or 0),
            "visitor_review_count": int(item.get("visitorReviewCount", 0) or 0),
            "blog_review_count": int(item.get("blogReviewCount", 0) or 0),
            "booking_url": item.get("bookingUrl", ""),
            "business_hours": item.get("businessHours", ""),
            "crawled_at": datetime.now().isoformat(),
        }
    except (ValueError, TypeError) as e:
        return None


def crawl_coffee_shops(regions: list[str], delay: float = 1.5) -> list[dict]:
    """여러 지역의 커피숍 크롤링"""
    all_places = []
    seen_ids = set()

    for region in regions:
        query = f"{region} 카페"
        print(f"Searching: {query}")

        places = search_naver_places(query, display=50)

        for place in places:
            if place["id"] not in seen_ids:
                seen_ids.add(place["id"])
                place["search_region"] = region
                all_places.append(place)

        print(f"  Found: {len(places)} places (Total: {len(all_places)})")

        time.sleep(delay + random.uniform(0, 1))

    return all_places


def calculate_simple_score(place: dict) -> float:
    """간단한 성공 점수 계산"""
    total_reviews = (
        place.get("review_count", 0)
        + place.get("visitor_review_count", 0)
        + place.get("blog_review_count", 0)
    )

    if total_reviews >= 500:
        review_score = 1.0
    elif total_reviews >= 200:
        review_score = 0.8
    elif total_reviews >= 100:
        review_score = 0.6
    elif total_reviews >= 50:
        review_score = 0.4
    else:
        review_score = 0.2

    return round(review_score, 2)


def main():
    print("=" * 60)
    print("Naver Places Realtime Crawler")
    print("=" * 60)
    print()

    regions = [
        "강남역",
        "역삼역",
        "삼성역",
        "선릉역",
        "홍대입구",
        "합정역",
        "망원동",
        "연남동",
        "이태원",
        "경리단길",
        "성수동",
        "건대입구",
        "잠실역",
        "석촌호수",
        "여의도",
        "광화문",
    ]

    print(f"Crawling {len(regions)} regions...")
    print()

    places = crawl_coffee_shops(regions, delay=1.0)

    for place in places:
        place["success_score"] = calculate_simple_score(place)

    places.sort(key=lambda x: x["success_score"], reverse=True)

    output_file = DATA_DIR / f"coffee_shops_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(places, f, ensure_ascii=False, indent=2)

    print()
    print("=" * 60)
    print(f"Crawled {len(places)} unique coffee shops")
    print(f"Saved to: {output_file}")
    print()

    print("Top 10 by review count:")
    for i, p in enumerate(places[:10], 1):
        total = p["review_count"] + p["visitor_review_count"] + p["blog_review_count"]
        print(f"  {i}. {p['name']} ({p['search_region']})")
        print(f"     Reviews: {total}, Score: {p['success_score']}")

    print()
    print("Data ready for analysis!")
    print("Run: python scripts/test_api.py")


if __name__ == "__main__":
    main()
