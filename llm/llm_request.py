from typing import Any

from cnst.llm_types import LlmType
from llm.llm_response import LlmResponse


async def invoke_intro(llm_client: Any, prompt: str, draft: str, llm_type: LlmType) -> 'LlmResponse':

    full_prompt = f"{prompt}\n\nInput:\n{draft}"
    response = await llm_client.ainvoke(messages=[{"role": "user", "content": full_prompt}])
    return LlmResponse.parse_plain_response(response, llm_type)

