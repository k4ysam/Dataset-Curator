from .base import BaseScraper
from typing import List
from playwright.sync_api import sync_playwright
import time
import random
import urllib.parse

class GoogleScraper(BaseScraper):
    def search(self, query: str) -> List[str]:
        print(f"Searching Google for: {query}")
        image_urls = set()
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # Google Images URL
                # q=query, tbm=isch (images)
                encoded_query = urllib.parse.quote(query)
                url = f"https://www.google.com/search?q={encoded_query}&tbm=isch"
                
                page.goto(url, wait_until="domcontentloaded")
                
                # Accept cookies if the dialog appears (common in EU/headless)
                # We can try to click "Reject all" or "Accept all" if we see them.
                # Selectors vary by region. 
                # Simplest is just try to scroll and see if images load.
                
                # Scroll to trigger lazy loading
                for _ in range(3):
                    # Google images are usually in divs with specific classes, 
                    # but easiest is to look for img tags that are result images.
                    # They usually have data-src or src.
                    
                    # We look for 'img' that are likely results. 
                    # Google uses Base64 for many thumbnails.
                    # We might get base64 or actual URLs.
                    # Real full-res extraction on Google is hard (needs clicking).
                    # For MVP, getting the thumbnail or preview web version is acceptable 
                    # IF "Scrape-to-Train" implies high quality, we might need to click.
                    # Clicking every image is slow.
                    # Let's try to get the standard displayed images.
                    
                    elements = page.query_selector_all("img")
                    
                    current_count = len(image_urls)
                    
                    for img in elements:
                        src = img.get_attribute("src")
                        # Google uses data-src sometimes
                        if not src:
                            src = img.get_attribute("data-src")
                            
                        if src and "http" in src and "google" not in src:
                             # Filter out google logos/icons
                             # Actually valid images might be encrypted-tbn0.gstatic.com
                             if "gstatic.com" in src:
                                 image_urls.add(src)
                             elif "http" in src:
                                 image_urls.add(src)

                    if len(image_urls) >= self.limit:
                        break
                        
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(random.uniform(1.0, 2.0))
                    
                    if len(image_urls) == current_count:
                         # Try clicking "Show more" if visible?
                         pass
                
                browser.close()
                
        except Exception as e:
            print(f"Error scraping Google: {e}")
            
        return list(image_urls)[:self.limit]
