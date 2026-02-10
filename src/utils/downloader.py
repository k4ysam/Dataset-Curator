import aiohttp
import asyncio
from PIL import Image
from io import BytesIO
from typing import List, Optional, Tuple

async def download_image(session: aiohttp.ClientSession, url: str) -> Tuple[str, Optional[Image.Image]]:
    """
    Downloads a single image and returns (url, PIL.Image object).
    Returns (url, None) on failure.
    """
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                data = await response.read()
                image = Image.open(BytesIO(data)).convert("RGB")
                return url, image
            return url, None
    except Exception as e:
        # print(f"Failed to download {url}: {e}")
        return url, None

async def download_images_parallel(urls: List[str], max_concurrency: int = 10) -> dict:
    """
    Downloads multiple images in parallel.
    Returns a dictionary {url: PIL.Image} for successful downloads.
    """
    results = {}
    connector = aiohttp.TCPConnector(limit=max_concurrency)
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
        tasks = [download_image(session, url) for url in urls]
        for completed_task in asyncio.as_completed(tasks):
            url, image = await completed_task
            if image:
                results[url] = image
                
    return results
