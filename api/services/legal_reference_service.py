"""Legal reference data loader service.

Loads static legal reference values from ``api/data/legal_references.json``
and provides typed accessor methods for advisor services.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast


JSONDict = dict[str, object]


def _normalize_dict(value: object) -> JSONDict:
    if not isinstance(value, dict):
        return {}
    typed = cast(dict[object, object], value)
    out: JSONDict = {}
    for key_obj, val_obj in typed.items():
        if isinstance(key_obj, str):
            out[key_obj] = val_obj
    return out


LEGAL_REFS_PATH = Path(__file__).parent.parent / "data" / "legal_references.json"


class LegalReferenceService:
    """Static legal reference service with in-memory cache."""

    def __init__(self) -> None:
        self._data: JSONDict = {}
        self._load()

    def _load(self) -> None:
        if not LEGAL_REFS_PATH.exists():
            self._data = {}
            return

        try:
            with open(LEGAL_REFS_PATH, encoding="utf-8") as f:
                payload = cast(object, json.load(f))
            self._data = _normalize_dict(payload)
        except Exception:
            self._data = {}

    def get_all(self) -> JSONDict:
        return self._data

    def get_meta(self) -> JSONDict:
        return _normalize_dict(self._data.get("meta", {}))

    def get_tax_rules(self) -> JSONDict:
        return _normalize_dict(self._data.get("tax", {}))

    def get_labor_rules(self) -> JSONDict:
        return _normalize_dict(self._data.get("labor", {}))

    def get_lease_rules(self) -> JSONDict:
        return _normalize_dict(self._data.get("lease", {}))

    def get_compliance_rules(self) -> JSONDict:
        return _normalize_dict(self._data.get("compliance", {}))

    def get_glossary(self) -> dict[str, str]:
        raw = _normalize_dict(self._data.get("glossary", {}))
        out: dict[str, str] = {}
        for k, v in raw.items():
            if isinstance(v, str):
                out[k] = v
        return out


_service: LegalReferenceService | None = None


def get_legal_reference_service() -> LegalReferenceService:
    global _service
    if _service is None:
        _service = LegalReferenceService()
    return _service
