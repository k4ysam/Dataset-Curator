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
    # Filter out local images from download list, they are already in cache if present
    # Local images have "local::" prefix
    urls_to_download = [u for u in urls if not u.startswith("local::")]
    
    missing_urls = [u for u in urls_to_download if u not in st.session_state.images_cache]
    
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
    
    # Compute embeddings for new images (local or downloaded)
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

    return newly_embedded

def find_similar(target_url, source_list=None):
    """
    Re-ranks lists based on similarity to target_url.
    If source_list is provided, only ranks images in that list.
    Returns the sorted list.
    """
    if target_url not in st.session_state.embeddings:
        st.warning("Embedding not found for this image.")
        return []

    target_emb = st.session_state.embeddings[target_url]
    
    # Calculate similarity with ALL other known embeddings
    # Optimally, we should only compare against source_list if provided, but for now filtering after is fine or we can slice embeddings.
    # To keep it simple and correct:
    
    if source_list is None:
        source_list = list(st.session_state.embeddings.keys())
        
    # Filter source_list to only those that have embeddings
    valid_source = [u for u in source_list if u in st.session_state.embeddings]
    
    if not valid_source:
        st.warning("No images to compare against.")
        return []

    embs = np.array([st.session_state.embeddings[u] for u in valid_source])
    
    sims = processor.calculate_similarity(target_emb, embs)
    
    # Sort urls by similarity
    # zip, sort, unzip
    sorted_pairs = sorted(zip(valid_source, sims), key=lambda x: x[1], reverse=True)
    # Return pairs (url, score)
    return sorted_pairs

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

# Tabs for Mode Selection
tab_scraper, tab_local = st.tabs(["Web Scraper", "Local Import"])

# --- TAB 1: Web Scraper ---
with tab_scraper:
    if not st.session_state.scraped_urls:
        st.info("Start by scraping some images from the sidebar.")
    else:
        # Action Bar
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Select All Scraped URLs"):
                st.session_state.basket.update(st.session_state.scraped_urls)
                st.rerun()
        with col2:
             # Placeholder for alignment if needed, or just remove col2
             pass

        if "analysis_done_count" in st.session_state:
            count = st.session_state.pop("analysis_done_count")
            if count > 0:
                st.success(f"Successfully analyzed {count} new images!")
            else:
                st.info("Analysis complete. No new images needed analysis.")

        # Grid for Scraped Images
        cols = st.columns(4)
        for i, url in enumerate(st.session_state.scraped_urls):
            col = cols[i % 4]
            with col:
                is_selected = url in st.session_state.basket
                
                with st.container(border=True):
                    if url in st.session_state.images_cache:
                        st.image(st.session_state.images_cache[url], use_container_width=True)
                    else:
                        st.image(url, use_container_width=True)
                    
                    # Controls
                    # Just Selection, no Similar button as requested
                    if st.checkbox("Select", label_visibility="collapsed", value=is_selected, key=f"sel_{i}"):
                        st.session_state.basket.add(url)
                    else:
                        st.session_state.basket.discard(url)

# --- TAB 2: Local Import ---
if "local_images" not in st.session_state:
    st.session_state.local_images = [] # List of unique IDs (local::{filename}::{uuid})
if "local_sim_scores" not in st.session_state:
    st.session_state.local_sim_scores = {} # uid -> score
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0

with tab_local:
    # File Uploader handles both images and zip
    # Use key to allow resetting
    uploaded_files = st.file_uploader(
        "Choose images or zip files from your computer", 
        accept_multiple_files=True, 
        type=['png', 'jpg', 'jpeg', 'webp', 'zip'],
        key=f"uploader_{st.session_state.uploader_key}"
    )
    
    if uploaded_files:
        import zipfile
        import uuid
        
        new_files_count = 0
        for uploaded_file in uploaded_files:
            # Check file type
            if uploaded_file.name.lower().endswith(".zip"):
                 # Handle Zip
                 try:
                     with zipfile.ZipFile(uploaded_file) as z:
                         for filename in z.namelist():
                             # Simple filter for images
                             if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                                 with z.open(filename) as f:
                                     # Load image bytes
                                     img_bytes = f.read()
                                     image = Image.open(io.BytesIO(img_bytes))
                                     
                                     # Unique ID to allow duplicate filenames from diff folders
                                     # Use prefix local::{filename}::{uuid}
                                     unique_start = f"local::{filename}::{uuid.uuid4()}"
                                     
                                     st.session_state.images_cache[unique_start] = image
                                     st.session_state.local_images.append(unique_start)
                                     new_files_count += 1
                 except Exception as e:
                     st.error(f"Error processing zip {uploaded_file.name}: {e}")
            else:
                # Handle Image
                # Unique ID
                file_id = f"local::{uploaded_file.name}::{uuid.uuid4()}"
                
                try:
                    image = Image.open(uploaded_file)
                    st.session_state.images_cache[file_id] = image
                    st.session_state.local_images.append(file_id)
                    new_files_count += 1
                except Exception as e:
                    st.error(f"Error loading {uploaded_file.name}: {e}")
        
        if new_files_count > 0:
            st.success(f"Imported {new_files_count} images.")
            # Reset uploader for addictive workflow
            st.session_state.uploader_key += 1
            st.rerun()
    
    # Clear Button
    if st.button("Clear Local Images"):
        # Remove local images from cache to free memory? Or just clear list?
        # Better to clear cache too for local items
        for uid in st.session_state.local_images:
            if uid in st.session_state.images_cache:
                del st.session_state.images_cache[uid]
            if uid in st.session_state.embeddings:
                del st.session_state.embeddings[uid]
                
        st.session_state.local_images = []
        st.session_state.local_sim_scores = {}
        st.rerun()

    if st.session_state.local_images:
        st.caption(f"Imported {len(st.session_state.local_images)} images.")
        
        # Action Bar for Local
        l_col1, l_col2 = st.columns([1, 1])
        with l_col1:
             if st.button("Select All Local Images"):
                st.session_state.basket.update(st.session_state.local_images)
                st.rerun()
        with l_col2:
             # Removed Analyze button
             pass

        # Grid for Local Images
        l_cols = st.columns(4)
        for i, uid in enumerate(st.session_state.local_images):
            col = l_cols[i % 4]
            with col:
                is_selected = uid in st.session_state.basket
                
                with st.container(border=True):
                    # Caption: filename + score if available
                    # Format: local::{filename}::{uuid}
                    parts = uid.split("::")
                    # parts[0] is 'local', parts[1] is filename, parts[2] is uuid
                    if len(parts) >= 2:
                        caption_text = parts[1]
                    else:
                        caption_text = uid # Fallback

                    if uid in st.session_state.local_sim_scores:
                        score = st.session_state.local_sim_scores[uid]
                        caption_text += f"\nSim: {score:.4f}"
                    
                    # Show image from cache
                    st.image(st.session_state.images_cache[uid], use_container_width=True, caption=caption_text)
                    
                    # Controls
                    lc1, lc2 = st.columns([1, 3])
                    with lc1:
                        if st.checkbox("Select", label_visibility="collapsed", value=is_selected, key=f"l_sel_{i}"):
                            st.session_state.basket.add(uid)
                        else:
                            st.session_state.basket.discard(uid)
                    
                    with lc2:
                        if st.button("🔍 Similar", key=f"l_sim_{i}"):
                            # 1. Ensure ALL local images are embedded first to prevent "vanishing"
                            # This is fast for local images (no network)
                            import aiohttp
                            asyncio.run(download_and_embed(st.session_state.local_images))
                                 
                            if uid in st.session_state.embeddings:
                                sorted_pairs = find_similar(uid, st.session_state.local_images)
                                if sorted_pairs:
                                    # Update listing order
                                    st.session_state.local_images = [u for u, s in sorted_pairs]
                                    # Store scores for display
                                    st.session_state.local_sim_scores = {u: s for u, s in sorted_pairs}
                                    st.rerun()
                            else:
                                st.error("Failed to process image.")

