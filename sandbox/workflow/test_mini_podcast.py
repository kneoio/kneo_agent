import asyncio
import os
from cnst.llm_types import LlmType
from core.config import load_config
from main import ApplicationManager
from mcp.external.internet_mcp import InternetMCP
from tools.dj_state import DJState, SoundFragment, MergingType
from tools.mini_podcast_builder import build_mini_podcast
from util.llm_factory import LlmFactory


class TestMiniPodcast:
    def __init__(self, llm):
        self.llm = llm
        #self.llm_type = LlmType.GROQ
        self.llm_type = LlmType.CLAUDE
        self.ai_dj_name = "Veenuo"
        self.brand = "lumisonic"
        prompt_path = os.path.join(os.path.dirname(__file__), "mini_podcast_prompt.md")
        prompt_text = open(prompt_path, "r", encoding="utf-8").read()
        self.agent_config = {
            "preferredLang": "en",
            "preferredVoice": "fzDFBB4mgvMlL36gPXcz",
            "secondaryVoice": "eVItLK1UvXctxuaRV2Oq",
            "secondaryVoiceName": "Samantha",
            "miniPodcastPrompt": prompt_text,
        }
        self.ai_logger = __import__("logging").getLogger("test")


async def main():
    config = load_config("config.yaml")
    llm_factory = LlmFactory(config)
    app_manager = ApplicationManager(config)
    internet_mcp = InternetMCP(app_manager.mcp_client)
    llm = llm_factory.get_llm_client(LlmType.GROQ, internet_mcp)

    dummy = TestMiniPodcast(llm)
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
