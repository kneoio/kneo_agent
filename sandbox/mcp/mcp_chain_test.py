import asyncio
import websockets
import json
import os
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END, MessagesState
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict
from dotenv import load_dotenv
import anthropic
from anthropic.types import MessageParam
import random

load_dotenv()
claude_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


class AgentState(MessagesState):
    selected_song: Dict[str, Any]


class MCPSongTool:
    def __init__(self, uri: str = None):
        self.uri = uri or os.getenv("MCP_SERVER_URI")
        if not self.uri:
            raise ValueError("MCP_SERVER_URI must be set in .env file")
        self.message_id = 1

    async def get_brand_sound_fragments(self, brand: str = "aizoo", page: int = 1, size: int = 50) -> Dict[str, Any]:
        async with websockets.connect(self.uri) as websocket:
            # Initialize
            init_message = {
                "jsonrpc": "2.0",
                "id": self.message_id,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "clientInfo": {"name": "LangGraph-MCP-Client", "version": "1.0.0"},
                    "capabilities": {}
                }
            }
            self.message_id += 1
            await websocket.send(json.dumps(init_message))
            await websocket.recv()

            # Get songs
            song_message = {
                "jsonrpc": "2.0",
                "id": self.message_id,
                "method": "tools/call",
                "params": {
                    "name": "get_brand_soundfragments",
                    "arguments": {"brand": brand, "page": page, "size": size}
                }
            }
            self.message_id += 1
            await websocket.send(json.dumps(song_message))
            response = await websocket.recv()

            result = json.loads(response)
            if "result" in result and "content" in result["result"]:
                content_text = result["result"]["content"][0]["text"]
                return json.loads(content_text)
            return {}


class MusicAgent:
    def __init__(self):
        self.mcp_tool = MCPSongTool()
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(state_schema=AgentState)

        workflow.add_node("fetch_and_select", self._fetch_and_select)
        workflow.add_node("get_artist_info", self._get_artist_info)

        workflow.set_entry_point("fetch_and_select")
        workflow.add_edge("fetch_and_select", "get_artist_info")
        workflow.add_edge("get_artist_info", END)

        return workflow.compile()

    async def _fetch_and_select(self, state: AgentState) -> AgentState:
        # Fetch songs
        data = await self.mcp_tool.get_brand_sound_fragments(brand="aizoo", page=1, size=50)
        songs = data.get("fragments", [])

        if not songs:
            state["selected_song"] = {}
            return state

        # Select random song
        selected = random.choice(songs)
        state["selected_song"] = selected

        return state

    async def _get_artist_info(self, state: AgentState) -> AgentState:
        selected = state["selected_song"]

        if not selected:
            state["messages"].append({
                "role": "assistant",
                "content": "No songs found in the catalog."
            })
            return state

        song = selected["soundfragment"]
        artist = song.get("artist", "Unknown")
        title = song.get("title", "Unknown")
        genre = song.get("genre", "Unknown")
        album = song.get("album", "Unknown")
        plays = selected.get("playedByBrandCount", 0)

        # Get artist info from Claude
        try:
            messages: list[MessageParam] = [
                MessageParam(role="user",
                             content=f"Tell me about the artist '{artist}'. Include their musical style, notable achievements, and background. Keep it concise but informative.")
            ]

            response = claude_client.messages.create(
                model="claude-3-opus-20240229",
                max_tokens=300,
                temperature=0.7,
                messages=messages
            )

            artist_info = response.content[0].text.strip()

            final_response = f"Selected Song: '{title}' by {artist}\n"
            final_response += f"Album: {album}\n"
            final_response += f"Genre: {genre}\n"
            final_response += f"Played: {plays} times\n\n"
            final_response += f"About {artist}:\n{artist_info}"

        except Exception as e:
            final_response = f"Selected Song: '{title}' by {artist}\n"
            final_response += f"Album: {album}\n"
            final_response += f"Genre: {genre}\n"
            final_response += f"Played: {plays} times\n\n"
            final_response += f"Could not fetch artist information: {e}"

        state["messages"].append({
            "role": "assistant",
            "content": final_response
        })

        return state

    async def run(self, query: str) -> str:
        initial_state = {
            "messages": [{"role": "user", "content": query}],
            "selected_song": {}
        }

        result = await self.graph.ainvoke(initial_state)
        last_message = result["messages"][-1]
        return last_message["content"] if isinstance(last_message, dict) else last_message.content


# Usage
async def main():
    agent = MusicAgent()
    response = await agent.run("Choose a song and tell me about the artist")
    print(response)


if __name__ == "__main__":
    asyncio.run(main())