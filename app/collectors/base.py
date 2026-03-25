from abc import ABC, abstractmethod
from typing import List
from app.schemas.result import ContentItem


class BaseCollector(ABC):
    @abstractmethod
    def collect(self, keyword: str, max_items: int) -> List[ContentItem]:
        raise NotImplementedError
