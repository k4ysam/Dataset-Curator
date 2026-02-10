import io
import zipfile
from PIL import Image
from typing import List, Dict, Optional

def create_dataset_zip(images: Dict[str, Image.Image], captions: Dict[str, str], include_captions: bool = True) -> io.BytesIO:
    """
    Creates a ZIP file in memory containing images and their captions.
    images: {filename: PIL.Image}
    captions: {filename: caption_text}
    include_captions: If True, includes .txt files with captions.
    """
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
        for filename, img in images.items():
            # Save Image
            img_byte_arr = io.BytesIO()
            # Convert to RGB to avoid alpha channel issues with JPEG
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            
            img.save(img_byte_arr, format="JPEG", quality=95)
            zip_file.writestr(filename, img_byte_arr.getvalue())
            
            # Save Caption
            if include_captions:
                txt_filename = filename.rsplit(".", 1)[0] + ".txt"
                caption = captions.get(filename, "")
                zip_file.writestr(txt_filename, caption)
            
    zip_buffer.seek(0)
    return zip_buffer

def generate_filename(index: int, prefix: str = "image") -> str:
    return f"{prefix}_{index:05d}.jpg"
