import asyncio
import os
import sys
from src.scrapers.google import GoogleScraper
from src.utils.downloader import download_images_parallel

# Ensure src is in path
sys.path.append(os.getcwd())

# Ensure src is in path
sys.path.append(os.getcwd())

def test_scrape():
    print("Scraping Google...")
    try:
        scraper = GoogleScraper(limit=5)
        # Verify if running in loop
        import asyncio
        try:
            loop = asyncio.get_running_loop()
            print("Warning: Running inside event loop")
        except RuntimeError:
            print("No active event loop (Good for sync Playwright)")
            
        urls = scraper.search("cyberpunk city")
        print(f"Found {len(urls)} URLs")
        return urls
    except Exception as e:
        print(f"Scraping failed: {e}")
        return []

async def test_download(urls):
    print("\nDownloading...")
    results = await download_images_parallel(urls)
    print(f"Downloaded {len(results)} images")
    return results

if __name__ == "__main__":
    urls = test_scrape()
    if urls:
        results = asyncio.run(test_download(urls))
        if len(results) == 0:
            print("FAILURE: No images downloaded. This confirms the issue.")
        else:
            print("SUCCESS: Images downloaded.")
    else:
        print("Scraping failed, cannot test download.")
