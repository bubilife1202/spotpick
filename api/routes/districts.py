from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/districts")


@router.get("/search")
def search_districts(
    q: str = Query("", min_length=0, description="검색어 (상권명, 구, 역 등)"),
    limit: int = Query(20, ge=1, le=50),
):
    from ..services.data_service import get_data_service

    svc = get_data_service()
    q_lower = q.strip().lower()

    if not q_lower:
        return {"results": [], "total": 0}

    matches: list[dict] = []
    for d in svc.districts:
        name: str = d.get("district_name", "")
        dtype: str = d.get("district_type", "")
        if q_lower in name.lower() or q_lower in dtype.lower():
            matches.append(
                {
                    "code": d["district_code"],
                    "name": name,
                    "type": dtype,
                    "monthly_sales": d.get("monthly_sales"),
                    "store_count": d.get("store_count"),
                    "survival_rate": d.get("survival_rate"),
                }
            )
        if len(matches) >= limit:
            break

    return {"results": matches, "total": len(matches)}


@router.get("/list")
def list_districts(
    district_type: str | None = Query(None, description="상권유형 필터 (골목상권, 발달상권, 전통시장, 관광특구)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    from ..services.data_service import get_data_service

    svc = get_data_service()
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
