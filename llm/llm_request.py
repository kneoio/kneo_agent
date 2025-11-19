import json
import logging
from typing import Any

from cnst.search_engine import SearchEngine
from llm.llm_response import LlmResponse
from mcp.external.internet_mcp import InternetMCP
from tools.sound_fragment_tool import get_brand_sound_fragment, get_tool_definition as get_sound_fragment_tool_definition
from tools.queue_tool import queue_intro_song, get_tool_definition as get_queue_tool_definition

logger = logging.getLogger(__name__)


async def invoke_intro(llm_client: Any, prompt: str, draft: str, on_air_memory: str) -> 'LlmResponse':
    memory_block = (
        "Recent on-air atmosphere (DO NOT repeat this text; use only for mood/context):\n"
        f"{on_air_memory}\n\n"
    )

    full_prompt = (
        f"{memory_block}"
        f"{prompt}\n\n"
        f"Draft input:\n{draft}"
    )

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



async def invoke_chat(llm_client: Any, messages: list) -> 'LlmResponse':
    tools = None
    if hasattr(llm_client, 'tool_functions') and llm_client.tool_functions:
        internet_tool = SearchEngine.Perplexity.value
        tools = [InternetMCP.get_tool_definition(default_engine=internet_tool)]
        if 'get_brand_sound_fragment' in llm_client.tool_functions:
            tools.append(get_sound_fragment_tool_definition())
        if 'queue_intro_song' in llm_client.tool_functions:
            tools.append(get_queue_tool_definition())
        logger.info(f'invoke_chat: tools enabled for {llm_client.llm_type.name}: internet={True}, sound_fragment={"get_brand_sound_fragment" in llm_client.tool_functions}, queue_intro_song={"queue_intro_song" in llm_client.tool_functions}')
    else:
        logger.debug(f"invoke_chat: No tools available for {llm_client.llm_type.name}")

    try:
        response = await llm_client.invoke(messages=messages, tools=tools)
    except Exception as e:
        error_msg = str(e)
        if "Failed to parse tool call arguments" in error_msg or "tool_use_failed" in error_msg:
            logger.error(f"LLM generated malformed tool call JSON: {error_msg}")
            fallback_response = type('obj', (object,), {
                'content': "I encountered an error processing your request. Could you rephrase or try again?",
                'tool_calls': None
            })()
            return LlmResponse.parse_plain_response(fallback_response, llm_client.llm_type)
        raise

    last_tool_output_str = None
    if hasattr(response, 'tool_calls') and response.tool_calls and getattr(llm_client, 'tool_functions', None):
        try:
            tc_count = len(response.tool_calls) if response.tool_calls else 0
            logger.info(f"invoke_chat: {tc_count} tool_calls returned")
        except Exception:
            logger.info("invoke_chat: tool_calls returned")
        
        messages.append({
            "role": "assistant",
            "content": getattr(response, 'content', '') or '',
            "tool_calls": response.tool_calls
        })
        
        for tool_call in response.tool_calls:
            try:
                if isinstance(tool_call, dict):
                    if 'function' in tool_call:
                        func_obj = tool_call.get('function') or {}
                        name = func_obj.get('name')
                        args_raw = func_obj.get('arguments')
                        tc_id = tool_call.get('id')
                    else:
                        name = tool_call.get('name')
                        args_raw = tool_call.get('arguments')
                        if args_raw is None:
                            args_raw = tool_call.get('args')
                        tc_id = tool_call.get('id') or tool_call.get('tool_call_id')
                else:
                    name = tool_call.function.name
                    args_raw = tool_call.function.arguments
                    tc_id = tool_call.id
                args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
                logger.info(f"invoke_chat: executing tool '{name}' with args={args}")
                func = llm_client.tool_functions.get(name)
                if not func:
                    continue
                result = await func(**args)
                try:
                    last_tool_output_str = json.dumps(result)
                except Exception:
                    last_tool_output_str = str(result)
                messages.append({
                    "tool_call_id": tc_id,
                    "role": "tool",
                    "name": name,
                    "content": last_tool_output_str
                })
            except Exception as e:
                safe_name = None
                if isinstance(tool_call, dict):
                    fn = tool_call.get('function') or {}
                    safe_name = fn.get('name')
                else:
                    safe_name = getattr(getattr(tool_call, 'function', None), 'name', None)
                logger.error(f"invoke_chat tool execution error for {safe_name}: {e}")

        response = await llm_client.invoke(messages=messages, tools=tools)
        try:
            clen = len(getattr(response, 'content', '') or '')
            logger.info(f"invoke_chat: follow-up response content length={clen}")
        except Exception:
            pass

        

    return LlmResponse.parse_plain_response(response, llm_client.llm_type)


async def translate_prompt(llm_client: Any, prompt: str, to_translate: str) -> 'LlmResponse':
    full_prompt = f"{prompt}\n\nInput:\n{to_translate}"
    response = await llm_client.invoke(messages=[
        {"role": "system", "content": "You are a professional translator."},
        {"role": "user", "content": full_prompt}
    ])
    print(f"RAW: {response}")
    return LlmResponse.parse_plain_response(response, llm_client.llm_type)


async def translate_content(llm_client: Any, content: str) -> 'LlmResponse':
    response = await llm_client.invoke(messages=[
        {"role": "system", "content": "You are a professional translator."},
        {"role": "user", "content": content}
    ])
    return LlmResponse.parse_plain_response(response, llm_client.llm_type)
