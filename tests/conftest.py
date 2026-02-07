"""Shared pytest fixtures for builder_curation tests."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

DATA_DIR = Path(__file__).parent.parent / "data"
INDUSTRIES_DIR = DATA_DIR / "industries"
PROCESSED_DIR = DATA_DIR / "processed"


@pytest.fixture
def coffee_config() -> dict[str, Any]:
    """Load CS100010 (cafe) industry config."""
    with open(INDUSTRIES_DIR / "CS100010.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def chicken_config() -> dict[str, Any]:
    """Load CS100007 (chicken) industry config."""
    with open(INDUSTRIES_DIR / "CS100007.json", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_district() -> dict[str, Any]:
    """A minimal district dict with key fields for testing."""
    return {
        "district_code": "TEST001",
        "district_name": "테스트상권",
        "district_type": "골목상권",
        "monthly_sales": 50000000,
        "monthly_transactions": 5000,
        "store_count": 10,
        "franchise_stores": 3,
        "new_stores": 2,
        "closed_stores": 1,
        "survival_rate": 0.85,
        "weekday_ratio": 0.73,
        "weekend_ratio": 0.27,
        "male_ratio": 0.42,
        "female_ratio": 0.58,
        "male_sales": 21000000,
        "female_sales": 29000000,
        "male_transactions": 2100,
        "female_transactions": 2900,
        "mon_sales": 7500000, "tue_sales": 7200000, "wed_sales": 7600000,
        "thu_sales": 7400000, "fri_sales": 7800000, "sat_sales": 6500000, "sun_sales": 6000000,
        "mon_transactions": 750, "tue_transactions": 720, "wed_transactions": 760,
        "thu_transactions": 740, "fri_transactions": 780, "sat_transactions": 650, "sun_transactions": 600,
        "time_00_06_sales": 1000000, "time_06_11_sales": 8000000,
        "time_11_14_sales": 15000000, "time_14_17_sales": 12000000,
        "time_17_21_sales": 10000000, "time_21_24_sales": 4000000,
        "time_00_06_transactions": 100, "time_06_11_transactions": 800,
        "time_11_14_transactions": 1500, "time_14_17_transactions": 1200,
        "time_17_21_transactions": 1000, "time_21_24_transactions": 400,
        "age_10_sales": 2000000, "age_20_sales": 12000000, "age_30_sales": 15000000,
        "age_40_sales": 10000000, "age_50_sales": 7000000, "age_60_sales": 4000000,
        "age_10_transactions": 200, "age_20_transactions": 1200, "age_30_transactions": 1500,
        "age_40_transactions": 1000, "age_50_transactions": 700, "age_60_transactions": 400,
        "peak_time": "11-14",
        "peak_day": "금",
        "main_age_group": "30대",
        # Population data
        "worker_total": 3000,
        "worker_male": 1800,
        "worker_female": 1200,
        "worker_age_10": 0,
        "worker_age_20": 500,
        "worker_age_30": 900,
        "worker_age_40": 850,
        "worker_age_50": 500,
        "worker_age_60": 250,
        "resident_total": 2000,
        "resident_male": 950,
        "resident_female": 1050,
        "resident_age_10": 200,
        "resident_age_20": 300,
        "resident_age_30": 400,
        "resident_age_40": 450,
        "resident_age_50": 350,
        "resident_age_60": 300,
        "total_households": 800,
        "apt_households": 500,
        "non_apt_households": 300,
        "apt_ratio": 0.625,
        # Foot traffic
        "foot_traffic_total": 500000,
        "foot_traffic_male": 220000,
        "foot_traffic_female": 280000,
        "foot_traffic_age_10": 50000,
        "foot_traffic_age_20": 100000,
        "foot_traffic_age_30": 120000,
        "foot_traffic_age_40": 100000,
        "foot_traffic_age_50": 70000,
        "foot_traffic_age_60": 60000,
        "foot_traffic_00_06": 50000,
        "foot_traffic_06_11": 100000,
        "foot_traffic_11_14": 80000,
        "foot_traffic_14_17": 90000,
        "foot_traffic_17_21": 110000,
        "foot_traffic_21_24": 70000,
        # Facilities
        "facility_score": 150,
        "facility_subway": 1,
        "facility_bus_stop": 5,
        "facility_university": 0,
        "transit_raw": 120,
        # Change indicators
        "change_indicator": "HL",
        "change_indicator_code": "HL",
        "avg_operation_months": 24,
        # Coordinates
        "lat": 37.5665,
        "lng": 126.978,
    }
