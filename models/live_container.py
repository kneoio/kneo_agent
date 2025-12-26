#!/usr/bin/env python3
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TtsConfig:
    primaryVoice: str
    secondaryVoice: str
    secondaryVoiceName: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TtsConfig':
        return cls(
            primaryVoice=data.get("primaryVoice", ""),
            secondaryVoice=data.get("secondaryVoice", ""),
            secondaryVoiceName=data.get("secondaryVoiceName", "")
        )


@dataclass
class PromptItem:
    songId: str
    draft: str
    prompt: str
    promptType: Optional[str] = None
    llmType: Optional[str] = None
    searchEngineType: Optional[str] = None
    startTime: Optional[str] = None
    oneTimeRun: bool = False
    dialogue: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PromptItem':
        return cls(
            songId=data.get("songId", ""),
            draft=data.get("draft", ""),
            prompt=data.get("prompt", ""),
            promptType=data.get("promptType"),
            llmType=data.get("llmType"),
            searchEngineType=data.get("searchEngineType"),
            startTime=data.get("startTime"),
            oneTimeRun=bool(data.get("oneTimeRun", False)),
            dialogue=bool(data.get("podcast", False))
        )


@dataclass
class LiveRadioStation:
    name: str
    slugName: str
    radioStationStatus: str
    djName: str
    info: str
    tts: TtsConfig
    prompts: List[PromptItem] = field(default_factory=list)
    messagePrompt: Optional[str] = None
    miniPodcastPrompt: Optional[str] = None
    preferredLang: Optional[str] = None
    songsCount: int = 1
    llmType: Optional[str] = None
    searchEngineType: Optional[str] = None
    streamType: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LiveRadioStation':
        tts_data = data.get("tts")
        if tts_data is None:
            raise ValueError(f"Station {data.get('name', 'unknown')} has null tts config")
        prompts_list = [PromptItem.from_dict(p) for p in data.get("prompts", [])]
        songs_count = len(prompts_list) if prompts_list else 1
        
        llm_type = prompts_list[0].llmType if prompts_list else None
        search_engine = prompts_list[0].searchEngineType if prompts_list else None
        
        return cls(
            name=data.get("name"),
            slugName=data.get("slugName"),
            radioStationStatus=data.get("radioStationStatus"),
            djName=data.get("djName"),
            info=data.get("info", ""),
            tts=TtsConfig.from_dict(tts_data),
            prompts=prompts_list,
            messagePrompt=data.get("messagePrompt"),
            miniPodcastPrompt=data.get("miniPodcastPrompt"),
            preferredLang=data.get("preferredLang"),
            songsCount=songs_count,
            llmType=llm_type,
            searchEngineType=search_engine,
            streamType=data.get("streamType")
        )


@dataclass
class LiveContainer:
    radioStations: List[LiveRadioStation] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LiveContainer':
        stations_data = data.get("radioStations", [])
        stations = [LiveRadioStation.from_dict(station) for station in stations_data]
        
        return cls(radioStations=stations)

    def get_station_by_name(self, name: str) -> Optional[LiveRadioStation]:
        for station in self.radioStations:
            if station.name == name:
                return station
        return None

    def get_stations_by_status(self, status: str) -> List[LiveRadioStation]:
        return [station for station in self.radioStations if station.radioStationStatus == status]

    def get_all_station_names(self) -> List[str]:
        return [station.name for station in self.radioStations]

    def __len__(self) -> int:
        return len(self.radioStations)

    def __getitem__(self, index: int) -> LiveRadioStation:
        return self.radioStations[index]
