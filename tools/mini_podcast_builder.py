import random

from mcp.server.llm_response import LlmResponse
from tools.dj_state import DJState
from util.file_util import debug_log


async def build_mini_podcast(self, state: DJState) -> DJState:
    song = state["song_fragments"][0]
    voice_a = self.agent_config.get("preferredVoice", "9BWtsMINqrJLrRacOk9x")
    voice_b = self.agent_config.get("secondaryVoice", "IKne3meq5aSn9XLyUdCD")
    host_name = self.ai_dj_name or "DJ"
    guest_name = self.agent_config.get("secondaryVoiceName", "Music Expert")

    mention_guest = random.choice([True, False])

    if mention_guest:
        guest_intro = (
            f"{host_name} should introduce {guest_name} as an expert or invited guest "
            f"(e.g. 'Now we have {guest_name} joining us to dive into this track'). "
        )
    else:
        guest_intro = (
            f"Do not mention {guest_name}'s name directly — make the conversation flow naturally "
            f"as if between two familiar co-hosts. "
        )

    prompt = (
        f"Generate a short 2-person radio dialogue (3–5 lines) between two DJs.\n"
        f"The main host is {host_name}, the co-host is {guest_name}.\n"
        f"{guest_intro}"
        f"Song: {song.title} by {song.artist}.\n"
        f"Description: {song.description}.\n"
        f"Style: intelligent, immersive, modern electronic radio tone.\n"
        f"Include optional expressive tags (e.g. [excited], [whispers], [laughs], [sighs]) "
        f"to shape emotional delivery.\n"
        f"Output strictly as a JSON array of objects like:\n"
        f'  [{{"text": "[excited] Hi, this is {host_name} — welcome back!", "voice_id": "{voice_a}"}},\n'
        f'   {{"text": "[warm] Thanks {host_name}, happy to join in.", "voice_id": "{voice_b}"}}].'
    )

    response = await self.llm.ainvoke(messages=[{"role": "user", "content": prompt}])
    llm_response = LlmResponse.parse_structured_response(response, self.llm_type)
    song.introduction_text = llm_response.actual_result
    self.ai_logger.info(
        f"{self.brand} FINAL_RESULT (DIALOG): {llm_response.actual_result}, \nREASONING: {llm_response.reasoning}\n"
    )
    debug_log(
        f"Built dialogue intro for {song.title}: {song.introduction_text}, brand: {self.brand} "
        f"(guest_mentioned={mention_guest})"
    )
    return state