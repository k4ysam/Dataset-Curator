from .base import BaseScraper
from typing import List
from playwright.sync_api import sync_playwright
import time
import random

class PinterestScraper(BaseScraper):
    def search(self, query: str) -> List[str]:
        print(f"Searching Pinterest for: {query}")
        image_urls = set()
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Use a consistent user agent to avoid immediate blocks, but Pinterest is tough.
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # Pinterest search URL
                url = f"https://www.pinterest.com/search/pins/?q={query}"
                page.goto(url, wait_until="domcontentloaded")
                
                # Scroll loop
                # We need to scroll to trigger lazy loading
                # Pinterest often requires login for deep scrolling, so we might only get the first batch.
                
                no_new_data_count = 0
                max_scrolls = 5  # Limit scrolls to avoid timeouts or blocks
                
                for _ in range(max_scrolls):
                    # Extract images
                    # Pinterest images usually have '564x' or '236x' in the URL. 
                    # We want the highest res possible.
                    # Selectors might change, but standard img tags are a good bet.
                    
                    elements = page.query_selector_all("img")
                    current_count = len(image_urls)
                    
                    for img in elements:
                        src = img.get_attribute("src")
                        if src and "pinimg.com" in src:
                            # Filter out profile pics and tiny thumbnails
                            if "75x75" in src or "60x60" in src or "30x30" in src:
                                continue
                                
                            # Convert to high res
                            # Common patterns: 236x, 474x, 564x
                            # We want originals or max available. 
                            # 'originals' is sometimes an option but not always predictable.
                            # safely upgrade to 564x (standard high quality for pins) or keep original if it looks large.
                            
                            high_res = src
                            for low in ["/236x/", "/474x/"]:
                                if low in high_res:
                                    high_res = high_res.replace(low, "/564x/")
                            
                            image_urls.add(high_res)
                            
                    if len(image_urls) >= self.limit:
                        break
                        
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(random.uniform(1.0, 2.0))
                    
                    if len(image_urls) == current_count:
                        no_new_data_count += 1
                        if no_new_data_count > 1:
                            break
                    else:
                        no_new_data_count = 0
                
                browser.close()
                
        except Exception as e:
            print(f"Error scraping Pinterest: {e}")
            
        return list(image_urls)[:self.limit]
