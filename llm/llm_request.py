import logging
from typing import Any

from llm.llm_response import LlmResponse
from llm.finetune_logger import get_finetune_logger
from core.db_logger import setup_db_logger
 

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


async def invoke_intro(llm_client: Any, prompt: str, draft: str, on_air_memory: str, brand: str = None,
                       prompt_title: str = None) -> Any:
    memory_block = ""
    if on_air_memory:
        memory_block = (
            "=== PAST CONTEXT (IGNORE SONG NAMES) ===\n"
            "The following is ONLY for mood/atmosphere reference.\n"
            "DO NOT copy or reuse any song titles or artist names from this section.\n"
            f"{on_air_memory}\n"
            "=== END PAST / NEW REQUEST BELOW ===\n\n"
        )

    full_prompt = (
        f"{memory_block}"
        f"{prompt}\n\n"
        f"Draft input:\n{draft}"
    )

    #logger.info(f"invoke_intro: full_prompt={full_prompt}")

    if brand:
        db_logger = setup_db_logger(brand)
        db_logger.info("LLM invoke_intro called",
                       extra={'event_type': 'llm_invoke', 'llm_type': llm_client.llm_type.name,
                              'has_memory': bool(on_air_memory), 'has_draft': bool(draft),
                              'full_prompt': full_prompt, 'prompt_title': prompt_title})

    messages = [
        {"role": "system",
         "content": "You are a professional radio DJ. CRITICAL: Use ONLY song information from 'Draft input:'. NEVER use song names from PAST CONTEXT."},
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
