import asyncio
import os
import sys
from PIL import Image
import numpy as np

# Ensure src is in path
sys.path.append(os.getcwd())

from src.ai.processor import ImageProcessor
from src.utils.downloader import download_images_parallel
from src.utils.exporter import create_dataset_zip, generate_filename

def test_ai():
    print("\n--- Testing AI Model ---")
    try:
        processor = ImageProcessor()
        # Create a dummy image
        img = Image.new('RGB', (100, 100), color='red')
        emb = processor.encode_images([img])
        print(f"Embedding shape: {emb.shape}")
        assert emb.shape == (1, 512)
        print("AI Model: OK")
        return True
    except Exception as e:
        print(f"AI Model Failed: {e}")
        return False

async def test_downloader():
    print("\n--- Testing Downloader ---")
    url = "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png"
    results = await download_images_parallel([url])
    if url in results and isinstance(results[url], Image.Image):
        print(f"Downloaded image size: {results[url].size}")
        print("Downloader: OK")
        return results[url]
    else:
        print("Downloader Failed")
        return None

def test_exporter(img):
    print("\n--- Testing Exporter ---")
    try:
        images = {"test.jpg": img}
        captions = {"test.jpg": "a google logo"}
        zip_buffer = create_dataset_zip(images, captions)
        size = zip_buffer.getbuffer().nbytes
        print(f"Zip created, size: {size} bytes")
        assert size > 0
        print("Exporter: OK")
        return True
    except Exception as e:
        print(f"Exporter Failed: {e}")
        return False

if __name__ == "__main__":
    ai_ok = test_ai()
    img = asyncio.run(test_downloader())
    
    if img:
        exp_ok = test_exporter(img)
    else:
        exp_ok = False
        
    if ai_ok and img and exp_ok:
        print("\nBACKEND VERIFICATION PASSED")
    else:
        print("\nBACKEND VERIFICATION FAILED")
        sys.exit(1)
