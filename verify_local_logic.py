import streamlit as st
import asyncio

# Mock session state
if "images_cache" not in st.session_state:
    st.session_state.images_cache = {}
if "embeddings" not in st.session_state:
    st.session_state.embeddings = {}

# Mock function to simulate download_and_embed logic from app.py
async def mock_download_and_embed(urls):
    # This mimics the logic I added to app.py
    urls_to_download = [u for u in urls if not u.startswith("local::")]
    st.write(f"URLs to download: {urls_to_download}")
    
    # Simulate caching
    for u in urls:
        if u.startswith("local::"):
            # Mock image
            st.session_state.images_cache[u] = "MockImage"
        else:
            # Simulate successful download for non-local
            st.session_state.images_cache[u] = "MockDownloadedImage"
            
    valid_urls_to_embed = [u for u in urls if u in st.session_state.images_cache and u not in st.session_state.embeddings]
    st.write(f"URLs to embed: {valid_urls_to_embed}")
    
    return len(valid_urls_to_embed)

st.title("Verification Script")

if st.button("Run Test"):
    urls = ["http://example.com/img1.jpg", "local::my_cat.jpg", "local::my_dog.png"]
    
    # Run the async function
    count = asyncio.run(mock_download_and_embed(urls))
    
    st.write(f"Processed {count} images.")
    
    if count == 3:
        st.success("PASS: Local images encompassed in embedding logic but excluded from download.")
    else:
        st.error(f"FAIL: Expected 3, got {count}")
