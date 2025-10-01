#!/usr/bin/env python3
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class SoundFragment:
    id: str
    title: str
    artist: str
    genres: List[str] = field(default_factory=list)
    album: Optional[str] = None
    description: Optional[str] = None
    type: str = "SONG"
    source: Optional[str] = None
    status: int = 1
    author: Optional[str] = None
    regDate: Optional[str] = None
    lastModifier: Optional[str] = None
    lastModifiedDate: Optional[str] = None

    # runtime-only (not persisted)
    draft_intro: Optional[str] = None
    introduction_text: Optional[str] = None
    audio_data: Optional[bytes] = None
    file_path: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SoundFragment':
        return cls(
            id=data.get("id"),
            author=data.get("author"),
            regDate=data.get("regDate"),
            lastModifier=data.get("lastModifier"),
            lastModifiedDate=data.get("lastModifiedDate"),
            source=data.get("source"),
            status=data.get("status", 1),
            type=data.get("type"),
            title=data.get("title"),
            artist=data.get("artist"),
            genres=data.get("genres", []),
            album=data.get("album"),
            description=data.get("description"),
        )
