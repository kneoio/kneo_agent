import asyncio
from cnst.llm_types import LlmType
from core.config import load_config
from main import ApplicationManager
from mcp.external.internet_mcp import InternetMCP
from tools.dj_state import DJState, SoundFragment, MergingType
from tools.mini_podcast_builder import build_mini_podcast
from util.llm_factory import LlmFactory


class TestGrokMiniPodcast:
    def __init__(self, llm):
        self.llm = llm
        self.llm_type = LlmType.GROQ
        self.ai_dj_name = "Veenuo"
        self.brand = "lumisonic"
        self.agent_config = {
            "preferredLang": "en",
            "preferredVoice": "fzDFBB4mgvMlL36gPXcz",
            "secondaryVoice": "eVItLK1UvXctxuaRV2Oq",
            "secondaryVoiceName": "Samantha",
            "miniPodcastPrompt": (
                "Generate a short 2-person radio dialogue (3–5 lines) between two DJs.\n"
                "The main host is **{host_name}**, the co-host is **{guest_name}**.\n\n"
                "**Song:** {song_title} by {song_artist}.\n"
                "**Description:** {song_description}.\n"
                "**Style:** {style_desc}.\n\n"
                "Include optional expressive tags (e.g. [excited], [whispers], [laughs], [sighs]) "
                "to shape emotional delivery.\n\n"
                "Output strictly as a JSON array of objects like:\n"
                "[\n"
                "  {\"text\": \"[excited] Hi, this is {host_name} — welcome back!\", \"voice_id\": \"{voice_a}\"},\n"
                "  {\"text\": \"[warm] Thanks {host_name}, happy to join in.\", \"voice_id\": \"{voice_b}\"}\n"
                "]"
            ),
        }
        self.ai_logger = __import__("logging").getLogger("test")


async def main():
    config = load_config("config.yaml")
    llm_factory = LlmFactory(config)
    app_manager = ApplicationManager(config)
    internet_mcp = InternetMCP(app_manager.mcp_client)
    llm = llm_factory.get_llm_client(LlmType.GROQ, internet_mcp)

    dummy = TestGrokMiniPodcast(llm)
    state = DJState(
        messages=[],
        events=[],
        history=[],
        context=[],
        song_fragments=[
            SoundFragment(
                title="Neon Horizon",
                artist="Lumisonic",
                genres=["electronic"],
                description="Bright electro-pop groove.",
                id="test_id")
        ],
        broadcast_success=False,
        __end__=False,
        merging_type=MergingType.INTRO_SONG,
        session_id="test-session"
    )

    await build_mini_podcast(dummy, state)


if __name__ == "__main__":
    asyncio.run(main())
