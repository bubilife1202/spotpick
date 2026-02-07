"""
Naver DataLab Search Trend Service

Integrates with Naver DataLab API to fetch keyword search trends.
Supports trend analysis and keyword comparison for industry and district research.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any
import httpx


class TrendService:
    """
    Service for fetching search trends from Naver DataLab API.

    API Spec:
    - URL: https://openapi.naver.com/v1/datalab/search
    - Method: POST
    - Headers: X-Naver-Client-Id, X-Naver-Client-Secret
    - Body: { startDate, endDate, timeUnit, keywordGroups }
    - Response: { results: [{title, keywords, data: [{period, ratio}]}] }
    """

    def __init__(self, client_id: str | None = None, client_secret: str | None = None):
        """
        Initialize TrendService with Naver API credentials.

        Args:
            client_id: Naver Client ID (defaults to NAVER_CLIENT_ID env var)
            client_secret: Naver Client Secret (defaults to NAVER_CLIENT_SECRET env var)
        """
        self.client_id = client_id or os.getenv("NAVER_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("NAVER_CLIENT_SECRET")

        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Naver API credentials not found. "
                "Set NAVER_CLIENT_ID and NAVER_CLIENT_SECRET in .env"
            )

        self.api_url = "https://openapi.naver.com/v1/datalab/search"

    def _get_default_date_range(self, months: int = 12) -> tuple[str, str]:
        """
        Get default date range for trend analysis.

        Args:
            months: Number of months to look back (default: 12)

        Returns:
            Tuple of (start_date, end_date) in YYYY-MM-DD format
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)

        return (
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )

    async def get_search_trend(
        self,
        keywords: list[str],
        start_date: str | None = None,
        end_date: str | None = None,
        time_unit: str = "month",
        device: str = ""  # "", "pc", "mo"
    ) -> dict[str, Any]:
        """
        Fetch search trend for given keywords.

        Args:
            keywords: List of keywords to analyze (max 5)
            start_date: Start date in YYYY-MM-DD format (default: 12 months ago)
            end_date: End date in YYYY-MM-DD format (default: today)
            time_unit: Time granularity - "date", "week", or "month" (default: "month")
            device: Device filter - "", "pc", or "mo" (default: "" = all devices)

        Returns:
            API response with trend data

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        if not keywords or len(keywords) > 5:
            raise ValueError("Keywords must be a non-empty list with max 5 items")

        # Use default date range if not provided
        if not start_date or not end_date:
            start_date, end_date = self._get_default_date_range()

        # Build keyword groups
        keyword_groups = [
            {
                "groupName": keyword,
                "keywords": [keyword]
            }
            for keyword in keywords
        ]

        # Prepare request payload
        payload = {
            "startDate": start_date,
            "endDate": end_date,
            "timeUnit": time_unit,
            "keywordGroups": keyword_groups
        }

        if device:
            payload["device"] = device

        # Make API request
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
            "Content-Type": "application/json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()

    async def compare_keywords(
        self,
        keywords: list[str],
        months: int = 12,
        device: str = ""
    ) -> dict[str, Any]:
        """
        Compare search trends for multiple keywords.

        Args:
            keywords: List of keywords to compare (max 5)
            months: Number of months to analyze (default: 12)
            device: Device filter - "", "pc", or "mo" (default: "" = all devices)

        Returns:
            Normalized trend data with comparison insights
        """
        if not keywords or len(keywords) > 5:
            raise ValueError("Keywords must be a non-empty list with max 5 items")

        start_date, end_date = self._get_default_date_range(months)

        raw_data = await self.get_search_trend(
            keywords=keywords,
            start_date=start_date,
            end_date=end_date,
            time_unit="month",
            device=device
        )

        # Transform and enrich response
        results = raw_data.get("results", [])

        # Calculate average ratios for ranking
        averages = []
        for result in results:
            data_points = result.get("data", [])
            avg_ratio = sum(point["ratio"] for point in data_points) / len(data_points) if data_points else 0
            averages.append({
                "keyword": result["title"],
                "average_ratio": avg_ratio,
                "data": data_points
            })

        # Sort by average ratio (descending)
        averages.sort(key=lambda x: x["average_ratio"], reverse=True)

        return {
            "keywords": keywords,
            "period": {
                "start": start_date,
                "end": end_date
            },
            "trends": averages,
            "summary": {
                "top_keyword": averages[0]["keyword"] if averages else None,
                "top_average": averages[0]["average_ratio"] if averages else 0
            }
        }

    async def get_district_trend(
        self,
        base_keyword: str,
        districts: list[str],
        months: int = 12
    ) -> dict[str, Any]:
        """
        Compare search trends across districts for a base keyword.

        Example: "카페" base keyword with ["강남", "홍대", "이태원"] districts

        Args:
            base_keyword: Base keyword to append to each district
            districts: List of district names (max 5)
            months: Number of months to analyze (default: 12)

        Returns:
            Trend comparison data
        """
        if not districts or len(districts) > 5:
            raise ValueError("Districts must be a non-empty list with max 5 items")

        # Build combined keywords
        keywords = [f"{district} {base_keyword}" for district in districts]

        return await self.compare_keywords(keywords=keywords, months=months)


# Singleton instance registry
_trend_service_instance: TrendService | None = None


def get_trend_service() -> TrendService:
    """
    Get or create TrendService singleton instance.

    Returns:
        TrendService instance
    """
    global _trend_service_instance

    if _trend_service_instance is None:
        _trend_service_instance = TrendService()

    return _trend_service_instance
