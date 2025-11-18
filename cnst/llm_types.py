from enum import Enum


class LlmType(Enum):
    CLAUDE = "CLAUDE"
    OPENAI = "OPENAI"
    GROQ = "GROQ"
    KIMI = "KIMI"
    DEEPSEEK = "DEEPSEEK"
    OPENROUTER = "OPENROUTER"
