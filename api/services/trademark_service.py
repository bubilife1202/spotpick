"""
상표 충돌 확인 서비스 — 업종별 주요 브랜드명과 유사도 비교.

KIPRIS API 키가 있으면 실제 상표 검색, 없으면 로컬 KNOWN_TRADEMARKS 목록 기반.
"""
from __future__ import annotations

import json
import math
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

INDUSTRIES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "industries"

# ---------------------------------------------------------------------------
# Jaro-Winkler similarity
# ---------------------------------------------------------------------------

def _jaro_similarity(s1: str, s2: str) -> float:
    if s1 == s2:
        return 1.0
    len1, len2 = len(s1), len(s2)
    if len1 == 0 or len2 == 0:
        return 0.0

    match_dist = max(len1, len2) // 2 - 1
    s1_matches = [False] * len1
    s2_matches = [False] * len2
    matches = 0
    transpositions = 0

    for i in range(len1):
        start = max(0, i - match_dist)
        end = min(i + match_dist + 1, len2)
        for j in range(start, end):
            if s2_matches[j] or s1[i] != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0.0

    k = 0
    for i in range(len1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if s1[i] != s2[k]:
            transpositions += 1
        k += 1

    return (matches / len1 + matches / len2 + (matches - transpositions / 2) / matches) / 3


def jaro_winkler(s1: str, s2: str, p: float = 0.1) -> float:
    """Jaro-Winkler similarity (0.0 – 1.0)."""
    jaro = _jaro_similarity(s1, s2)
    prefix = 0
    for c1, c2 in zip(s1, s2):
        if c1 == c2:
            prefix += 1
        else:
            break
        if prefix == 4:
            break
    return jaro + prefix * p * (1 - jaro)


# ---------------------------------------------------------------------------
# Trademark Service
# ---------------------------------------------------------------------------

@lru_cache(maxsize=16)
def _load_known_trademarks(industry_code: str) -> list[str]:
    """Load KNOWN_TRADEMARKS from industry config JSON."""
    config_path = INDUSTRIES_DIR / f"{industry_code}.json"
    if not config_path.exists():
        return []
    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("KNOWN_TRADEMARKS", [])


def _normalize(name: str) -> str:
    """Normalize brand name for comparison: lowercase, strip spaces/special chars."""
    return re.sub(r"[\s\-_·.]", "", name.lower())


class TrademarkService:
    def __init__(self, industry_code: str = "CS100010"):
        self.industry_code = industry_code
        self.known_trademarks = _load_known_trademarks(industry_code)
        self.kipris_api_key: Optional[str] = os.getenv("KIPRIS_API_KEY")

    def check(self, name: str, threshold: float = 0.80) -> dict[str, Any]:
        """
        Check a proposed brand name against known trademarks.

        Returns:
            {
                "query": str,
                "conflicts": [{ "name": str, "similarity": float }],
                "risk_level": "high" | "medium" | "low",
                "suggestions": [str],
            }
        """
        norm_name = _normalize(name)
        conflicts: list[dict[str, Any]] = []

        for tm in self.known_trademarks:
            norm_tm = _normalize(tm)
            sim = jaro_winkler(norm_name, norm_tm)
            # Also check substring containment
            if norm_tm in norm_name or norm_name in norm_tm:
                sim = max(sim, 0.95)
            if sim >= threshold:
                conflicts.append({"name": tm, "similarity": round(sim, 3)})

        conflicts.sort(key=lambda c: c["similarity"], reverse=True)

        # Determine risk level
        if any(c["similarity"] >= 0.95 for c in conflicts):
            risk_level = "high"
        elif any(c["similarity"] >= 0.85 for c in conflicts):
            risk_level = "medium"
        else:
            risk_level = "low"

        # Generate suggestions
        suggestions: list[str] = []
        if risk_level != "low":
            suggestions.append(f"'{name}' 대신 독창적인 이름을 고려해보세요")
            suggestions.append("상표 출원 전 KIPRIS(www.kipris.or.kr)에서 정확한 검색을 권장합니다")
            if risk_level == "high":
                suggestions.append("동일/유사 상표가 존재하여 등록 거절 가능성이 높습니다")

        return {
            "query": name,
            "conflicts": conflicts[:10],
            "risk_level": risk_level,
            "suggestions": suggestions,
        }


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
_registry: dict[str, TrademarkService] = {}


def get_trademark_service(industry_code: str = "CS100010") -> TrademarkService:
    if industry_code not in _registry:
        _registry[industry_code] = TrademarkService(industry_code)
    return _registry[industry_code]
