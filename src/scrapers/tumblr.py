from .base import BaseScraper
from typing import List
from playwright.sync_api import sync_playwright
import time
import random

class TumblrScraper(BaseScraper):
    def search(self, query: str) -> List[str]:
        print(f"Searching Tumblr for: {query}")
        image_urls = set()
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                # Mobile user agent sometimes yields simpler HTML
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # Tumblr search URL
                formatted_query = query.replace(" ", "+")
                url = f"https://www.tumblr.com/search/{formatted_query}"
                page.goto(url, wait_until="domcontentloaded")
                
                # Scroll to trigger lazy loading
                for _ in range(5):
                    # Look for images inside post containers
                    # Tumblr structure varies. Often articles have images.
                    # We look for img tags that are part of the post content.
                    # 'srcset' often has multiple resolutions.
                    
                    elements = page.query_selector_all("article img") # target images inside articles to avoid avatars
                    if not elements:
                        elements = page.query_selector_all("img") # fallback
                    
                    current_count = len(image_urls)
                    
                    for img in elements:
                        src = img.get_attribute("src")
                        srcset = img.get_attribute("srcset")
                        
                        target_url = src
                        
                        # Try to find largest in srcset
                        if srcset:
                            # format: "url1 500w, url2 1280w"
                            parts = srcset.split(",")
                            best_url = src
                            max_width = 0
                            for part in parts:
                                p_strip = part.strip().split(" ")
                                if len(p_strip) == 2:
                                    u, w = p_strip
                                    try:
                                        width = int(w.replace("w", ""))
                                        if width > max_width:
                                            max_width = width
                                            best_url = u
                                    except:
                                        pass
                            target_url = best_url

                        if target_url and "media.tumblr.com" in target_url and "avatar" not in target_url:
                            # Attempt resolution upgrade if not using srcset
                            if "_500." in target_url or "_400." in target_url or "_250." in target_url:
                                for size in ["_1280.", "_540."]:
                                     # We don't verify if 1280 exists, but it's a common pattern.
                                     # Safer to stick to what we see OR try to upgrade slightly.
                                     # Let's keep it simple: prefer the one we found, unless only low res is available.
                                     pass
                            
                            image_urls.add(target_url)
                            
                    if len(image_urls) >= self.limit:
                        break
                        
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    time.sleep(random.uniform(1.0, 2.0))
                    
                    if len(image_urls) == current_count:
                        break
                
                browser.close()
                
        except Exception as e:
            print(f"Error scraping Tumblr: {e}")
            
        return list(image_urls)[:self.limit]
