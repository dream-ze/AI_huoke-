from abc import ABC, abstractmethod
from typing import Tuple

from app.schemas.detail import CollectDetailRequest
from app.schemas.request import CollectRequest
from app.schemas.result import CollectStats, ContentItem


class BaseCollector(ABC):
    @abstractmethod
    def collect(self, req: CollectRequest) -> Tuple[list[ContentItem], CollectStats]:
        raise NotImplementedError

    @abstractmethod
    def fetch_detail(self, req: CollectDetailRequest) -> ContentItem:
        raise NotImplementedError
