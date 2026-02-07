from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/districts")


@router.get("/{district_code}/charts")
def get_district_charts(
    district_code: str,
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """특정 상권의 차트 데이터 (시간대/요일/연령/성별) 반환."""
    from ..services.data_service import get_data_service

    svc = get_data_service(industry_code=industry_code)
    d = svc.get_district(district_code)
    if not d:
        raise HTTPException(status_code=404, detail="상권을 찾을 수 없습니다")

    detail = svc.get_district_detail(district_code)
    district_name = d.get("district_name", "")
    district_type = d.get("district_type", "")
    monthly_sales = max(1, d.get("monthly_sales", 1))

    def to_pct(val: object) -> float:
        if isinstance(val, (int, float)):
            return round(float(val) / monthly_sales * 100, 1)
        return 0.0

    def format_label(sales: object, transactions: object) -> str:
        parts: list[str] = []
        if isinstance(sales, (int, float)) and int(sales) > 0:
            parts.append(f"매출 {int(sales):,}원")
        if isinstance(transactions, (int, float)) and int(transactions) > 0:
            parts.append(f"거래 {int(transactions):,}건")
        return " · ".join(parts) if parts else ""

    time_bd = (detail or {}).get("time_breakdown", {})
    day_bd = (detail or {}).get("day_breakdown", {})
    cust_bd = (detail or {}).get("customer_breakdown", {})

    charts = []

    # 시간대별
    time_slots = [
        ("00-06", "time_00_06_sales", "새벽(0-6시)"),
        ("06-11", "time_06_11_sales", "아침(6-11시)"),
        ("11-14", "time_11_14_sales", "점심(11-14시)"),
        ("14-17", "time_14_17_sales", "오후(14-17시)"),
        ("17-21", "time_17_21_sales", "저녁(17-21시)"),
        ("21-24", "time_21_24_sales", "밤(21-24시)"),
    ]
    charts.append({
        "type": "time",
        "title": f"{district_name} 시간대별 매출 비중",
        "data": [
            {
                "name": name,
                "value": to_pct(d.get(field)),
                "label": format_label(
                    (time_bd.get(bd_key) or {}).get("sales"),
                    (time_bd.get(bd_key) or {}).get("transactions"),
                ),
            }
            for name, field, bd_key in time_slots
        ],
    })

    # 요일별
    day_slots = [
        ("월", "mon_sales", "월"),
        ("화", "tue_sales", "화"),
        ("수", "wed_sales", "수"),
        ("목", "thu_sales", "목"),
        ("금", "fri_sales", "금"),
        ("토", "sat_sales", "토"),
        ("일", "sun_sales", "일"),
    ]
    charts.append({
        "type": "day",
        "title": f"{district_name} 요일별 매출 비중",
        "data": [
            {
                "name": name,
                "value": to_pct(d.get(field)),
                "label": format_label(
                    (day_bd.get(bd_key) or {}).get("sales"),
                    (day_bd.get(bd_key) or {}).get("transactions"),
                ),
            }
            for name, field, bd_key in day_slots
        ],
    })

    # 연령대별
    age_slots = [
        ("10대", "age_10_sales"),
        ("20대", "age_20_sales"),
        ("30대", "age_30_sales"),
        ("40대", "age_40_sales"),
        ("50대", "age_50_sales"),
        ("60대+", "age_60_sales"),
    ]
    age_bd = cust_bd.get("age", {}) if isinstance(cust_bd, dict) else {}
    charts.append({
        "type": "age",
        "title": f"{district_name} 연령대별 매출 비중",
        "data": [
            {
                "name": name,
                "value": to_pct(d.get(field)),
                "label": format_label(
                    (age_bd.get(name) or {}).get("sales"),
                    (age_bd.get(name) or {}).get("transactions"),
                ),
            }
            for name, field in age_slots
        ],
    })

    # 성별
    gender_bd = cust_bd.get("gender", {}) if isinstance(cust_bd, dict) else {}
    charts.append({
        "type": "gender",
        "title": f"{district_name} 성별 매출 비중",
        "data": [
            {
                "name": "남성",
                "value": round(float(d.get("male_ratio", 0)) * 100, 1),
                "label": format_label(
                    (gender_bd.get("male") or {}).get("sales"),
                    (gender_bd.get("male") or {}).get("transactions"),
                ),
            },
            {
                "name": "여성",
                "value": round(float(d.get("female_ratio", 0)) * 100, 1),
                "label": format_label(
                    (gender_bd.get("female") or {}).get("sales"),
                    (gender_bd.get("female") or {}).get("transactions"),
                ),
            },
        ],
    })

    return {
        "charts": charts,
        "district_name": district_name,
        "district_type": district_type,
    }


@router.get("/{district_code}/timeline")
def get_district_timeline(
    district_code: str,
    industry_code: str = Query("CS100010", description="업종 코드"),
    cafe_type: str | None = Query(None, description="업태 (테이크아웃, 브런치, 일반 등)"),
    budget_max: int | None = Query(None, description="예산 상한"),
    area_pyeong: int = Query(15, ge=1, le=200, description="면적(평)"),
):
    """특정 상권의 창업 타임라인 반환."""
    from ..services.data_service import get_data_service
    from ..services.timeline_service import get_timeline_service

    svc = get_data_service(industry_code=industry_code)
    d = svc.get_district(district_code)
    if not d:
        raise HTTPException(status_code=404, detail="상권을 찾을 수 없습니다")

    district_type = d.get("district_type", "골목상권")

    # budget_max → budget_range 매핑
    if budget_max is not None:
        if budget_max <= 30_000_000:
            budget_range = "3천만원 이하"
        elif budget_max <= 100_000_000:
            budget_range = "3천~1억"
        else:
            budget_range = "1억+"
    else:
        budget_range = "3천~1억"

    timeline_svc = get_timeline_service(industry_code=industry_code)
    result = timeline_svc.calculate_timeline(
        business_type=cafe_type or "일반",
        budget_range=budget_range,
        area_pyeong=area_pyeong,
        district_type=district_type,
    )

    return result


@router.get("/{district_code}/detail")
def get_district_detail_for_report(
    district_code: str,
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """보고서용 상권 상세 정보 — 헤더/판정 섹션에 사용."""
    from ..services.data_service import get_data_service, estimate_rent

    svc = get_data_service(industry_code=industry_code)
    d = svc.get_district(district_code)
    if not d:
        raise HTTPException(status_code=404, detail="상권을 찾을 수 없습니다")

    sales_per_store = int(d["monthly_sales"] / max(1, d.get("store_count", 1)))
    pctile = svc._sales_percentile.get(d["district_code"], 0.5)
    estimated_rent = estimate_rent(
        d["district_type"], sales_per_store, pctile, svc._rent_ranges,
        industry_code=svc.industry_code,
    )
    success_prob = svc._calculate_success_probability(d)
    risk_factors = svc._identify_risks(d)
    key_factors = svc._extract_key_factors(d)

    return {
        "district_code": d["district_code"],
        "district_name": d["district_name"],
        "district_type": d["district_type"],
        "success_probability": success_prob,
        "estimated_rent": estimated_rent,
        "monthly_sales": d["monthly_sales"],
        "sales_per_store": sales_per_store,
        "foot_traffic_total": d.get("foot_traffic_total", 0),
        "worker_total": d.get("worker_total", 0),
        "resident_total": d.get("resident_total", 0),
        "facility_subway": d.get("facility_subway", 0),
        "change_indicator": d.get("change_indicator", ""),
        "survival_rate": d.get("survival_rate", 0),
        "store_count": d.get("store_count", 0),
        "new_stores": d.get("new_stores", 0),
        "closed_stores": d.get("closed_stores", 0),
        "franchise_stores": d.get("franchise_stores", 0),
        "peak_time": d.get("peak_time", ""),
        "peak_day": d.get("peak_day", ""),
        "main_age_group": d.get("main_age_group", ""),
        "risk_factors": risk_factors,
        "key_success_factors": key_factors,
        "lat": d.get("lat", 0.0),
        "lng": d.get("lng", 0.0),
    }


# ---------------------------------------------------------------------------
# Analysis endpoint — rule-based AI commentary for each report section
# ---------------------------------------------------------------------------


def _fmt_pct(ratio: float) -> str:
    """Format 0-1 ratio as percentage string."""
    return f"{ratio * 100:.0f}%"


def _peak_time_label(peak: str) -> str:
    """Convert peak time code to human label."""
    labels = {
        "00-06": "새벽(0-6시)",
        "06-11": "오전(6-11시)",
        "11-14": "점심(11-14시)",
        "14-17": "오후(14-17시)",
        "17-21": "저녁(17-21시)",
        "21-24": "밤(21-24시)",
    }
    return labels.get(peak, peak)


def _peak_day_label(day: str) -> str:
    """Normalize peak day to Korean."""
    mapping = {"mon": "월요일", "tue": "화요일", "wed": "수요일",
               "thu": "목요일", "fri": "금요일", "sat": "토요일", "sun": "일요일"}
    lower = day.lower().strip()
    if lower in mapping:
        return mapping[lower]
    # Already Korean
    if day and not day.endswith("요일"):
        return f"{day}요일"
    return day or "평일"


def _compute_industry_averages(
    svc: Any,
    industry_code: str,
) -> dict[str, float]:
    """Compute average stats across all districts for the industry."""
    districts = svc.districts
    n = max(1, len(districts))
    total_sales = sum(d.get("monthly_sales", 0) for d in districts)
    total_stores_all = sum(d.get("store_count", 0) for d in districts)
    total_survival = sum(d.get("survival_rate", 0) for d in districts)

    # Per-store sales average
    per_store_sales_list = []
    for d in districts:
        sc = max(1, d.get("store_count", 1))
        per_store_sales_list.append(d.get("monthly_sales", 0) / sc)
    avg_sales_per_store = sum(per_store_sales_list) / n if per_store_sales_list else 0
    avg_store_count = total_stores_all / n
    avg_survival = total_survival / n

    return {
        "avg_sales_per_store": avg_sales_per_store,
        "avg_store_count": avg_store_count,
        "avg_survival_rate": avg_survival,
    }


@router.get("/{district_code}/analysis")
async def get_district_analysis(
    district_code: str,
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    """Rule-based AI analysis commentary for a district report."""
    from ..services.data_service import get_data_service, estimate_rent
    from ..services.simulation_service import get_simulation_service

    svc = get_data_service(industry_code=industry_code)
    d = svc.get_district(district_code)
    if not d:
        raise HTTPException(status_code=404, detail="상권을 찾을 수 없습니다")

    display_name = svc.display_name
    district_name = d.get("district_name", "")
    store_count = max(1, d.get("store_count", 1))
    sales_per_store = int(d["monthly_sales"] / store_count)
    survival_rate = d.get("survival_rate", 0)
    peak_time = d.get("peak_time", "")
    peak_day = d.get("peak_day", "")
    main_age = d.get("main_age_group", "")

    # Estimate rent
    pctile = svc._sales_percentile.get(d["district_code"], 0.5)
    est_rent = estimate_rent(
        d["district_type"], sales_per_store, pctile,
        svc._rent_ranges, industry_code=industry_code,
    )

    # Success probability
    success_prob = svc._calculate_success_probability(d)

    # Industry averages
    avgs = _compute_industry_averages(svc, industry_code)

    # Simulation data for profitability
    sim_svc = get_simulation_service(industry_code=industry_code)
    sim = await sim_svc.simulate(district_code, area_pyeong=15)

    # --- Build time percentage breakdown ---
    monthly_sales = max(1, d.get("monthly_sales", 1))
    time_fields = [
        ("00-06", "time_00_06_sales"),
        ("06-11", "time_06_11_sales"),
        ("11-14", "time_11_14_sales"),
        ("14-17", "time_14_17_sales"),
        ("17-21", "time_17_21_sales"),
        ("21-24", "time_21_24_sales"),
    ]
    time_pcts: dict[str, float] = {}
    for label, field in time_fields:
        val = d.get(field, 0)
        if isinstance(val, (int, float)):
            time_pcts[label] = round(val / monthly_sales * 100, 1)

    peak_pct = time_pcts.get(peak_time, 0)

    # --- Verdict summary ---
    verdict_word = "추천합니다" if success_prob >= 0.65 else (
        "주의가 필요합니다" if success_prob >= 0.45 else "신중히 검토해야 합니다")

    survival_desc = (
        f"생존율 {_fmt_pct(survival_rate)}로 {'매우 안정적' if survival_rate >= 0.9 else '안정적' if survival_rate >= 0.7 else '다소 낮'}이며"
    )

    peak_desc = ""
    if peak_time:
        peak_label = _peak_time_label(peak_time)
        peak_desc = f", {peak_label} 매출 비중이 {peak_pct:.0f}%로 {'직장인 수요가 높습니다' if peak_time == '11-14' else '저녁 수요가 강합니다' if peak_time == '17-21' else '해당 시간대 수요가 집중됩니다'}"

    competition_desc = f". 다만 {display_name} {d.get('store_count', 0)}개가 경쟁하고 있어 차별화가 필요합니다." if d.get("store_count", 0) > 10 else "."

    verdict_summary = (
        f"{district_name} 상권은 {display_name} 창업에 {verdict_word}. "
        f"{survival_desc}{peak_desc}{competition_desc}"
    )

    # --- Profitability comment ---
    sps_man = round(sales_per_store / 10_000)
    avg_sps_man = round(avgs["avg_sales_per_store"] / 10_000)
    sales_vs_avg = "양호합니다" if sps_man >= avg_sps_man else "다소 낮습니다"

    prof_parts = [
        f"점포당 월매출 {sps_man:,}만원으로 서울 {display_name} 평균(약 {avg_sps_man:,}만원) 대비 {sales_vs_avg}."
    ]

    if sim:
        net_profit = sim["break_even"]["monthly_net_profit"]
        be_min = sim["break_even"]["break_even_months_min"]
        be_max = sim["break_even"]["break_even_months_max"]
        net_man = round(net_profit / 10_000)
        prof_parts.append(
            f" 예상 월 순이익은 약 {net_man:,}만원이며, 투자 회수까지 약 {be_min}~{be_max}개월 소요됩니다."
        )

    profitability_comment = "".join(prof_parts)

    # --- Customer comment ---
    cust_parts = []
    if peak_time:
        cust_parts.append(f"{_peak_time_label(peak_time)} 매출이 {peak_pct:.0f}%로 압도적입니다.")
    if main_age:
        cust_parts.append(f" 주요 고객은 {main_age}이며,")
    if peak_day:
        cust_parts.append(f" {_peak_day_label(peak_day)}이 매출 피크입니다.")

    # Suggest improvements for weak time slots
    weak_times = []
    for label, pct in time_pcts.items():
        if pct < 10 and label != "00-06":  # ignore early morning
            weak_times.append(_peak_time_label(label))
    if weak_times:
        cust_parts.append(
            f" {', '.join(weak_times[:2])} 매출이 낮아 "
            "해당 시간대 프로모션으로 보완할 수 있습니다."
        )

    customer_comment = "".join(cust_parts) if cust_parts else (
        f"{district_name}의 고객 데이터를 확인해주세요."
    )

    # --- Competition comment ---
    total_stores = d.get("store_count", 0)
    franchise_stores = d.get("franchise_stores", 0)
    franchise_ratio = round(franchise_stores / max(1, total_stores) * 100)
    new_stores = d.get("new_stores", 0)
    closed_stores = d.get("closed_stores", 0)

    comp_parts = [f"반경 내 {display_name} {total_stores}개"]
    if franchise_ratio > 0:
        comp_parts.append(f" (프랜차이즈 {franchise_ratio}%)")
    comp_parts.append(".")

    if total_stores > avgs["avg_store_count"]:
        comp_parts.append(
            f" 서울 평균({avgs['avg_store_count']:.0f}개) 대비 경쟁이 치열합니다."
        )
    else:
        comp_parts.append(
            f" 서울 평균({avgs['avg_store_count']:.0f}개) 대비 경쟁이 적은 편입니다."
        )

    if closed_stores > new_stores:
        comp_parts.append(
            f" 폐업({closed_stores}개)이 신규({new_stores}개)보다 많아 시장이 위축되고 있습니다."
        )
    elif new_stores > closed_stores:
        comp_parts.append(
            f" 신규({new_stores}개)가 폐업({closed_stores}개)보다 많아 성장 중인 상권입니다."
        )

    competition_comment = "".join(comp_parts)

    # --- Risk comment ---
    risks = svc._identify_risks(d)
    if risks:
        risk_comment = f"주요 리스크는 {risks[0].split('(')[0].strip()}입니다."
        if survival_rate >= 0.8:
            risk_comment += f" 생존율은 {_fmt_pct(survival_rate)}로 {'매우 ' if survival_rate >= 0.9 else ''}안정적이나,"
        else:
            risk_comment += f" 생존율이 {_fmt_pct(survival_rate)}로 주의가 필요하며,"
        risk_comment += " 신규 진입 시 기존 단골 확보가 과제입니다."
        if len(risks) > 1:
            risk_comment += f" 추가로 {', '.join(r.split('(')[0].strip() for r in risks[1:3])}에 유의하세요."
    else:
        risk_comment = (
            f"특별한 리스크 요인이 감지되지 않았습니다. "
            f"생존율 {_fmt_pct(survival_rate)}로 안정적인 상권입니다."
        )

    return {
        "verdict_summary": verdict_summary,
        "profitability_comment": profitability_comment,
        "customer_comment": customer_comment,
        "competition_comment": competition_comment,
        "risk_comment": risk_comment,
    }
