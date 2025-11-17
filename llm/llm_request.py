from typing import Any
import logging

from cnst.llm_types import LlmType
from cnst.search_engine import SearchEngine
from llm.llm_response import LlmResponse
from mcp.external.internet_mcp import InternetMCP

logger = logging.getLogger(__name__)


async def invoke_intro(llm_client: Any, prompt: str, draft: str, on_air_memory: str) -> 'LlmResponse':
    full_prompt = f"{prompt}\n\nInput:\n{draft}\n\nOn-air memory:\n{on_air_memory}"
    
    tools = None
    if hasattr(llm_client, 'tool_functions') and llm_client.tool_functions:
        internet_tool = SearchEngine.Perplexity.value
        tools = [InternetMCP.get_tool_definition(default_engine=internet_tool)]
        logger.info(f'invoke_intro: Internet tools "{internet_tool}" enabled for {llm_client.llm_type.name}')
    else:
        logger.debug(f"invoke_intro: No internet tools available for {llm_client.llm_type.name}")
    
    response = await llm_client.invoke(
        messages=[
            {"role": "system", "content": "You are a professional radio DJ"},
            {"role": "user", "content": full_prompt}
        ],
        tools=tools
    )
    return LlmResponse.parse_plain_response(response, llm_client.llm_type)


async def invoke_chat(llm_client: Any, messages: list, llm_type: LlmType) -> 'LlmResponse':
    tools = None
    if hasattr(llm_client, 'tool_functions') and llm_client.tool_functions:
        internet_tool = SearchEngine.Perplexity.value
        tools = [InternetMCP.get_tool_definition(default_engine=internet_tool)]
        logger.info(f'invoke_chat: Internet tools "{internet_tool}" enabled for {llm_type.name}')
    else:
        logger.debug(f"invoke_chat: No internet tools available for {llm_type.name}")

    response = await llm_client.invoke(
        messages=messages,
        tools=tools
    )
    return LlmResponse.parse_plain_response(response, llm_type)


async def translate_prompt(llm_client: Any, prompt: str, to_translate: str) -> 'LlmResponse':
    full_prompt = f"{prompt}\n\nInput:\n{to_translate}"
    response = await llm_client.invoke(messages=[
        {"role": "system", "content": "You are a professional translator."},
        {"role": "user", "content": full_prompt}
    ])
    print(f"RAW: {response}")
    return LlmResponse.parse_plain_response(response, llm_client.llm_type)

async def translate_content(llm_client: Any, full_prompt: str) -> 'LlmResponse':
    response = await llm_client.invoke(messages=[
        {"role": "system", "content": "You are a professional translator."},
        {"role": "user", "content": full_prompt}
    ])
    print(f"RAW: {response}")
    return LlmResponse.parse_plain_response(response, llm_client.llm_type)
