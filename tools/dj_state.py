from typing import Dict, Any, List, Optional
from langgraph.graph import MessagesState


class DJState(MessagesState):
    brand: str
    songs: List[Dict[str, Any]]
    selected_song: Dict[str, Any]
    introduction_text: str
    audio_data: Optional[bytes]
    reason: str
    title: str
    artist: str
