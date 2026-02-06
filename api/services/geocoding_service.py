"""
Geocoding service (Seoul-only beta)

- Uses OpenStreetMap Nominatim (no API key)
- Caches results on disk to avoid repeated external calls
- Applies a simple rate limit to respect Nominatim usage policy
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import httpx


@dataclass(frozen=True)
class Coordinates:
    lat: float
    lng: float


class GeocodingService:
    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[2]
        self._cache_path = root / "data" / "cache" / "geocode_cache.json"
        self._cache: dict[str, Optional[Coordinates]] = {}

        self._lock = asyncio.Lock()
        self._last_request_ts: float = 0.0
        self._client: Optional[httpx.AsyncClient] = None

        self._load_cache()

    def _load_cache(self) -> None:
        try:
            if not self._cache_path.exists():
                return
            raw = json.loads(self._cache_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return
            for q, v in raw.items():
                if not isinstance(q, str):
                    continue
                if v is None:
                    self._cache[q] = None
                    continue
                if not isinstance(v, dict):
                    continue
                lat = v.get("lat")
                lng = v.get("lng")
                if isinstance(lat, (int, float)) and isinstance(lng, (int, float)):
                    self._cache[q] = Coordinates(lat=float(lat), lng=float(lng))
        except Exception:
            # Cache should never take down the API.
            return

    def _save_cache(self) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload: dict[str, Optional[dict[str, float]]] = {}
            for q, v in self._cache.items():
                if v is None:
                    payload[q] = None
                else:
                    payload[q] = {"lat": v.lat, "lng": v.lng}
            self._cache_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            return

    async def geocode(self, query: str) -> Optional[Coordinates]:
        q = (query or "").strip()
        if not q:
            return None

        cached = self._cache.get(q)
        if cached is not None or q in self._cache:
            return cached

        async with self._lock:
            cached = self._cache.get(q)
            if cached is not None or q in self._cache:
                return cached

            # Respect Nominatim usage policy (basic throttling)
            elapsed = time.time() - self._last_request_ts
            if elapsed < 1.0:
                await asyncio.sleep(1.0 - elapsed)

            if self._client is None:
                # Nominatim requires a descriptive User-Agent.
                self._client = httpx.AsyncClient(
                    timeout=10.0,
                    headers={
                        "User-Agent": "builder_curation/0.1 (local dev)",
                        "Accept-Language": "ko",
                    },
                )

            try:
                resp = await self._client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": q,
                        "format": "jsonv2",
                        "limit": 1,
                        "countrycodes": "kr",
                    },
                )
                resp.raise_for_status()
                items = resp.json()
                self._last_request_ts = time.time()

                if isinstance(items, list) and items:
                    first = items[0]
                    lat = first.get("lat")
                    lon = first.get("lon")
                    if isinstance(lat, str) and isinstance(lon, str):
                        coords = Coordinates(lat=float(lat), lng=float(lon))
                        self._cache[q] = coords
                        self._save_cache()
                        return coords
            except Exception:
                # Don't cache transient failures; just return None.
                return None

            # Cache negative result to avoid repeated misses.
            self._cache[q] = None
            self._save_cache()
            return None


_geocoding_service: Optional[GeocodingService] = None


def get_geocoding_service() -> GeocodingService:
    global _geocoding_service
    if _geocoding_service is None:
        _geocoding_service = GeocodingService()
    return _geocoding_service

