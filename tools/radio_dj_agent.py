import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple

from langgraph.graph import MessagesState
from langgraph.graph import StateGraph, END

from api.interaction_memory import InteractionMemory
from api.queue import Queue
from cnst.play_list_item_type import PlaylistItemType
from mcp.memory_mcp import MemoryMCP
from mcp.sound_fragment_mcp import SoundFragmentMCP
from util.file_util import debug_log
from util.intro_helper import get_random_ad_intro


class DJState(MessagesState):
    events: List[Dict[str, Any]]
    history: List[Dict[str, Any]]
    action_type: str
    mood: str
    context: str
    available_ads: List[Dict[str, Any]]
    selected_sound_fragment: Dict[str, Any]
    introduction_text: str
    audio_data: Optional[bytes]
    reason: str
    title: str
    artist: str
    listeners: List[Dict[str, Any]]
    http_memory_data: Dict[str, Any]  # Add this to store HTTP response


def _route_action(state: DJState) -> str:
    return state["action_type"]


def _route_song_fetch(state: DJState) -> str:
    if not state["selected_sound_fragment"]:
        return "end"
    return "create_audio"


class RadioDJAgent:

    def __init__(self, config, memory: InteractionMemory, audioProcessor, agent_config=None, brand=None,
                 mcp_client=None,
                 debug=False, llmClient=None):
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(handler)

        self.llm = llmClient

        self.queue = Queue(config)
        self.memory = memory
        self.audio_processor = audioProcessor
        self.agent_config = agent_config or {}
        self.ai_dj_name = self.agent_config.get("name")
        self.brand = brand
        self.sound_fragments_mcp = SoundFragmentMCP(mcp_client)
        self.memory_mcp = MemoryMCP(mcp_client)
        self.graph = self._build_graph()
        debug_log("RadioDJAgent initialized")

    def _build_graph(self):
        workflow = StateGraph(state_schema=DJState)
        workflow.add_node("check_events", self._check_events)
        workflow.add_node("decision", self._decision)
        workflow.add_node("fetch_song", self._fetch_song)
        workflow.add_node("create_audio", self._create_audio)

        workflow.set_entry_point("check_events")

        workflow.add_edge("check_events", "decision")

        workflow.add_conditional_edges(
            "decision",
            _route_action,
            {
                "song": "fetch_song",
                "ad": "create_audio"
            }
        )

        workflow.add_conditional_edges(
            "fetch_song",
            _route_song_fetch,
            {
                "create_audio": "create_audio",
                "end": END
            }
        )

        workflow.add_edge("create_audio", END)

        debug_log("Graph workflow built")
        return workflow.compile()

    async def _check_events(self, state: DJState) -> DJState:
        debug_log("Entering _check_events")

        try:
            # Use HTTP memory data instead of MCP call
            http_memory_data = state.get("http_memory_data", {})
            events = http_memory_data.get("EVENT", [])

            state["events"] = events
            state["reason"] = f"Found {len(events)} events to process"
            debug_log("Events retrieved from HTTP data", {"count": len(events), "events": events})
        except Exception as e:
            self.logger.error(f"Error checking events: {e}", exc_info=self.debug)
            state["events"] = []
            state["reason"] = f"Error checking events: {str(e)}"

        return state

    async def _decision(self, state: DJState) -> DJState:
        debug_log("Entering _decision")

        ads = await self.sound_fragments_mcp.get_by_type(self.brand, types=PlaylistItemType.ADVERTISEMENT.value)
        state["available_ads"] = [ad.get("id") for ad in ads]  # Extract only IDs
        debug_log(f"Ads fetched: {len(ads)} available")
        memory_data = self.memory.get_all_memory_data()
        state["context"] = memory_data.get("environment")[0]
        decision_prompt = self.agent_config["decision_prompt"].format(
            ai_dj_name=self.ai_dj_name,
            context=state["context"],
            brand=self.brand,
            events=state["events"],
            ads=state["available_ads"]
        )

        try:
            messages = [
                {"role": "system",
                 "content": "Output JSON only: - Ad: {\"action\": \"ad\", \"selected_song_uuid\": \"ad-uuid\"} - Song: {\"action\": \"song\", \"mood\": \"determined-mood\"}"},
                {"role": "user", "content": decision_prompt}
            ]
            response = await self.llm.ainvoke(messages)
            debug_log(f"LLM response received: {response.content[:200]}...")
            parsed_response = self._parse_llm_response(response.content)

            state["action_type"] = parsed_response.get("action", "song")
            debug_log("Action type determined", {"action_type": state["action_type"]})

            if state["action_type"] == "ad":
                state["introduction_text"] = parsed_response.get("introduction_text", get_random_ad_intro())
                selected_uuid = parsed_response.get("selected_song_uuid", "")
                selected_ad = {}
                for item in ads:
                    if item.get('id') == selected_uuid:
                        selected_ad = item
                state["selected_sound_fragment"] = selected_ad
                debug_log(f"Selected ad: {selected_ad}")
                ad_info = selected_ad.get('soundfragment', {})
                debug_log(f"Ad sound fragment: {ad_info}")
                state["title"] = ad_info.get('title', 'Advertisement')
                state["artist"] = ad_info.get('artist', 'Sponsor')
            else:
                # Use HTTP memory data instead of MCP calls
                http_memory_data = state.get("http_memory_data", {})
                state["history"] = http_memory_data.get("CONVERSATION_HISTORY", [])
                state["listeners"] = http_memory_data.get("LISTENER_CONTEXT", [])

                debug_log(f"Retrieved conversation history from HTTP: {len(state['history'])} items")
                debug_log(f"Retrieved listeners from HTTP: {len(state['listeners'])} items")

                state["mood"] = parsed_response.get("mood", "upbeat")
                debug_log(f"Song mood determined: {state['mood']}")

            state["reason"] = f"Decision made: {state['action_type']}"

        except Exception as e:
            self.logger.error(f"Decision failed: {e}", exc_info=self.debug)
            state["action_type"] = "song"
            state["mood"] = "upbeat"
            state["reason"] = f"Decision failed: {str(e)}"
            self.logger.warning(f"Fallback to default: action=song, mood=upbeat")

        return state

    async def _fetch_song(self, state: DJState) -> DJState:
        debug_log("Entering _fetch_song")

        try:
            song = await self.sound_fragments_mcp.get_song_by_mood(self.brand, state["mood"])
            if song:
                state["selected_sound_fragment"] = song
                song_info = song.get('soundfragment', {})
                state["title"] = song_info.get('title')
                state["artist"] = song_info.get('artist')

                debug_log("state['title']", state["title"])
                debug_log("state['artist']", state["artist"])
                debug_log("self.ai_dj_name", self.ai_dj_name)
                debug_log("state['context']", state["context"])
                debug_log("state['events']", state["events"])
                debug_log("state['history']", state["history"])
                debug_log("state['listeners']", state["listeners"])

                song_prompt = self.agent_config["prompt"].format(
                    ai_dj_name=self.ai_dj_name,
                    context=state["context"],
                    brand=self.brand,
                    events=state["events"],
                    title=state["title"],
                    artist=state["artist"],
                    mood=state["mood"],
                    history=state["history"],
                    listeners=state["listeners"],
                )

                messages = [
                    {"role": "system",
                     "content": "Generate plain text"},
                    {"role": "user", "content": song_prompt}
                ]
                response = await self.llm.ainvoke(messages)
                state["introduction_text"] = response.content.strip()
                debug_log(f"Result: >>>> : {state['introduction_text']}...")
                state["reason"] = f"Song fetched and intro generated for mood: {state['mood']}"
            else:
                debug_log("No song to broadcast.")
                state["selected_sound_fragment"] = {}
                state["introduction_text"] = ""
                state["reason"] = f"No song found for mood: {state['mood']}"

        except Exception as e:
            self.logger.error(f"Error in fetch_song: {e}")
            state["selected_sound_fragment"] = {}
            state["introduction_text"] = ""
            state["reason"] = f"Error in fetch_song: {str(e)}"

        return state

    def _parse_llm_response(self, response: str) -> Dict[str, str]:
        try:
            json_match = re.search(r'\{[^}]*\}', response)
            if json_match:
                return json.loads(json_match.group(0))
            else:
                self.logger.error(f"Parsing LLM response issue: {response}")
                return {}
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {e}")
            return {}

    async def _create_audio(self, state: DJState) -> DJState:
        debug_log("Entering _create_audio")

        try:
            audio_data, reason = await self.audio_processor.generate_tts_audio(
                state["introduction_text"],
                state["title"],
                state["artist"]
            )

            state["audio_data"] = audio_data
            state["reason"] = reason

        except Exception as e:
            self.logger.error(f"Error creating audio: {e}", exc_info=self.debug)
            state["reason"] = f"Error creating audio: {str(e)}"

        return state

    async def create_introduction(self, brand: str, http_memory_data: Dict[str, Any] = None) -> Tuple[
        Optional[bytes], str, str, str]:
        self._reset_memory()

        initial_state = {
            "messages": [],
            "brand": brand,
            "events": [],
            "action_type": "",
            "mood": "",
            "available_ads": [],
            "selected_sound_fragment": {},
            "introduction_text": "",
            "audio_data": None,
            "reason": "",
            "title": "Unknown",
            "artist": "Unknown",
            "listeners": [],
            "history": [],
            "http_memory_data": http_memory_data or {}  # Pass HTTP data to state
        }

        try:
            result = await self.graph.ainvoke(initial_state)
            return (
                result["audio_data"],
                result["selected_sound_fragment"].get("id"),
                result["title"],
                result["artist"]
            )
        except Exception as e:
            reason = f"Workflow execution failed: {str(e)}"
            self.logger.error(reason, exc_info=self.debug)
            return None, reason, "Unknown", "Unknown"

    def _reset_memory(self):
        memory_data = self.memory.get_all_memory_data()
        if memory_data.get('messages'):
            self.memory.reset_messages()
        events = memory_data.get('events', [])
        event_ids = memory_data.get('event_ids', [])

    def enable_debug(self):
        self.logger.setLevel(logging.DEBUG)

    def disable_debug(self):
        self.logger.setLevel(logging.INFO)