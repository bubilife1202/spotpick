"""Industries API — list available industry types."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/industries")
async def list_industries():
    """Return list of available industry codes and names."""
    from config.industry_config import get_available_industries

    industries = get_available_industries()
    return {"industries": industries, "total": len(industries)}


@router.get("/industries/{industry_code}/config")
async def get_industry_config(industry_code: str):
    """Return public config for a specific industry (questions, display_name, icon, etc.)."""
    from config.industry_config import load_industry_config

    try:
        cfg = load_industry_config(industry_code)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Industry {industry_code} not found")

    return {
        "code": cfg.get("code", industry_code),
        "name": cfg.get("name", ""),
        "display_name": cfg.get("display_name", ""),
        "icon": cfg.get("icon", "🏪"),
        "color": cfg.get("color", "blue"),
        "INITIAL_QUESTIONS": cfg.get("INITIAL_QUESTIONS", []),
        "DAILY_SCENARIO": cfg.get("DAILY_SCENARIO", {}),
    }
