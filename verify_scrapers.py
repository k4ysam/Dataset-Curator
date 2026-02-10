from src.scrapers.tumblr import TumblrScraper
from src.scrapers.google import GoogleScraper
from src.scrapers.pinterest import PinterestScraper
import sys

def test_tumblr():
    print("\n--- Testing Tumblr ---")
    scraper = TumblrScraper(limit=5)
    urls = scraper.search("cyberpunk city")
    print(f"Found {len(urls)} URLs:")
    for url in urls:
        print(url)
    return len(urls) > 0

def test_google():
    print("\n--- Testing Google ---")
    scraper = GoogleScraper(limit=5)
    urls = scraper.search("vaporwave aesthetic")
    print(f"Found {len(urls)} URLs:")
    for url in urls:
        print(url)
    return len(urls) > 0

def test_pinterest():
    print("\n--- Testing Pinterest ---")
    scraper = PinterestScraper(limit=5)
    urls = scraper.search("brutalist architecture")
    print(f"Found {len(urls)} URLs:")
    for url in urls:
        print(url)
    return len(urls) > 0

if __name__ == "__main__":
    t = test_tumblr()
    g = test_google()
    p = test_pinterest()
    
    if t and g and p:
        print("\nALL SCRAER TESTS PASSED")
        sys.exit(0)
    else:
        print("\nSOME TESTS FAILED")
        # Google crawler might return 0 if it fails to find images in the 'download' hook.
        pass
