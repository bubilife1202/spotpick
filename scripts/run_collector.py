import asyncio
import os
from datetime import datetime

from collectors.public_data import SemasCollector
from collectors.crawlers import NaverPlaceCrawler
from collectors.common.storage import DataStorage


async def run_semas_collection():
    api_key = os.getenv("DATA_GO_KR_API_KEY")
    if not api_key:
        print("DATA_GO_KR_API_KEY not set, skipping SEMAS collection")
        return

    storage = DataStorage()

    async with SemasCollector(api_key) as collector:
        seoul_districts = [
            "11680",  # 강남구
            "11740",  # 강동구
            "11305",  # 강북구
            "11500",  # 강서구
        ]

        for district in seoul_districts:
            print(f"Collecting stores for district: {district}")
            result = await collector.collect(type="stores", region_code=district)

            print(f"  - Collected: {result.success_count}, Errors: {result.error_count}")

            if result.data:
                storage.save_jsonl(
                    [vars(s) for s in result.data],
                    source="semas",
                    filename=f"stores_{district}",
                )


async def run_naver_collection():
    storage = DataStorage()

    async with NaverPlaceCrawler() as crawler:
        queries = [
            ("강남역", "커피"),
            ("홍대", "커피"),
            ("이태원", "커피"),
        ]

        for region, category in queries:
            print(f"Crawling: {region} {category}")
            result = await crawler.collect(
                query=category,
                region=region,
                max_results=50,
            )

            print(f"  - Collected: {result.success_count}, Errors: {result.error_count}")

            if result.data:
                storage.save_jsonl(
                    [vars(p) for p in result.data],
                    source="naver_place",
                    filename=f"{region}_{category}",
                )


async def main():
    print(f"Starting collection at {datetime.now()}")

    await run_semas_collection()
    await run_naver_collection()

    print(f"Collection completed at {datetime.now()}")


if __name__ == "__main__":
    asyncio.run(main())
