from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic
from dataclasses import dataclass
from datetime import datetime
import httpx
import structlog

T = TypeVar("T")
logger = structlog.get_logger()


@dataclass
class CollectionResult(Generic[T]):
    data: list[T]
    source: str
    collected_at: datetime
    total_count: int
    success_count: int
    error_count: int
    errors: list[str]


class BaseCollector(ABC):
    def __init__(self, name: str, base_url: str | None = None):
        self.name = name
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "BaseCollector":
        self._client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "BuilderCuration/0.1.0"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("Collector not initialized. Use async context manager.")
        return self._client

    @abstractmethod
    async def collect(self, **params: Any) -> CollectionResult[Any]:
        pass

    @abstractmethod
    async def validate(self, data: Any) -> bool:
        pass

    async def fetch_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    async def fetch_html(self, url: str) -> str:
        response = await self.client.get(url)
        response.raise_for_status()
        return response.text
