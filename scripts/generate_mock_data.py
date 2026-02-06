import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import math

random.seed(42)

SEOUL_DISTRICTS = {
    "강남구": {
        "code": "11680",
        "center": (37.5172, 127.0473),
        "rent_base": 5000000,
        "population": 100000,
    },
    "서초구": {
        "code": "11650",
        "center": (37.4837, 127.0324),
        "rent_base": 4500000,
        "population": 85000,
    },
    "마포구": {
        "code": "11440",
        "center": (37.5663, 126.9014),
        "rent_base": 3500000,
        "population": 90000,
    },
    "용산구": {
        "code": "11170",
        "center": (37.5384, 126.9654),
        "rent_base": 4000000,
        "population": 70000,
    },
    "성동구": {
        "code": "11200",
        "center": (37.5633, 127.0371),
        "rent_base": 3000000,
        "population": 75000,
    },
    "종로구": {
        "code": "11110",
        "center": (37.5735, 126.9790),
        "rent_base": 4500000,
        "population": 60000,
    },
    "중구": {
        "code": "11140",
        "center": (37.5641, 126.9979),
        "rent_base": 5000000,
        "population": 55000,
    },
    "영등포구": {
        "code": "11560",
        "center": (37.5264, 126.8963),
        "rent_base": 3500000,
        "population": 95000,
    },
    "송파구": {
        "code": "11710",
        "center": (37.5145, 127.1066),
        "rent_base": 4000000,
        "population": 110000,
    },
    "광진구": {
        "code": "11215",
        "center": (37.5385, 127.0823),
        "rent_base": 2800000,
        "population": 80000,
    },
}

COMMERCIAL_AREAS = [
    {
        "name": "강남역",
        "district": "강남구",
        "coords": (37.4979, 127.0276),
        "type": "발달상권",
        "floating_pop": 150000,
    },
    {
        "name": "역삼역",
        "district": "강남구",
        "coords": (37.5007, 127.0365),
        "type": "발달상권",
        "floating_pop": 80000,
    },
    {
        "name": "삼성역",
        "district": "강남구",
        "coords": (37.5088, 127.0631),
        "type": "발달상권",
        "floating_pop": 90000,
    },
    {
        "name": "선릉역",
        "district": "강남구",
        "coords": (37.5045, 127.0490),
        "type": "발달상권",
        "floating_pop": 70000,
    },
    {
        "name": "홍대입구",
        "district": "마포구",
        "coords": (37.5571, 126.9246),
        "type": "발달상권",
        "floating_pop": 130000,
    },
    {
        "name": "합정역",
        "district": "마포구",
        "coords": (37.5495, 126.9138),
        "type": "발달상권",
        "floating_pop": 60000,
    },
    {
        "name": "망원동",
        "district": "마포구",
        "coords": (37.5562, 126.9102),
        "type": "골목상권",
        "floating_pop": 35000,
    },
    {
        "name": "연남동",
        "district": "마포구",
        "coords": (37.5663, 126.9258),
        "type": "골목상권",
        "floating_pop": 45000,
    },
    {
        "name": "이태원",
        "district": "용산구",
        "coords": (37.5344, 126.9947),
        "type": "발달상권",
        "floating_pop": 70000,
    },
    {
        "name": "경리단길",
        "district": "용산구",
        "coords": (37.5405, 126.9876),
        "type": "골목상권",
        "floating_pop": 30000,
    },
    {
        "name": "성수동",
        "district": "성동구",
        "coords": (37.5447, 127.0558),
        "type": "발달상권",
        "floating_pop": 55000,
    },
    {
        "name": "서울숲",
        "district": "성동구",
        "coords": (37.5443, 127.0374),
        "type": "골목상권",
        "floating_pop": 40000,
    },
    {
        "name": "광화문",
        "district": "종로구",
        "coords": (37.5759, 126.9769),
        "type": "발달상권",
        "floating_pop": 85000,
    },
    {
        "name": "익선동",
        "district": "종로구",
        "coords": (37.5740, 126.9880),
        "type": "골목상권",
        "floating_pop": 35000,
    },
    {
        "name": "을지로",
        "district": "중구",
        "coords": (37.5660, 126.9910),
        "type": "발달상권",
        "floating_pop": 65000,
    },
    {
        "name": "명동",
        "district": "중구",
        "coords": (37.5636, 126.9850),
        "type": "발달상권",
        "floating_pop": 120000,
    },
    {
        "name": "여의도",
        "district": "영등포구",
        "coords": (37.5219, 126.9245),
        "type": "발달상권",
        "floating_pop": 95000,
    },
    {
        "name": "문래동",
        "district": "영등포구",
        "coords": (37.5170, 126.8945),
        "type": "골목상권",
        "floating_pop": 25000,
    },
    {
        "name": "잠실역",
        "district": "송파구",
        "coords": (37.5133, 127.1001),
        "type": "발달상권",
        "floating_pop": 100000,
    },
    {
        "name": "석촌호수",
        "district": "송파구",
        "coords": (37.5085, 127.0998),
        "type": "골목상권",
        "floating_pop": 45000,
    },
    {
        "name": "건대입구",
        "district": "광진구",
        "coords": (37.5404, 127.0698),
        "type": "발달상권",
        "floating_pop": 85000,
    },
    {
        "name": "성수역",
        "district": "성동구",
        "coords": (37.5446, 127.0558),
        "type": "발달상권",
        "floating_pop": 50000,
    },
]

COFFEE_SHOP_PREFIXES = [
    "커피",
    "카페",
    "로스터리",
    "브루잉",
    "에스프레소",
    "빈스",
    "모카",
    "라떼",
]
COFFEE_SHOP_SUFFIXES = [
    "하우스",
    "랩",
    "스튜디오",
    "공방",
    "팩토리",
    "웍스",
    "플레이스",
    "스테이션",
]
COFFEE_SHOP_NAMES = [
    "블루보틀",
    "테라로사",
    "펠트",
    "프릳츠",
    "센터커피",
    "앤트러사이트",
    "커피리브레",
    "나무사이로",
    "믹스커피",
    "모모스커피",
    "헬카페",
    "그레이프랩",
    "레이어드",
]


def random_coords_near(center: tuple[float, float], radius_km: float = 0.5) -> tuple[float, float]:
    lat, lng = center
    radius_deg = radius_km / 111.0

    angle = random.uniform(0, 2 * math.pi)
    r = radius_deg * math.sqrt(random.uniform(0, 1))

    new_lat = lat + r * math.cos(angle)
    new_lng = lng + r * math.sin(angle) / math.cos(math.radians(lat))

    return (round(new_lat, 6), round(new_lng, 6))


def generate_store_name() -> str:
    if random.random() < 0.3:
        return random.choice(COFFEE_SHOP_NAMES)

    style = random.randint(1, 4)
    if style == 1:
        return f"{random.choice(COFFEE_SHOP_PREFIXES)}{random.choice(COFFEE_SHOP_SUFFIXES)}"
    elif style == 2:
        return f"더 {random.choice(COFFEE_SHOP_PREFIXES)}"
    elif style == 3:
        syllables = ["아", "루", "미", "소", "하", "나", "도", "리", "온", "빈"]
        return "".join(random.choices(syllables, k=random.randint(2, 3)))
    else:
        return f"{random.choice(COFFEE_SHOP_PREFIXES)} {random.randint(1, 99)}"


def generate_open_date(is_successful: bool) -> datetime:
    now = datetime.now()
    if is_successful:
        months_ago = random.randint(24, 60)
    else:
        months_ago = random.randint(3, 36)
    return now - timedelta(days=months_ago * 30)


def generate_stores(n: int = 500) -> list[dict]:
    stores = []
    used_names = set()

    for i in range(n):
        area = random.choice(COMMERCIAL_AREAS)
        district_info = SEOUL_DISTRICTS[area["district"]]

        name = generate_store_name()
        while name in used_names:
            name = generate_store_name()
        used_names.add(name)

        is_successful = random.random() < 0.4
        is_closed = not is_successful and random.random() < 0.5

        open_date = generate_open_date(is_successful)
        close_date = None
        if is_closed:
            months_open = random.randint(6, 24)
            close_date = open_date + timedelta(days=months_open * 30)
            if close_date > datetime.now():
                close_date = datetime.now() - timedelta(days=random.randint(30, 180))

        if is_successful:
            review_count = random.randint(200, 800)
            avg_score = round(random.uniform(4.2, 4.9), 1)
        elif is_closed:
            review_count = random.randint(10, 100)
            avg_score = round(random.uniform(3.0, 4.0), 1)
        else:
            review_count = random.randint(50, 300)
            avg_score = round(random.uniform(3.5, 4.3), 1)

        coords = random_coords_near(area["coords"], radius_km=0.3)

        rent_variation = random.uniform(0.7, 1.3)
        rent = int(district_info["rent_base"] * rent_variation)

        has_takeout = random.random() < 0.85
        has_delivery = random.random() < 0.3

        menu_count = random.randint(15, 40)
        avg_price = random.randint(3500, 7000)

        store = {
            "id": f"store_{i + 1:04d}",
            "name": name,
            "category_large": "음식",
            "category_medium": "커피/음료",
            "category_small": "커피전문점",
            "address": f"서울특별시 {area['district']} {area['name']}길 {random.randint(1, 100)}",
            "road_address": f"서울특별시 {area['district']} {area['name']}로 {random.randint(1, 500)}",
            "lat": coords[0],
            "lng": coords[1],
            "commercial_area": area["name"],
            "commercial_area_type": area["type"],
            "district": area["district"],
            "district_code": district_info["code"],
            "phone": f"02-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "open_date": open_date.strftime("%Y-%m-%d"),
            "close_date": close_date.strftime("%Y-%m-%d") if close_date else None,
            "is_closed": is_closed,
            "survival_months": (((close_date or datetime.now()) - open_date).days // 30),
            "review_count": review_count,
            "avg_review_score": avg_score,
            "blog_review_count": int(review_count * random.uniform(0.1, 0.3)),
            "estimated_monthly_rent": rent,
            "has_takeout": has_takeout,
            "has_delivery": has_delivery,
            "menu_count": menu_count,
            "avg_menu_price": avg_price,
            "operating_hours": f"{random.randint(7, 10)}:00-{random.randint(20, 23)}:00",
            "weekend_open": random.random() < 0.9,
            "is_franchise": random.random() < 0.2,
            "size_sqm": random.choice([15, 20, 25, 33, 40, 50, 66]),
        }

        stores.append(store)

    return stores


def calculate_success_score(store: dict) -> dict:
    survival_months = store["survival_months"]
    if survival_months >= 36:
        survival_score = 1.0
    elif survival_months >= 24:
        survival_score = 0.8
    elif survival_months >= 12:
        survival_score = 0.6
    elif survival_months >= 6:
        survival_score = 0.4
    else:
        survival_score = 0.2

    if store["is_closed"]:
        survival_score *= 0.3

    score_component = min(store["avg_review_score"] / 5.0, 1.0)
    count_component = min(store["review_count"] / 500, 1.0)
    review_score = score_component * 0.7 + count_component * 0.3

    growth_score = 0.5
    if store["review_count"] > 300 and store["avg_review_score"] > 4.0:
        growth_score = 0.8
    elif store["review_count"] < 50:
        growth_score = 0.3

    stability_score = 0.7 if store["avg_review_score"] > 4.0 else 0.4

    total_score = (
        survival_score * 0.4 + review_score * 0.3 + growth_score * 0.2 + stability_score * 0.1
    )

    return {
        "survival_score": round(survival_score, 3),
        "review_score": round(review_score, 3),
        "growth_score": round(growth_score, 3),
        "stability_score": round(stability_score, 3),
        "total_score": round(total_score, 3),
    }


def generate_commercial_areas() -> list[dict]:
    areas = []

    for i, area in enumerate(COMMERCIAL_AREAS):
        district_info = SEOUL_DISTRICTS[area["district"]]

        competitor_count = random.randint(10, 50)

        area_data = {
            "id": f"area_{i + 1:03d}",
            "name": area["name"],
            "type": area["type"],
            "lat": area["coords"][0],
            "lng": area["coords"][1],
            "district": area["district"],
            "district_code": district_info["code"],
            "floating_population": area["floating_pop"],
            "resident_population": int(district_info["population"] * random.uniform(0.05, 0.15)),
            "avg_rent_price": int(district_info["rent_base"] * random.uniform(0.8, 1.5)),
            "coffee_shop_count": competitor_count,
            "competitor_density": round(competitor_count / 0.25, 1),
            "avg_success_score": round(random.uniform(0.4, 0.7), 2),
            "survival_rate_1y": round(random.uniform(0.5, 0.8), 2),
            "survival_rate_3y": round(random.uniform(0.25, 0.5), 2),
            "nearby_subway": True,
            "bus_stops": random.randint(2, 8),
            "parking_available": random.random() < 0.4,
            "office_ratio": round(random.uniform(0.1, 0.6), 2),
            "residential_ratio": round(random.uniform(0.1, 0.5), 2),
            "commercial_ratio": round(random.uniform(0.2, 0.6), 2),
        }

        areas.append(area_data)

    return areas


def main():
    output_dir = Path("data/mock")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Generating stores...")
    stores = generate_stores(500)

    print("Calculating success scores...")
    for store in stores:
        store["success_metrics"] = calculate_success_score(store)

    stores_file = output_dir / "stores.json"
    with open(stores_file, "w", encoding="utf-8") as f:
        json.dump(stores, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(stores)} stores to {stores_file}")

    successful = [s for s in stores if s["success_metrics"]["total_score"] >= 0.6]
    failed = [s for s in stores if s["is_closed"]]
    print(f"  - Successful (score >= 0.6): {len(successful)}")
    print(f"  - Closed: {len(failed)}")

    print("\nGenerating commercial areas...")
    areas = generate_commercial_areas()

    areas_file = output_dir / "commercial_areas.json"
    with open(areas_file, "w", encoding="utf-8") as f:
        json.dump(areas, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(areas)} areas to {areas_file}")

    print("\nGenerating district summary...")
    district_summary = {}
    for district, info in SEOUL_DISTRICTS.items():
        district_stores = [s for s in stores if s["district"] == district]
        district_summary[district] = {
            "code": info["code"],
            "store_count": len(district_stores),
            "avg_success_score": round(
                sum(s["success_metrics"]["total_score"] for s in district_stores)
                / len(district_stores)
                if district_stores
                else 0,
                3,
            ),
            "avg_rent": int(
                sum(s["estimated_monthly_rent"] for s in district_stores) / len(district_stores)
            )
            if district_stores
            else 0,
            "closed_count": len([s for s in district_stores if s["is_closed"]]),
            "survival_rate": round(
                1 - len([s for s in district_stores if s["is_closed"]]) / len(district_stores)
                if district_stores
                else 0,
                3,
            ),
        }

    summary_file = output_dir / "district_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(district_summary, f, ensure_ascii=False, indent=2)
    print(f"Saved district summary to {summary_file}")

    print("\n=== Data Generation Complete ===")


if __name__ == "__main__":
    main()
