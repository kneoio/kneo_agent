import asyncio
import os
import logging
from core.config import load_config
from main import ApplicationManager
from mcp.external.internet_mcp import InternetMCP
from util.llm_factory import LlmFactory
from tools.message_dialogue_builder import build_message_dialogue
from models.sound_fragment import SoundFragment
from cnst.llm_types import LlmType

class TestMessageDialogue:
    def __init__(self):
        prompt_path = os.path.join(os.path.dirname(__file__), "message_prompt.md")
        prompt_text = open(prompt_path, "r", encoding="utf-8").read()
        self.agent_config = {
            "messagePrompt": prompt_text,
            "preferredVoice": "9BWtsMINqrJLrRacOk9x",
            "secondaryVoice": "IKne3meq5aSn9XLyUdCD",
            "secondaryVoiceName": "Samantha"
        }
        self.ai_dj_name = "DJ_host"
        self.llm = None
        self.brand = "test_brand"
        self.ai_logger = logging.getLogger("flow")
    def _reset_message(self, _):
        pass

async def main():
    config = load_config("config.yaml")
    llm_factory = LlmFactory(config)
    app_manager = ApplicationManager(config)
    internet_mcp = InternetMCP(app_manager.mcp_client)
    llm = llm_factory.get_llm_client(LlmType.GROQ, internet_mcp)

    s = TestMessageDialogue()
    s.llm = llm
    s.llm_type = LlmType.GROQ

    song = SoundFragment(id="test_id", title="Song", artist="Artist", genres=["electronic"], description="desc")
    state = {
        "messages": [{"from": "user", "content": "shout out to all"}],
        "song_fragments": [song]
    }
    await build_message_dialogue(s, state)
    #print(song.introduction_text)

if __name__ == "__main__":
    asyncio.run(main())
