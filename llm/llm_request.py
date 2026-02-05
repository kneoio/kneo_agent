import json
import logging
from typing import Any

from cnst.search_engine import SearchEngine
from llm.llm_response import LlmResponse
from llm.finetune_logger import get_finetune_logger
from core.db_logger import setup_db_logger
from mcp.external.internet_mcp import InternetMCP
from tools.sound_fragment_tool import get_tool_definition as get_sound_fragment_tool_definition
from tools.queue_tool import get_tool_definition as get_queue_tool_definition
 

logger = logging.getLogger(__name__)
_ft_logger = get_finetune_logger()


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


async def invoke_intro(llm_client: Any, prompt: str, draft: str, on_air_memory: str, brand: str = None, prompt_title: str = None) -> Any:
    memory_block = ""
    if on_air_memory:
        memory_block = (
            "PAST on-air atmosphere - DO NOT use song/artist info from this section, only for mood/context:\n"
            f"{on_air_memory}\n\n"
        )

    full_prompt = (
        f"{memory_block}"
        f"{prompt}\n\n"
        f"Draft input:\n{draft}"
    )

    logger.info(f"invoke_intro: full_prompt={full_prompt}")
    
    if brand:
        db_logger = setup_db_logger(brand)
        db_logger.info("LLM invoke_intro called", 
                      extra={'event_type': 'llm_invoke', 'llm_type': llm_client.llm_type.name, 
                            'has_memory': bool(on_air_memory), 'has_draft': bool(draft),
                            'full_prompt': full_prompt, 'prompt_title': prompt_title})

    messages = [
        {"role": "system", "content": "You are a professional radio DJ"},
        {"role": "user", "content": full_prompt}
    ]

    response = await llm_client.invoke(messages=messages)

    try:
        response_content = ""
        if hasattr(response, 'content'):
            response_content = response.content if isinstance(response.content, str) else str(response.content)
        
        if brand:
            db_logger = setup_db_logger(brand)
            db_logger.info("LLM response received", 
                          extra={'event_type': 'llm_response', 'llm_type': llm_client.llm_type.name,
                                'response_content': response_content})
        
        _ft_logger.log_interaction(
            function_name="invoke_intro",
            llm_type=llm_client.llm_type.name,
            messages=messages,
            response_content=response_content,
            metadata={"has_on_air_memory": bool(on_air_memory)}
        )
    except Exception as e:
        logger.debug(f"invoke_intro: finetune logging failed: {e}")

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
        
        logger.info(
            f'invoke_chat: tools enabled for {llm_client.llm_type.name}: '
            f'internet={True}, '
            f'sound_fragment={"get_brand_sound_fragment" in llm_client.tool_functions}, '
            f'queue_intro_and_song={"queue_intro_and_song" in llm_client.tool_functions}'
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

    try:
        _ft_logger.log_interaction(
            function_name="invoke_chat",
            llm_type=llm_client.llm_type.name,
            messages=messages,
            response_content=llm_response.actual_result,
            tools=tools,
            tool_calls=getattr(response, 'tool_calls', None),
            tool_results=[m for m in messages if m.get("role") == "tool"] if messages else None,
            reasoning=llm_response.reasoning,
            thinking=llm_response.thinking,
            metadata={"return_full_history": return_full_history}
        )
    except Exception as e:
        logger.debug(f"invoke_chat: finetune logging failed: {e}")

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
    llm_response = LlmResponse.parse_plain_response(response, llm_client.llm_type)

    try:
        _ft_logger.log_interaction(
            function_name="translate_prompt",
            llm_type=llm_client.llm_type.name,
            messages=tp_messages,
            response_content=llm_response.actual_result,
            reasoning=llm_response.reasoning,
            thinking=llm_response.thinking
        )
    except Exception as e:
        logger.debug(f"translate_prompt: finetune logging failed: {e}")

    return llm_response


async def translate_content(llm_client: Any, content: str) -> 'LlmResponse':
    tc_messages = [
        {"role": "system", "content": "You are a professional translator."},
        {"role": "user", "content": content}
    ]
    if hasattr(llm_client, "invoke"):
        response = await llm_client.invoke(messages=tc_messages)
    else:
        response = await llm_client.ainvoke(_combine_messages(tc_messages))
    llm_response = LlmResponse.parse_plain_response(response, llm_client.llm_type)

    try:
        _ft_logger.log_interaction(
            function_name="translate_content",
            llm_type=llm_client.llm_type.name,
            messages=tc_messages,
            response_content=llm_response.actual_result,
            reasoning=llm_response.reasoning,
            thinking=llm_response.thinking
        )
    except Exception as e:
        logger.debug(f"translate_content: finetune logging failed: {e}")

    return llm_response
