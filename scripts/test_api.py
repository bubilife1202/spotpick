import sys

sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    print(f"Health: {response.status_code}")
    print(response.json())
    print()


def test_quick_recommendation():
    print("=== Quick Recommendation ===")
    response = client.get("/api/v1/recommendations/quick?budget=3000000")
    print(f"Status: {response.status_code}")
    data = response.json()

    if "recommendation" in data:
        rec = data["recommendation"]
        print(f"추천 지역: {rec['area_name']}")
        print(f"성공 확률: {rec['success_probability']}")
        print(f"예상 월세: {rec['monthly_rent']}")
        print(f"핵심 성공 요인: {rec['key_factors']}")
        print(f"주요 리스크: {rec['main_risk']}")
        print(f"팁: {rec['tip']}")
        print(f"\n대안 지역:")
        for alt in data["alternatives"]:
            print(f"  - {alt['area_name']}: {alt['success_probability']}, {alt['monthly_rent']}")
    print()


def test_full_recommendation():
    print("=== Full Recommendation ===")
    response = client.post(
        "/api/v1/recommendations",
        json={
            "category": "coffee",
            "budget_min": 2000000,
            "budget_max": 4000000,
            "top_n": 5,
        },
    )
    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Total candidates: {data['total_candidates']}")
    print(f"\nTop 5 추천:")
    for rec in data["recommendations"]:
        print(f"\n{rec['rank']}. {rec['area_name']} ({rec['area_type']})")
        print(f"   위치: {rec['address']}")
        print(f"   성공 확률: {rec['success_probability'] * 100:.0f}%")
        print(f"   예상 월세: {rec['estimated_monthly_rent']:,}원")
        print(f"   리스크: {', '.join(rec['risk_factors'][:2]) or '없음'}")
        print(f"   성공 요인: {', '.join(rec['key_success_factors'][:3])}")
    print()


def test_analyze_location():
    print("=== Analyze Location (강남역) ===")
    response = client.get(
        "/api/v1/recommendations/analyze",
        params={"lat": 37.4979, "lng": 127.0276, "category": "coffee"},
    )
    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"가장 가까운 상권: {data['nearest_area']}")
    print(f"분석 결과:")
    analysis = data["analysis"]
    print(f"  성공 확률: {analysis['success_probability'] * 100:.0f}%")
    print(f"  신뢰도: {analysis['confidence'] * 100:.0f}%")
    print(f"  리스크: {analysis['risk_factors']}")
    print(f"  추천: {analysis['recommendations'][:2]}")
    print(f"\n주변 특성:")
    features = data["features"]
    print(f"  유동인구: {features['floating_population']:,}명")
    print(f"  경쟁업체: {features['competitor_count']}개")
    print(f"  예상 월세: {features['avg_rent_price']:,}원")
    print(f"\n인근 성공 매장:")
    for store in data["nearby_successful_stores"][:3]:
        print(f"  - {store['name']}: 점수 {store['score']:.2f}")
    print()


def test_stores():
    print("=== Stores (강남구, 성공 점수 0.6 이상) ===")
    response = client.get(
        "/api/v1/stores",
        params={"district": "강남구", "min_score": 0.6, "page_size": 5},
    )
    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Total: {data['total']}")
    for store in data["items"]:
        print(
            f"  - {store['name']}: 점수 {store['success_metrics']['total_score']:.2f}, 리뷰 {store['review_count']}개"
        )
    print()


def test_areas():
    print("=== Areas (성공률순) ===")
    response = client.get("/api/v1/areas", params={"sort_by": "survival_rate_3y"})
    print(f"Status: {response.status_code}")
    data = response.json()

    print(f"Total areas: {data['total']}")
    for area in data["items"][:5]:
        print(
            f"  - {area['name']} ({area['district']}): 3년 생존율 {area['survival_rate_3y'] * 100:.0f}%"
        )
    print()


def test_compare_areas():
    print("=== Compare Areas ===")
    response = client.get(
        "/api/v1/areas/compare",
        params={"area_names": "강남역,홍대입구,성수동"},
    )
    print(f"Status: {response.status_code}")
    data = response.json()

    print("비교 결과:")
    for area in data["areas"]:
        print(f"  {area['name']}:")
        print(f"    유동인구: {area['floating_population']:,}")
        print(f"    월세: {area['avg_rent_price']:,}원")
        print(f"    3년 생존율: {area['survival_rate_3y'] * 100:.0f}%")

    print(f"\n분석:")
    analysis = data["analysis"]
    print(f"  생존율 최고: {analysis['best_survival_rate']}")
    print(f"  임대료 최저: {analysis['lowest_rent']}")
    print(f"  유동인구 최고: {analysis['highest_traffic']}")
    print(f"  추천: {analysis['recommendation']}")


if __name__ == "__main__":
    print("=" * 60)
    print("Builder Curation API Test")
    print("=" * 60)
    print()

    test_health()
    test_quick_recommendation()
    test_full_recommendation()
    test_analyze_location()
    test_stores()
    test_areas()
    test_compare_areas()
