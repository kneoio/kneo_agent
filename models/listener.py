from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class Listener:
    id: str
    author: str
    regDate: str
    lastModifier: str
    lastModifiedDate: str
    localizedName: Dict[str, str]
    userId: int
    telegramName: str
    country: str
    nickName: Dict[str, str]
    slugName: str
    archived: int
    listenerOf: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Listener':
        return cls(
            id=data.get("id"),
            author=data.get("author"),
            regDate=data.get("regDate"),
            lastModifier=data.get("lastModifier"),
            lastModifiedDate=data.get("lastModifiedDate"),
            localizedName=data.get("localizedName", {}),
            userId=data.get("userId"),
            telegramName=data.get("telegramName"),
            country=data.get("country"),
            nickName=data.get("nickName", {}),
            slugName=data.get("slugName"),
            archived=data.get("archived", 0),
            listenerOf=data.get("listenerOf", [])
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "author": self.author,
            "regDate": self.regDate,
            "lastModifier": self.lastModifier,
            "lastModifiedDate": self.lastModifiedDate,
            "localizedName": self.localizedName,
            "userId": self.userId,
            "telegramName": self.telegramName,
            "country": self.country,
            "nickName": self.nickName,
            "slugName": self.slugName,
            "archived": self.archived,
            "listenerOf": self.listenerOf
        }
