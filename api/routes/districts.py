from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/districts")


@router.get("/search")
def search_districts(
    q: str = Query("", min_length=0, description="검색어 (상권명, 구, 역 등)"),
    limit: int = Query(20, ge=1, le=50),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    from ..services.data_service import get_data_service

    svc = get_data_service(industry_code=industry_code)
    q_clean = (q or "").strip()
    q_lower = q_clean.lower()

    if not q_lower:
        return {"results": [], "total": 0}

    # Use DataService ranking to avoid "강남" -> only "강남구청..." results due to input order + early break.
    raw = svc.search_districts(q_clean, limit=limit)

    def clamp_rate(v: object) -> float | None:
        try:
            if isinstance(v, (int, float)):
                return float(max(0.0, min(1.0, float(v))))
        except Exception:
            return None
        return None

    results: list[dict[str, object]] = []
    for d in raw:
        name = d.get("district_name", "")
        dtype = d.get("district_type", "")
        results.append(
            {
                "code": d["district_code"],
                "name": name,
                "type": dtype,
                "monthly_sales": d.get("monthly_sales"),
                "store_count": d.get("store_count"),
                "survival_rate": clamp_rate(d.get("survival_rate")),
            }
        )

    return {"results": results, "total": len(results)}


@router.get("/list")
def list_districts(
    district_type: str | None = Query(None, description="상권유형 필터 (골목상권, 발달상권, 전통시장, 관광특구)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    industry_code: str = Query("CS100010", description="업종 코드"),
):
    from ..services.data_service import get_data_service

    svc = get_data_service(industry_code=industry_code)
    filtered = svc.districts

    if district_type:
        filtered = [d for d in filtered if d.get("district_type") == district_type]

    total = len(filtered)
    page = filtered[offset : offset + limit]

    return {
        "results": [
            {
                "code": d["district_code"],
                "name": d["district_name"],
                "type": d.get("district_type", ""),
            }
            for d in page
        ],
        "total": total,
    }
