import logging
import asyncio
from cnst.llm_types import LlmType
from util.llm_factory import LlmFactory
from core.config import load_config

async def test_google_generation():
    print("Loading config.yaml…")
    config = load_config("config.yaml")
    print("Initializing Google client…")
    factory = LlmFactory(config)
    client = factory.get_llm_client(LlmType.GOOGLE)
    if not client:
        raise Exception("Failed to instantiate Google client")
    print("Successfully instantiated Google client")
    print(f"Client type: {type(client)}")
    try:
        print("Attempting real generation call…")
        response = await client.ainvoke("Hello, say 'Google integration works!'")
        print(f"Response: {response.content}")
    except Exception as e:
        print(f"Generation failed: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(test_google_generation())
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        exit(1)
