from typing import List
from enum import Enum
from langgraph.graph import MessagesState
from models.sound_fragment import SoundFragment


class MergingType(Enum):
    INTRO_SONG = "INTRO_SONG"
    NOT_MIXED = "NOT_MIXED"
    SONG_INTRO_SONG = "SONG_INTRO_SONG"
    FILLER_SONG = "FILLER_SONG"
    INTRO_SONG_INTRO_SONG = "INTRO_SONG_INTRO_SONG"
    INTRO_FILLER_SONG = "INTRO_FILLER_SONG"
    OUTRO_SONG = "OUTRO_SONG"


class DJState(MessagesState):
    events: List[dict]
    messages: List[dict]
    history: List[dict]
    context: List[str]
    song_fragments: List[SoundFragment]

    broadcast_success: bool
    __end__: bool
    merging_type: MergingType
