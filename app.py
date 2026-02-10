import streamlit as st
import asyncio
import aiohttp
import io
from PIL import Image
import numpy as np

# Adjust python path if needed or rely on src package
import sys
import os
sys.path.append(os.getcwd())

from src.scrapers.tumblr import TumblrScraper
from src.scrapers.google import GoogleScraper
from src.scrapers.pinterest import PinterestScraper
from src.ai.processor import ImageProcessor
from src.utils.downloader import download_images_parallel, download_image
from src.utils.exporter import create_dataset_zip, generate_filename

# --- Configuration & Styling ---
st.set_page_config(page_title="Dataset Curator AI", layout="wide")

st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        border-radius: 5px;
    }
    .img-container {
        position: relative;
    }
</style>
""", unsafe_allow_html=True)

# --- State Management ---
if "scraped_urls" not in st.session_state:
    st.session_state.scraped_urls = [] # List of URL strings
if "basket" not in st.session_state:
    st.session_state.basket = set() # Set of URLs
if "embeddings" not in st.session_state:
    st.session_state.embeddings = {} # url -> np.network
if "images_cache" not in st.session_state:
    st.session_state.images_cache = {} # url -> PIL.Image (LRU-like manual management if needed, but for now allow unrestricted RAM usage as per request)

# --- Resources ---
@st.cache_resource
def get_processor():
    return ImageProcessor()

processor = get_processor()

# --- helper functions ---
async def download_and_embed(urls):
    """
    Downloads images that aren't in cache, and computes embeddings for them.
    Updates session_state.
    """
    missing_urls = [u for u in urls if u not in st.session_state.images_cache]
    
    if missing_urls:
        with st.spinner(f"Downloading {len(missing_urls)} images for analysis..."):
            # Custom downloader
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            connector = aiohttp.TCPConnector(limit=20)
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                 # Reconstruct download_images_parallel inline or import
                 # Importing helper
                 from src.utils.downloader import download_image
                 tasks = [download_image(session, url) for url in missing_urls]
                 results = await asyncio.gather(*tasks)
                 
            for url, img in results:
                if img:
                     st.session_state.images_cache[url] = img
    
    # Compute embeddings for new images
    valid_urls_to_embed = [u for u in urls if u in st.session_state.images_cache and u not in st.session_state.embeddings]
    
    newly_embedded = 0
    if valid_urls_to_embed:
        with st.spinner(f"Computing embeddings for {len(valid_urls_to_embed)} images..."):
             images = [st.session_state.images_cache[u] for u in valid_urls_to_embed]
             # Batch processing
             embeddings = processor.encode_images(images)
             for i, url in enumerate(valid_urls_to_embed):
                 st.session_state.embeddings[url] = embeddings[i]
             newly_embedded = len(valid_urls_to_embed)
    
    return newly_embedded

def find_similar(target_url):
    """
    Re-ranks lists based on similarity to target_url
    """
    if target_url not in st.session_state.embeddings:
        st.warning("Embedding not found for this image.")
        return

    target_emb = st.session_state.embeddings[target_url]
    
    # Calculate similarity with ALL other known embeddings
    urls = list(st.session_state.embeddings.keys())
    embs = np.array([st.session_state.embeddings[u] for u in urls])
    
    sims = processor.calculate_similarity(target_emb, embs)
    
    # Sort urls by similarity
    # zip, sort, unzip
    sorted_pairs = sorted(zip(urls, sims), key=lambda x: x[1], reverse=True)
    sorted_urls = [u for u, s in sorted_pairs]
    
    # Update display list
    st.session_state.scraped_urls = sorted_urls
    st.success("Gallery re-ranked by similarity!")

# --- Sidebar ---
with st.sidebar:
    st.title("Search")
    
    scraper_choice = st.selectbox("Source", ["Tumblr", "Pinterest", "Google"])
    search_query = st.text_input("Prompt", "cyberpunk city aesthetic")
    limit = st.slider("Max Results", 10, 100, 50)
    
    if st.button("Scrape", type="primary"):
        with st.spinner(f"Scraping {scraper_choice}..."):
            if scraper_choice == "Tumblr":
                scraper = TumblrScraper(limit=limit)
            elif scraper_choice == "Google":
                scraper = GoogleScraper(limit=limit)
            elif scraper_choice == "Pinterest":
                scraper = PinterestScraper(limit=limit)
                
            urls = scraper.search(search_query)
            
            if urls:
                st.session_state.scraped_urls = urls
                st.success(f"Found {len(urls)} images.")
            else:
                st.error("No images found.")
                
    st.divider()
    
    st.subheader("Basket")
    st.caption(f"{len(st.session_state.basket)} images selected")
    
    # Basket Options
    zip_name = st.text_input("Zip Filename", "dataset")
    include_prompts = st.toggle("Include Prompt Text Files", value=True)
    
    if st.button("Clear Basket"):
        st.session_state.basket = set()
        st.rerun()

    if st.button("💾 Export Dataset"):
        if not st.session_state.basket:
            st.error("Basket is empty!")
        else:
            # Need to ensure all basket images are downloaded
            # (they might be selected but not downloaded if we only scraped URLs?)
            # Wait, user requirement: "DO NOT download files to disk initially; only store and display URLs."
            # "When 'Find Similar' is clicked, download that image..."
            # So images in gallery might NOT be downloaded yet.
            # But to Export, we need them.
            
            urls_to_download = [u for u in st.session_state.basket if u not in st.session_state.images_cache]
            if urls_to_download:
                import aiohttp
                asyncio.run(download_and_embed(list(st.session_state.basket)))
                
            # Prepare data
            images_map = {generate_filename(i, "img"): st.session_state.images_cache[u] for i, u in enumerate(st.session_state.basket) if u in st.session_state.images_cache}
            captions_map = {k: search_query for k in images_map.keys()} # Simple caption
            
            # Pass new options to create_dataset_zip
            zip_io = create_dataset_zip(images_map, captions_map, include_captions=include_prompts)
            
            # Ensure filename has .zip extension
            if not zip_name.endswith(".zip"):
                download_filename = f"{zip_name}.zip"
            else:
                download_filename = zip_name

            st.download_button(
                label="Download Zip",
                data=zip_io,
                file_name=download_filename,
                mime="application/zip"
            )

# --- Main Gallery ---
st.title("Dataset Curator")

if not st.session_state.scraped_urls:
    st.info("Start by scraping some images from the sidebar.")
else:
    # Action Bar
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Select All URLs"):
            st.session_state.basket.update(st.session_state.scraped_urls)
    with col2:
        if st.button("Analyze & Compute Embeddings (All)"):
            import aiohttp
            count = asyncio.run(download_and_embed(st.session_state.scraped_urls))
            st.session_state["analysis_done_count"] = count
            st.rerun()

    if "analysis_done_count" in st.session_state:
        count = st.session_state.pop("analysis_done_count")
        if count > 0:
            st.success(f"Successfully analyzed {count} new images!")
        else:
            st.info("Analysis complete. No new images needed analysis.")

    # Grid
    cols = st.columns(4)
    for i, url in enumerate(st.session_state.scraped_urls):
        col = cols[i % 4]
        with col:
            # Display image. If cached, use PIL, else use URL directly
            # Streamlit image can take URL
            
            is_selected = url in st.session_state.basket
            
            # Use container for layout
            with st.container(border=True):
                if url in st.session_state.images_cache:
                    st.image(st.session_state.images_cache[url], use_container_width=True)
                else:
                    st.image(url, use_container_width=True)
                
                # Controls
                c1, c2 = st.columns([1, 3])
                with c1:
                    # Basket toggle
                    if st.checkbox("Select", value=is_selected, key=f"sel_{i}"):
                        st.session_state.basket.add(url)
                    else:
                        st.session_state.basket.discard(url)
                
                with c2:
                    if st.button("🔍 Similar", key=f"sim_{i}"):
                        # Ensure this image is downloaded/embedded
                        if url not in st.session_state.embeddings:
                             import aiohttp
                             asyncio.run(download_and_embed([url]))
                             
                        if url in st.session_state.embeddings:
                            find_similar(url)
                            st.rerun()
                        else:
                            st.error("Failed to process image for similarity search.")

