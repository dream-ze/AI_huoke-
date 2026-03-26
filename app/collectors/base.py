from abc import ABC, abstractmethod
from typing import Tuple

from app.schemas.detail import CollectDetailRequest
from app.schemas.result import CollectStats, ContentItem


class BaseCollector(ABC):
    @abstractmethod
    def collect(self, keyword: str, max_items: int) -> Tuple[list[ContentItem], CollectStats, bool]:
        raise NotImplementedError

    @abstractmethod
    def fetch_detail(self, req: CollectDetailRequest) -> ContentItem:
        raise NotImplementedError
