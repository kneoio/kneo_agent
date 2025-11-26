import json
import logging
from typing import Any

from cnst.search_engine import SearchEngine
from llm.llm_response import LlmResponse
from mcp.external.internet_mcp import InternetMCP
from tools.sound_fragment_tool import get_tool_definition as get_sound_fragment_tool_definition
from tools.queue_tool import get_tool_definition as get_queue_tool_definition
from tools.listener_tool import get_tool_definition as get_listener_tool_definition
from tools.stations_tool import (
    get_list_stations_tool_definition,
    get_station_live_tool_definition,
)

logger = logging.getLogger(__name__)


def _combine_messages(messages: list) -> str:
    parts = []
    for m in messages or []:
        role = m.get("role")
        content = m.get("content")
        if not content:
            continue
        if role == "system":
            parts.append(f"System: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
        elif role == "tool":
            parts.append(f"Tool: {content}")
        else:
            parts.append(f"User: {content}")
    return "\n\n".join(parts)


async def invoke_intro(llm_client: Any, prompt: str, draft: str, on_air_memory: str, enable_tools: bool = True) -> Any:
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
    if enable_tools and hasattr(llm_client, 'tool_functions') and llm_client.tool_functions:
        internet_tool = SearchEngine.Perplexity.value
        tools = [InternetMCP.get_tool_definition(default_engine=internet_tool)]
        logger.info(f'invoke_intro: Internet tools "{internet_tool}" enabled for {llm_client.llm_type.name}')
    else:
        logger.debug(f"invoke_intro: Tools disabled or not available for {llm_client.llm_type.name}")

    response = await llm_client.invoke(
        messages=[
            {"role": "system", "content": "You are a professional radio DJ"},
            {"role": "user", "content": full_prompt}
        ],
        tools=tools
    )

    return response



async def invoke_chat(llm_client: Any, messages: list, return_full_history: bool = False) -> 'LlmResponse':
    tools = None
    if llm_client.tool_functions:
        internet_tool = SearchEngine.Perplexity.value
        tools = [InternetMCP.get_tool_definition(default_engine=internet_tool)]
        if 'get_brand_sound_fragment' in llm_client.tool_functions:
            sf_def = get_sound_fragment_tool_definition()
            tools.append(sf_def)
        if 'queue_intro_and_song' in llm_client.tool_functions:
            q_def = get_queue_tool_definition()
            tools.append(q_def)
        if 'get_listener_by_telegram' in llm_client.tool_functions:
            listener_def = get_listener_tool_definition()
            tools.append(listener_def)
        if 'list_stations' in llm_client.tool_functions:
            tools.append(get_list_stations_tool_definition())
        if 'get_station_live' in llm_client.tool_functions:
            tools.append(get_station_live_tool_definition())
        logger.info(
            f'invoke_chat: tools enabled for {llm_client.llm_type.name}: '
            f'internet={True}, '
            f'sound_fragment={"get_brand_sound_fragment" in llm_client.tool_functions}, '
            f'queue_intro_and_song={"queue_intro_and_song" in llm_client.tool_functions}, '
            f'listener={"get_listener_by_telegram" in llm_client.tool_functions}, '
            f'list_stations={"list_stations" in llm_client.tool_functions}, '
            f'get_station_live={"get_station_live" in llm_client.tool_functions}'
        )
        try:
            tool_names = []
            for t in tools or []:
                fn = (t or {}).get('function') if isinstance(t, dict) else None
                if isinstance(fn, dict):
                    tool_names.append(fn.get('name'))
            logger.info(f'invoke_chat: sending tool names: {tool_names}')
        except Exception:
            pass
    else:
        logger.debug(f"invoke_chat: No tools available for {llm_client.llm_type.name}")

    try:
        if hasattr(llm_client, "invoke"):
            response = await llm_client.invoke(messages=messages, tools=tools)
        else:
            combined = _combine_messages(messages)
            response = await llm_client.ainvoke(combined)
    except Exception as e:
        return LlmResponse.from_invoke_error(e, llm_client.llm_type)

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
                if not func and "<" in (name or ""):
                    base_name = name.split("<", 1)[0]
                    func = llm_client.tool_functions.get(base_name)
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

        if hasattr(llm_client, "invoke"):
            response = await llm_client.invoke(messages=messages, tools=tools)
        else:
            combined_followup = _combine_messages(messages)
            response = await llm_client.ainvoke(combined_followup)
        try:
            clen = len(getattr(response, 'content', '') or '')
            logger.info(f"invoke_chat: follow-up response content length={clen}")
        except Exception:
            pass

        

    llm_response = LlmResponse.parse_plain_response(response, llm_client.llm_type)
    if return_full_history:
        llm_response.full_messages = messages
    return llm_response


async def translate_prompt(llm_client: Any, prompt: str, to_translate: str) -> 'LlmResponse':
    full_prompt = f"{prompt}\n\nInput:\n{to_translate}"
    tp_messages = [
        {"role": "system", "content": "You are a professional translator."},
        {"role": "user", "content": full_prompt}
    ]
    if hasattr(llm_client, "invoke"):
        response = await llm_client.invoke(messages=tp_messages)
    else:
        response = await llm_client.ainvoke(_combine_messages(tp_messages))
    print(f"RAW: {response}")
    return LlmResponse.parse_plain_response(response, llm_client.llm_type)


async def translate_content(llm_client: Any, content: str) -> 'LlmResponse':
    tc_messages = [
        {"role": "system", "content": "You are a professional translator."},
        {"role": "user", "content": content}
    ]
    if hasattr(llm_client, "invoke"):
        response = await llm_client.invoke(messages=tc_messages)
    else:
        response = await llm_client.ainvoke(_combine_messages(tc_messages))
    return LlmResponse.parse_plain_response(response, llm_client.llm_type)
