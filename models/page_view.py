from dataclasses import dataclass
from typing import List, Optional, Generic, TypeVar


@dataclass
class SongItem:
    id: Optional[str]
    title: Optional[str]
    artist: Optional[str]
    labels_en: Optional[List[str]]


@dataclass
class BrandSongsResult:
    brand: str
    fragment_type: str
    total_count: int
    songs: List[SongItem]
    page: int
    page_size: int
    total_pages: int


T = TypeVar("T")


@dataclass
class Page(Generic[T]):
    items: List[T]
    total_count: int
    page: int
    page_size: int
    total_pages: int
