#!/usr/bin/env python3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Profile:
    id: str
    name: str
    description: str
    allowedGenres: List[str]
    announcementFrequency: str
    explicitContent: bool
    language: Optional[str] = None
    author: str = "undefined"
    regDate: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lastModifier: str = "undefined"
    lastModifiedDate: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    archived: int = 0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Profile':
        return cls(
            id=data.get("id", ""),
            author=data.get("author", "undefined"),
            regDate=data.get("regDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            lastModifier=data.get("lastModifier", "undefined"),
            lastModifiedDate=data.get("lastModifiedDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            name=data.get("name", ""),
            description=data.get("description", ""),
            allowedGenres=data.get("allowedGenres", []),
            announcementFrequency=data.get("announcementFrequency", "MEDIUM"),
            explicitContent=data.get("explicitContent", False),
            language=data.get("language"),
            archived=data.get("archived", 0)
        )

    @property
    def profile(self):
        if hasattr(self, '_profile'):
            return self._profile
        from types import SimpleNamespace
        return SimpleNamespace(name="Standard", allowedGenres=[], explicitContent=False, announcementFrequency="MEDIUM")


@dataclass
class Brand:
    id: str
    country: str
    url: str
    actionUrl: str
    slugName: str
    profile: Profile
    status: str = "OFF_LINE"
    playlistCount: int = 0
    listenersCount: int = 0
    author: str = "undefined"
    regDate: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lastModifier: str = "undefined"
    lastModifiedDate: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    archived: int = 0

    # Runtime state not included in API model
    state: Dict[str, Any] = field(default_factory=lambda: {
        "current_song": None,
        "audience_info": {},
        "upcoming_events": [],
        "last_action": None,
        "feedback": []
    })

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Brand':
        profile_data = data.get("profile", {})
        profile = Profile.from_dict(profile_data) if profile_data else None

        return cls(
            id=data.get("id", ""),
            author=data.get("author", "undefined"),
            regDate=data.get("regDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            lastModifier=data.get("lastModifier", "undefined"),
            lastModifiedDate=data.get("lastModifiedDate", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            country=data.get("country", ""),
            url=data.get("url", ""),
            actionUrl=data.get("actionUrl", ""),
            slugName=data.get("slugName", ""),
            archived=data.get("archived", 0),
            playlistCount=data.get("playlistCount", 0),
            listenersCount=data.get("listenersCount", 0),
            status=data.get("status", "OFF_LINE"),
            profile=profile
        )

    def get_current_profile(self) -> str:
        return self.profile.name if self.profile else "generic"

    def get_api_identifier(self) -> str:
        return self.slugName

    def update_state(self, key: str, value: Any):
        self.state[key] = value

    def get_state(self) -> Dict[str, Any]:
        return self.state.copy()

    def get_state_value(self, key: str) -> Any:
        return self.state.get(key)


class BrandManager:

    def __init__(self):
        self.brands: Dict[str, Brand] = {}
        self.slug_to_id_map: Dict[str, str] = {}
        self.current_brand_id: Optional[str] = None

    def add_brand(self, brand_data: Dict[str, Any]) -> Brand:
        brand = Brand.from_dict(brand_data)
        self.brands[brand.id] = brand

        self.slug_to_id_map[brand.slugName] = brand.id

        if self.current_brand_id is None:
            self.current_brand_id = brand.id

        return brand

    def get_brand(self, brand_identifier: Optional[str] = None) -> Optional[Brand]:
        if not brand_identifier:
            target_id = self.current_brand_id
        elif brand_identifier in self.brands:
            target_id = brand_identifier
        elif brand_identifier in self.slug_to_id_map:
            target_id = self.slug_to_id_map[brand_identifier]
        else:
            return None

        if not target_id or target_id not in self.brands:
            return None

        return self.brands[target_id]

    def get_brand_by_slug(self, slug_name: str) -> Optional[Brand]:
        if slug_name in self.slug_to_id_map:
            return self.brands[self.slug_to_id_map[slug_name]]
        return None

    def set_current_brand(self, brand_identifier: str) -> bool:
        if brand_identifier in self.slug_to_id_map:
            self.current_brand_id = self.slug_to_id_map[brand_identifier]
            return True

        if brand_identifier in self.brands:
            self.current_brand_id = brand_identifier
            return True

        return False

    def get_current_brand_id(self) -> Optional[str]:
        return self.current_brand_id

    def get_current_brand_slug(self) -> Optional[str]:
        if not self.current_brand_id:
            return None
        brand = self.brands.get(self.current_brand_id)
        return brand.slugName if brand else None

    def get_all_brand_ids(self) -> List[str]:
        return list(self.brands.keys())

    def get_all_brand_slugs(self) -> List[str]:
        return list(self.slug_to_id_map.keys())

    @classmethod
    def from_api_response(cls, api_data: Dict[str, Any]) -> 'BrandManager':
        manager = cls()
        entries = api_data.get("payload", {}).get("viewData", {}).get("entries", [])

        for entry in entries:
            manager.add_brand(entry)

        return manager