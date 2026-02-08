"""이벤트 수집 — JSONL 파일 로깅 (경량)."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/analytics")

LOG_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "analytics"
LOG_DIR.mkdir(parents=True, exist_ok=True)


class EventPayload(BaseModel):
    event: str = ""
    session_id: str = ""
    timestamp: str = ""
    page: str = ""
    referrer: str = ""
    props: dict[str, Any] = {}


@router.post("/event")
async def receive_event(payload: EventPayload, request: Request) -> dict[str, bool]:
    """이벤트 수신 → JSONL 파일에 append."""
    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:12]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"events_{today}.jsonl"

    entry = {
        "event": payload.event,
        "session_id": payload.session_id,
        "timestamp": payload.timestamp or datetime.now(timezone.utc).isoformat(),
        "page": payload.page,
        "referrer": payload.referrer,
        "ip_hash": ip_hash,
        "props": payload.props,
    }

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return {"ok": True}


@router.get("/summary")
def get_summary(date: str = "") -> dict[str, Any]:
    """일별 이벤트 집계 (내부용)."""
    target_date = date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"events_{target_date}.jsonl"

    if not log_file.exists():
        return {"date": target_date, "total_events": 0, "unique_sessions": 0, "events": {}}

    events: dict[str, int] = {}
    sessions: set[str] = set()

    with open(log_file, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)
                ev = entry.get("event", "unknown")
                events[ev] = events.get(ev, 0) + 1
                sid = entry.get("session_id")
                if sid:
                    sessions.add(sid)
            except Exception:
                continue

    return {
        "date": target_date,
        "total_events": sum(events.values()),
        "unique_sessions": len(sessions),
        "events": events,
    }
