"""Smoke test to verify test infrastructure works."""


def test_infrastructure_works():
    """Basic smoke test - if this passes, pytest is working."""
    assert True


def test_sample_district_fixture(sample_district):
    """Verify sample_district fixture has required fields."""
    assert sample_district["district_code"] == "TEST001"
    assert sample_district["monthly_sales"] == 50000000
    assert sample_district["worker_total"] == 3000
    assert sample_district["apt_ratio"] == 0.625
    assert "foot_traffic_total" in sample_district
