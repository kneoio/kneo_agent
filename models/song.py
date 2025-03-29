#!/usr/bin/env python3
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class SoundFragment:
    id: str
    title: str
    artist: str
    genre: str
    album: str
    type: str = "SONG"
    source: str = "DIGITALOCEAN"
    status: int = 1
    author: str = "undefined"
    regDate: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lastModifier: str = "undefined"
    lastModifiedDate: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SoundFragment':
        return cls(
            id=data.get("id", ""),
            author=data.get("author", "undefined"),
            regDate=data.get("regDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            lastModifier=data.get("lastModifier", "undefined"),
            lastModifiedDate=data.get("lastModifiedDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            source=data.get("source", "DIGITALOCEAN"),
            status=data.get("status", 1),
            type=data.get("type", "SONG"),
            title=data.get("title", ""),
            artist=data.get("artist", ""),
            genre=data.get("genre", ""),
            album=data.get("album", "")
        )


@dataclass
class Song:
    id: str
    soundFragmentDTO: SoundFragment
    playedByBrandCount: int = 0
    lastTimePlayedByBrand: Optional[str] = None
    explicit: bool = False

    @property
    def title(self) -> str:
        return self.soundFragmentDTO.title

    @property
    def artist(self) -> str:
        return self.soundFragmentDTO.artist

    @property
    def genre(self) -> str:
        return self.soundFragmentDTO.genre

    @property
    def album(self) -> str:
        return self.soundFragmentDTO.album

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "genre": self.genre,
            "album": self.album,
            "explicit": self.explicit,
            "playedByBrandCount": self.playedByBrandCount,
            "lastTimePlayedByBrand": self.lastTimePlayedByBrand
        }

    def get(self, key, default=None):
        if key == "id":
            return self.id
        elif key == "title":
            return self.title
        elif key == "artist":
            return self.artist
        elif key == "genre":
            return self.genre
        elif key == "album":
            return self.album
        elif key == "explicit":
            return self.explicit
        elif key == "playedByBrandCount":
            return self.playedByBrandCount
        elif key == "lastTimePlayedByBrand":
            return self.lastTimePlayedByBrand
        return default

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Song':
        sound_fragment_data = data.get("soundFragmentDTO", {})
        sound_fragment = SoundFragment.from_dict(sound_fragment_data)

        return cls(
            id=data.get("id", ""),
            soundFragmentDTO=sound_fragment,
            playedByBrandCount=data.get("playedByBrandCount", 0),
            lastTimePlayedByBrand=data.get("lastTimePlayedByBrand"),
            explicit=data.get("explicit", False)
        )