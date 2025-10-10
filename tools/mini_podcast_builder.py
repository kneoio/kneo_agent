from mcp.server.llm_response import LlmResponse
from tools.dj_state import DJState
from util.file_util import debug_log

async def build_mini_podcast(self, state: DJState) -> DJState:
    song = state["song_fragments"][0]
    voice_a = self.agent_config.get("preferredVoice", "9BWtsMINqrJLrRacOk9x")
    voice_b = self.agent_config.get("secondaryVoice", "IKne3meq5aSn9XLyUdCD")

    lang = self.agent_config.get("preferredLang", "en")
    lang_data = self.agent_config.get("locale_data", {}).get(lang, {})

    host_name = lang_data.get("host_name", self.ai_dj_name or "DJ")
    guest_name = lang_data.get("guest_name", self.agent_config.get("secondaryVoiceName", "Music Expert"))
    style_desc = lang_data.get("style", "intelligent, immersive, modern electronic radio tone")
    prompt_template = lang_data.get("prompt") or self.agent_config.get("miniPodcastPrompt")

    try:
        prompt = prompt_template.format(
            host_name=host_name,
            guest_name=guest_name,
            song_title=song.title,
            song_artist=song.artist,
            song_description=song.description,
            style_desc=style_desc,
            voice_a=voice_a,
            voice_b=voice_b,
        )
    except Exception as e:
        debug_log(f"[ERROR] miniPodcastPrompt formatting failed: {e}")
        debug_log(
            f"Context → host={host_name}, guest={guest_name}, song={song.title}, artist={song.artist}, desc={song.description}, style={style_desc}")
        raise

    response = await self.llm.ainvoke(messages=[{"role": "user", "content": prompt}])
    llm_response = LlmResponse.parse_structured_response(response, self.llm_type)
    song.introduction_text = llm_response.actual_result

    self.ai_logger.info(
        f"{self.brand} FINAL_RESULT (PODCAST): {llm_response.actual_result}, \nREASONING: {llm_response.reasoning}\n"
    )
    debug_log(
        f"Built mini podcast intro for {song.title}: {song.introduction_text}, brand: {self.brand}, lang={lang}"
    )
    return state
