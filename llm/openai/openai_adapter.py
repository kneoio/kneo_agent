from openai import AsyncOpenAI
import openai


class OpenAIAdapter:
    def __init__(self, openai_client: AsyncOpenAI, model: str, temperature=None):
        self.client = openai_client
        self.model = model
        self.temperature = temperature
        self.tool_functions = {}
        self.llm_type = None

    async def invoke(self, messages, tools=None):
        openai_messages = []
        for m in messages:
            role = m.get("role")
            content = m.get("content")
            openai_messages.append({"role": role, "content": content})

        kwargs = {"model": self.model, "messages": openai_messages}
        if tools:
            kwargs["tools"] = tools
        elif not self.tool_functions:
            kwargs["tool_choice"] = "none"
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature

        try:
            resp = await self.client.chat.completions.create(**kwargs)
            message = resp.choices[0].message
            return type('obj', (object,), {
                'content': message.content or "",
                'tool_calls': getattr(message, 'tool_calls', None)
            })()
        except openai.RateLimitError as e:
            return type('obj', (object,), {
                'content': f"Rate limited: {str(e)}",
                'tool_calls': None
            })()
        except Exception as e:
            return type('obj', (object,), {
                'content': f"Provider error: {str(e)}",
                'tool_calls': None
            })()
