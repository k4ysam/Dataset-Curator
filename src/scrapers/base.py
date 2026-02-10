from abc import ABC, abstractmethod
from typing import List, Optional

class BaseScraper(ABC):
    def __init__(self, limit: int = 50):
        self.limit = limit

    @abstractmethod
    def search(self, query: str) -> List[str]:
        """
        Search for images based on a query.
        Returns a list of image URLs.
        """
        pass
