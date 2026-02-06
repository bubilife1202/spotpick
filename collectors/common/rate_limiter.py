import asyncio
import random
from collections import deque
from datetime import datetime, timedelta


class RateLimiter:
    def __init__(
        self,
        requests_per_second: float = 1.0,
        min_delay: float = 1.0,
        max_delay: float = 3.0,
        burst_size: int = 1,
    ):
        self.min_interval = 1.0 / requests_per_second
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.burst_size = burst_size
        self._timestamps: deque[datetime] = deque(maxlen=burst_size)
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = datetime.now()

            while len(self._timestamps) >= self.burst_size:
                oldest = self._timestamps[0]
                elapsed = (now - oldest).total_seconds()
                if elapsed < self.min_interval * self.burst_size:
                    wait_time = self.min_interval * self.burst_size - elapsed
                    await asyncio.sleep(wait_time)
                    now = datetime.now()
                else:
                    break

            self._timestamps = deque(
                [
                    ts
                    for ts in self._timestamps
                    if (now - ts).total_seconds() < self.min_interval * self.burst_size
                ],
                maxlen=self.burst_size,
            )

            random_delay = random.uniform(self.min_delay, self.max_delay)
            await asyncio.sleep(random_delay)

            self._timestamps.append(datetime.now())

    async def __aenter__(self) -> "RateLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *args: object) -> None:
        pass


class DomainRateLimiter:
    def __init__(self, default_rps: float = 1.0):
        self._limiters: dict[str, RateLimiter] = {}
        self._default_rps = default_rps
        self._lock = asyncio.Lock()

    async def acquire(self, domain: str) -> None:
        async with self._lock:
            if domain not in self._limiters:
                self._limiters[domain] = RateLimiter(requests_per_second=self._default_rps)

        await self._limiters[domain].acquire()
