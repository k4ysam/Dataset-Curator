import torch
from sentence_transformers import SentenceTransformer
from PIL import Image
from typing import List, Union
import numpy as np

class ImageProcessor:
    def __init__(self, model_name: str = "sentence-transformers/clip-ViT-B-32"):
        # Load model. Streamlit will cache the instance if we wrapper it right, 
        # but here we just define the class.
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        print(f"Loading AI model on {self.device}...")
        self.model = SentenceTransformer(model_name, device=self.device)
        print("Model loaded.")

    def encode_images(self, images: List[Image.Image]) -> np.ndarray:
        """
        Compute embeddings for a list of PIL Images.
        """
        # sentence-transformers handles batching automatically usually, but let's be safe
        embeddings = self.model.encode(images, batch_size=32, convert_to_numpy=True)
        return embeddings

    def encode_text(self, text: str) -> np.ndarray:
        """
        Compute embedding for a text query.
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
        
    def calculate_similarity(self, source_embedding: np.ndarray, candidate_embeddings: np.ndarray) -> np.ndarray:
        """
        Calculate cosine similarity between one source embedding and many candidates.
        """
        # Cosine similarity: (A . B) / (||A|| * ||B||)
        # SentenceTransformers embeddings are typically normalized? 
        # Let's verify or just normalize manually.
        
        # Normalize source
        norm_source = np.linalg.norm(source_embedding)
        if norm_source > 0:
            source_embedding = source_embedding / norm_source
            
        # Normalize candidates
        norm_candidates = np.linalg.norm(candidate_embeddings, axis=1, keepdims=True)
        # Avoid division by zero
        norm_candidates[norm_candidates == 0] = 1
        candidate_embeddings = candidate_embeddings / norm_candidates
        
        # Dot product
        similarities = np.dot(candidate_embeddings, source_embedding)
        return similarities
