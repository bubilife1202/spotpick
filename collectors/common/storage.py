import json
from pathlib import Path
from datetime import datetime
from typing import Any
import structlog

logger = structlog.get_logger()


class DataStorage:
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_dated_path(self, source: str, date: datetime | None = None) -> Path:
        if date is None:
            date = datetime.now()
        path = self.base_path / source / date.strftime("%Y/%m/%d")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def save_json(
        self,
        data: Any,
        source: str,
        filename: str,
        date: datetime | None = None,
    ) -> Path:
        path = self._get_dated_path(source, date)
        filepath = path / f"{filename}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        logger.info(
            "saved_json", filepath=str(filepath), records=len(data) if isinstance(data, list) else 1
        )
        return filepath

    def save_jsonl(
        self,
        data: list[dict[str, Any]],
        source: str,
        filename: str,
        date: datetime | None = None,
    ) -> Path:
        path = self._get_dated_path(source, date)
        filepath = path / f"{filename}.jsonl"

        with open(filepath, "w", encoding="utf-8") as f:
            for record in data:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

        logger.info("saved_jsonl", filepath=str(filepath), records=len(data))
        return filepath

    def load_json(self, source: str, filename: str, date: datetime) -> Any:
        path = self._get_dated_path(source, date)
        filepath = path / f"{filename}.json"

        with open(filepath, encoding="utf-8") as f:
            return json.load(f)

    def list_files(self, source: str, pattern: str = "*.json") -> list[Path]:
        source_path = self.base_path / source
        if not source_path.exists():
            return []
        return sorted(source_path.rglob(pattern))
