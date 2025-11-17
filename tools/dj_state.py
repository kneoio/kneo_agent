from typing import List
from langgraph.graph import MessagesState
from models.sound_fragment import SoundFragment

class DJState(MessagesState):
    events: List[dict]
    messages: List[dict]
    history: List[dict]
    context: List[str]
    song_fragments: List[SoundFragment]
    brand: str
    intro_texts: List[str]
    audio_file_paths: List[str]
    song_ids: List[str]
    broadcast_success: bool
    dialogue_states: List[bool]
