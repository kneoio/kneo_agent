from cnst.play_list_item_type import PlaylistItemType
from mcp.external.internet_mcp import InternetMCP
from mcp.server.llm_response import LlmResponse
from tools.dj_state import DJState, MergingType
from tools.draft_builder import build_draft
from util.file_util import debug_log
from util.randomizer import get_random_merging_type


async def build_song_intro(self, state: DJState) -> DJState:
    for song in state["song_fragments"]:
        song.draft_intro = build_draft(
            title=song.title,
            artist=song.artist,
            ai_dj_name=self.ai_dj_name,
            brand=self.brand,
            song_description=song.description,
            genres=song.genres,
            history=state["history"],
            context=state["context"]
        )

    if len(state["song_fragments"]) == 1:
        state["merging_type"] = MergingType.INTRO_SONG
    else:
        state["merging_type"] = get_random_merging_type()

    debug_log(f"Merging chosen: {state['merging_type'].name}")
    return state

async def embellish(self, state: DJState) -> DJState:
        targets = []
        if state["merging_type"] == MergingType.INTRO_SONG and len(state["song_fragments"]) >= 1:
            targets = [state["song_fragments"][0]]
        elif state["merging_type"] == MergingType.SONG_INTRO_SONG and len(state["song_fragments"]) >= 2:
            targets = [state["song_fragments"][1]]
        elif state["merging_type"] == MergingType.INTRO_SONG_INTRO_SONG and len(state["song_fragments"]) >= 2:
            targets = [state["song_fragments"][0], state["song_fragments"][1]]

        for song in targets:
            draft = song.draft_intro or ""
            full_prompt = f"{self.agent_config['prompt']}\n\nInput:\n{draft}"

            prompt_messages = [
                {"role": "system", "content": "Generate plain text"},
                {"role": "user", "content": full_prompt}
            ]

            allow_search = (
                    song.type != PlaylistItemType.ADVERTISEMENT.value
                    and not song.genres
                    and not song.description
            )
            tools = [InternetMCP.get_tool_definition(default_engine=self.search_engine)] if allow_search else None

            response = await self.llm.ainvoke(messages=prompt_messages, tools=tools)
            try:
                llm_response = LlmResponse.parse_plain_response(response, self.llm_type)
                song.introduction_text = llm_response.actual_result
                debug_log(f"Embellished intro for {song.title}: {song.introduction_text}")
                self.ai_logger.info(
                    f"{self.brand} FINAL_RESULT: {llm_response.actual_result}, \nREASONING: {llm_response.reasoning}\n"
                )
            except Exception as e:
                self.logger.error(f"LLM Response parsing failed for {song.title}: {e}")
                song.introduction_text = draft

        return state